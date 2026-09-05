from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
"""
Tests for Audit Logging System:
- Model immutability (append-only enforcement, deletion prevention)
- Automatic secret and sensitive data scrubbing
- Domain actions auditing (10 required actions)
- Authorized Read-Only REST API endpoints and query filtering
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.accounts.services import AuthService
from apps.audit.models import AuditEvent
from apps.audit.services import AuditService, sanitize_metadata
from apps.bookings.models import Booking
from apps.bookings.services import BookingLinkService, BookingService
from apps.customers.models import Customer, CustomerIdentity
from apps.leads.models import Lead, LeadActivity
from apps.leads.services import LeadManagementService
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.scheduling.models import BlockedPeriod, HolidayClosure, SpecialAvailability, WeeklyAvailability
from apps.services.models import Package, PhotographyService


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        email="admin_audit@example.com",
        password="SecureAdminPassword123!",
        full_name="Audit Administrator",
    )
    add_member(user)
    return user


@pytest.fixture
def second_staff(db):
    return User.objects.create_user(
        email="staff_audit@example.com",
        password="StaffPassword123!",
        full_name="Staff Member",
    )


@pytest.fixture
def auth_client(admin_user):
    client = APIClient()
    _, token = AuthService.authenticate_admin(admin_user.email, "SecureAdminPassword123!")
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def test_customer(db):
    customer = Customer.objects.create(organization=test_workspace(),
        display_name="Audit Test Client",
        primary_phone="+15551234567",
    )
    CustomerIdentity.objects.create(
        customer=customer,
        channel=CustomerIdentity.Channel.WHATSAPP,
        external_user_id="15551234567",
        normalized_phone="+15551234567",
    )
    return customer


@pytest.fixture
def photography_service(db):
    service = PhotographyService.objects.create(organization=test_workspace(),
        name="Portrait Session",
        slug="portrait-session-audit",
        description="Standard studio portrait",
        duration_minutes=60,
        buffer_before_minutes=15,
        buffer_after_minutes=15,
        base_price=Decimal("150.00"),
        is_active=True,
    )
    WeeklyAvailability.objects.create(organization=test_workspace(),
        weekday=0,  # Monday
        start_time=time(9, 0),
        end_time=time(17, 0),
        is_active=True,
    )
    return service


@pytest.fixture
def test_lead(db, test_customer, photography_service):
    return create_lead(
        customer=test_customer,
        source_channel="WHATSAPP",
        service=photography_service,
        status=Lead.Status.NEW,
    )


# =============================================================================
# 1. Model Immutability Tests
# =============================================================================

@pytest.mark.django_db
class TestAuditModelImmutability:

    def test_audit_event_creation_succeeds(self, admin_user):
        event = AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.USER_LOGIN,
            entity_type="User",
            entity_id=str(admin_user.id),
            metadata={"email": admin_user.email},
            ip_address="127.0.0.1",
        )
        assert event.id is not None
        assert event.action == AuditEvent.Action.USER_LOGIN
        assert event.actor == admin_user

    def test_audit_event_update_raises_permission_error(self, admin_user):
        event = AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.USER_LOGIN,
            entity_type="User",
            entity_id=str(admin_user.id),
        )
        event.action = AuditEvent.Action.USER_LOGOUT
        with pytest.raises(PermissionError, match="append-only"):
            event.save()

    def test_audit_event_delete_raises_permission_error(self, admin_user):
        event = AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.USER_LOGIN,
            entity_type="User",
            entity_id=str(admin_user.id),
        )
        with pytest.raises(PermissionError, match="cannot be deleted"):
            event.delete()

    def test_audit_queryset_bulk_update_raises_permission_error(self, admin_user):
        AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.USER_LOGIN,
            entity_type="User",
            entity_id=str(admin_user.id),
        )
        with pytest.raises(PermissionError, match="append-only"):
            AuditEvent.objects.all().update(action=AuditEvent.Action.USER_LOGOUT)

    def test_audit_queryset_bulk_delete_raises_permission_error(self, admin_user):
        AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.USER_LOGIN,
            entity_type="User",
            entity_id=str(admin_user.id),
        )
        with pytest.raises(PermissionError, match="cannot be deleted"):
            AuditEvent.objects.all().delete()


# =============================================================================
# 2. Sensitive Data Redaction & Sanitization Tests
# =============================================================================

@pytest.mark.django_db
class TestAuditSanitization:

    def test_sensitive_keys_are_redacted(self):
        raw_meta = {
            "user_id": "12345",
            "password": "SuperSecretPassword!",
            "auth_token": "token_abc123xyz",
            "meta_access_token": "EAAG...",
            "api_key": "sk-123456",
            "app_secret": "meta_app_secret_value",
            "credit_card": "4111222233334444",
            "cvv": "123",
            "notes": "Safe public note",
        }
        sanitized = sanitize_metadata(raw_meta)

        assert sanitized["user_id"] == "12345"
        assert sanitized["notes"] == "Safe public note"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["auth_token"] == "[REDACTED]"
        assert sanitized["meta_access_token"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["app_secret"] == "[REDACTED]"
        assert sanitized["credit_card"] == "[REDACTED]"
        assert sanitized["cvv"] == "[REDACTED]"

    def test_nested_structures_are_sanitized_recursively(self):
        raw_meta = {
            "service": "Wedding Shoot",
            "config": {
                "secret_key": "xyz_secret",
                "webhook_verify_token": "verify_123",
                "env": "production",
            },
            "credentials": {
                "any_field": "hidden",
            },
            "sub_items": [
                {"token": "item_token_1", "item_name": "Item A"},
                {"safe_field": 100},
            ],
        }
        sanitized = sanitize_metadata(raw_meta)

        assert sanitized["service"] == "Wedding Shoot"
        assert sanitized["config"]["secret_key"] == "[REDACTED]"
        assert sanitized["config"]["webhook_verify_token"] == "[REDACTED]"
        assert sanitized["config"]["env"] == "production"
        assert sanitized["credentials"] == "[REDACTED]"
        assert sanitized["sub_items"][0]["token"] == "[REDACTED]"
        assert sanitized["sub_items"][0]["item_name"] == "Item A"
        assert sanitized["sub_items"][1]["safe_field"] == 100


# =============================================================================
# 3. Domain Action Auditing Tests (10 Actions)
# =============================================================================

@pytest.mark.django_db
class TestDomainActionAuditing:

    def test_1_lead_status_changed_audit(self, test_lead, admin_user):
        LeadManagementService.update_status(
            lead=test_lead,
            new_status=Lead.Status.QUALIFIED,
            actor=admin_user,
            notes="Customer confirmed interest",
        )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.LEAD_STATUS_CHANGED,
            entity_id=str(test_lead.id),
        ).first()

        assert event is not None
        assert event.actor == admin_user
        assert event.entity_type == "Lead"
        assert event.metadata["old_status"] == Lead.Status.NEW
        assert event.metadata["new_status"] == Lead.Status.QUALIFIED
        assert event.metadata["notes"] == "Customer confirmed interest"

    def test_2_lead_assigned_audit(self, test_lead, second_staff, admin_user):
        LeadManagementService.assign_staff(
            lead=test_lead,
            staff=second_staff,
            actor=admin_user,
        )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.LEAD_ASSIGNED,
            entity_id=str(test_lead.id),
        ).first()

        assert event is not None
        assert event.actor == admin_user
        assert event.metadata["new_staff_id"] == str(second_staff.id)
        assert event.metadata["new_staff_email"] == second_staff.email

    def test_3_booking_link_generated_audit(self, test_lead, admin_user):
        link = BookingLinkService.create_for_lead(
            lead=test_lead,
            created_by=admin_user,
        )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.BOOKING_LINK_GENERATED,
            entity_id=str(link.id),
        ).first()

        assert event is not None
        assert event.actor == admin_user
        assert event.metadata["lead_id"] == str(test_lead.id)
        assert event.metadata["link_prefix"] == link.token[:8]

    @patch("apps.notifications.services.NotificationService.dispatch_now")
    def test_4_booking_link_sent_audit(self, mock_dispatch, test_customer):
        mock_dispatch.return_value = None
        notif, _ = NotificationService.send_booking_link(
            customer=test_customer,
            booking_url="https://studio.example.com/book/token123",
            lead_id="sample-lead-id",
        )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.BOOKING_LINK_SENT,
            entity_id=str(notif.id),
        ).first()

        assert event is not None
        assert event.entity_type == "Notification"
        assert event.metadata["customer_id"] == str(test_customer.id)

    def test_5_booking_created_audit(self, test_lead, photography_service, admin_user):
        link = BookingLinkService.create_for_lead(lead=test_lead, created_by=admin_user)
        # Find next Monday 10:00 AM
        now = timezone.now()
        days_ahead = (0 - now.weekday() + 7) % 7 or 7
        target_date = (now + timedelta(days=days_ahead)).date()
        studio_tz = timezone.get_current_timezone()
        starts_at = timezone.make_aware(
            datetime.combine(target_date, time(10, 0)), studio_tz
        )

        booking = BookingService.create_booking(
            booking_link_token=link.token,
            starts_at=starts_at,
        )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.BOOKING_CREATED,
            entity_id=str(booking.id),
        ).first()

        assert event is not None
        assert event.metadata["customer_id"] == str(test_lead.customer.id)
        assert event.metadata["service_id"] == str(photography_service.id)

    def test_6_booking_cancelled_audit(self, test_lead, photography_service, admin_user):
        link = BookingLinkService.create_for_lead(lead=test_lead, created_by=admin_user)
        now = timezone.now()
        days_ahead = (0 - now.weekday() + 7) % 7 or 7
        target_date = (now + timedelta(days=days_ahead)).date()
        studio_tz = timezone.get_current_timezone()
        starts_at = timezone.make_aware(
            datetime.combine(target_date, time(14, 0)), studio_tz
        )

        booking = BookingService.create_booking(
            booking_link_token=link.token,
            starts_at=starts_at,
        )
        BookingService.cancel_booking(
            booking=booking,
            reason="Customer requested reschedule",
            cancelled_by=admin_user,
        )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.BOOKING_CANCELLED,
            entity_id=str(booking.id),
        ).first()

        assert event is not None
        assert event.actor == admin_user
        assert event.metadata["reason"] == "Customer requested reschedule"

    def test_7_availability_changed_audit(self, auth_client):
        # Create WeeklyAvailability via API
        url = reverse("api_v1:scheduling:weekly-availability-list")
        payload = {
            "weekday": 2,  # Wednesday
            "start_time": "10:00:00",
            "end_time": "18:00:00",
            "is_active": True,
        }
        res = auth_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        created_id = res.data["id"]

        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.AVAILABILITY_CHANGED,
            entity_id=str(created_id),
        ).first()
        assert event is not None
        assert event.metadata["change_type"] == "create"
        assert event.metadata["weekday"] == 2

    def test_8_service_changed_audit(self, auth_client):
        # Create PhotographyService via API
        url = reverse("api_v1:services:service-list")
        payload = {
            "name": "Maternity Photography",
            "slug": "maternity-photo-audit",
            "description": "Studio maternity session",
            "duration_minutes": 90,
            "buffer_before_minutes": 15,
            "buffer_after_minutes": 15,
            "base_price": "250.00",
            "is_active": True,
        }
        res = auth_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        service_id = res.data["id"]

        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.SERVICE_CHANGED,
            entity_id=str(service_id),
        ).first()
        assert event is not None
        assert event.metadata["change_type"] == "create"
        assert event.metadata["name"] == "Maternity Photography"

    def test_9_integration_settings_changed_audit(self, admin_user):
        AuditService.record_integration_settings_changed(
            setting_name="META_WEBHOOK_VERIFY_TOKEN",
            old_value="old_secret_token",
            new_value="new_secret_token",
            actor=admin_user,
        )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.INTEGRATION_SETTINGS_CHANGED,
            entity_id="META_WEBHOOK_VERIFY_TOKEN",
        ).first()

        assert event is not None
        assert event.actor == admin_user
        # Secrets in metadata should be redacted
        assert event.metadata["old_value"] == "[REDACTED]"
        assert event.metadata["new_value"] == "[REDACTED]"

    def test_10_staff_role_changed_audit(self, second_staff, admin_user):
        AuthService.update_staff_role(
            target_user=second_staff,
            is_staff=True,
            is_superuser=True,
            actor=admin_user,
        )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.STAFF_ROLE_CHANGED,
            entity_id=str(second_staff.id),
        ).first()

        assert event is not None
        assert event.actor == admin_user
        assert event.metadata["changes"]["is_superuser"]["new"] is True


# =============================================================================
# 4. Authorized Read-Only Audit REST API Tests
# =============================================================================

@pytest.mark.django_db
class TestAuditAPI:

    def test_unauthenticated_requests_rejected(self):
        client = APIClient()
        url = reverse("api_v1:audit:audit-event-list")
        res = client.get(url)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_audit_events(self, auth_client, admin_user):
        # Create some audit events
        AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.BOOKING_CREATED,
            entity_type="Booking",
            entity_id="test-booking-uuid",
            metadata={"notes": "First booking"},
        )
        AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.LEAD_STATUS_CHANGED,
            entity_type="Lead",
            entity_id="test-lead-uuid",
            metadata={"notes": "Lead updated"},
        )

        url = reverse("api_v1:audit:audit-event-list")
        res = auth_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["count"] >= 2

    def test_filter_by_action_and_entity_type(self, auth_client, admin_user):
        AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.BOOKING_CREATED,
            entity_type="Booking",
            entity_id="booking-filter-id",
        )
        AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.LEAD_STATUS_CHANGED,
            entity_type="Lead",
            entity_id="lead-filter-id",
        )

        url = reverse("api_v1:audit:audit-event-list")
        res = auth_client.get(f"{url}?action=BOOKING_CREATED")
        assert res.status_code == status.HTTP_200_OK
        assert all(item["action"] == "BOOKING_CREATED" for item in res.data["results"])

    def test_retrieve_single_audit_event(self, auth_client, admin_user):
        event = AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.BOOKING_CREATED,
            entity_type="Booking",
            entity_id="single-retrieve-id",
            metadata={"detail": "test retrieve"},
        )
        url = reverse("api_v1:audit:audit-event-detail", kwargs={"pk": event.id})
        res = auth_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == str(event.id)
        assert res.data["action"] == AuditEvent.Action.BOOKING_CREATED
        assert res.data["actor"]["email"] == admin_user.email

    def test_non_get_methods_are_disallowed(self, auth_client, admin_user):
        event = AuditEvent.objects.create(organization=test_workspace(),
            actor=admin_user,
            action=AuditEvent.Action.BOOKING_CREATED,
            entity_type="Booking",
            entity_id="test-disallowed-id",
        )
        list_url = reverse("api_v1:audit:audit-event-list")
        detail_url = reverse("api_v1:audit:audit-event-detail", kwargs={"pk": event.id})

        # POST is forbidden
        res_post = auth_client.post(list_url, {"action": "BOOKING_CREATED"})
        assert res_post.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # PUT is forbidden
        res_put = auth_client.put(detail_url, {"action": "LEAD_STATUS_CHANGED"})
        assert res_put.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # PATCH is forbidden
        res_patch = auth_client.patch(detail_url, {"action": "LEAD_STATUS_CHANGED"})
        assert res_patch.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # DELETE is forbidden
        res_delete = auth_client.delete(detail_url)
        assert res_delete.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
