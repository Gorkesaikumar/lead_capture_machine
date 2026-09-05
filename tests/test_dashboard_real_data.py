"""Regression coverage for database-backed dashboard values, with no provider calls."""
from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from rest_framework.test import APIClient

from apps.customers.models import Customer
from apps.conversations.models import Conversation
from apps.integrations.models import IntegrationConfig
from apps.leads.models import Lead, LeadActivity, LeadForm
from apps.subscriptions.models import BillingTransaction
from tests.tenant_fixtures import add_member, make_organization

pytestmark = pytest.mark.django_db
NOW = datetime(2026, 9, 1, 1, tzinfo=dt_timezone.utc)


@pytest.fixture
def dashboard(mocker, admin_user):
    mocker.patch("django.utils.timezone.now", return_value=NOW)
    org = make_organization(name="Real workspace", timezone="Asia/Kolkata")
    add_member(admin_user, org)
    client = APIClient()
    client.force_authenticate(admin_user)
    client.credentials(HTTP_X_ORGANIZATION_ID=str(org.id))
    return client, org


def lead(org, source, *, created_at=NOW, deleted=False, status="NEW", name="Recorded customer"):
    customer = Customer.objects.create(organization=org, display_name=name)
    item = Lead.objects.create(organization=org, customer=customer, source_channel=source,
                               is_deleted=deleted, status=status)
    Lead.objects.filter(pk=item.pk).update(created_at=created_at)
    return item


def test_dashboard_empty_workspace_returns_real_zeros(dashboard):
    client, _ = dashboard
    response = client.get("/api/v1/analytics/dashboard/?preset=this_month")
    assert response.status_code == 200
    data = response.json()
    assert data["leads"]["total_leads"] == 0
    assert data["leads"]["open_conversations"] == 0
    assert data["leads"]["lead_to_booking_conversion_rate"] == 0
    assert data["activities"] == data["recent_leads"] == []
    assert [row["status"] for row in data["channels"]] == ["DISCONNECTED", "DISCONNECTED", "NOT_CONFIGURED"]
    assert all(row["leadCount"] == 0 for row in data["channels"])
    assert data["leads_timeseries"] == [{"date": "2026-09-01", "total": 0, "converted": 0,
                                        "instagram": 0, "whatsapp": 0, "website": 0, "other": 0}]


def test_dashboard_scopes_counts_names_activity_and_channel_state(dashboard):
    client, org = dashboard
    other_org = make_organization(name="Private other workspace")
    # August in UTC, September in the organization's timezone.
    ig = lead(org, "INSTAGRAM", created_at=NOW - timedelta(hours=6), status="CONVERTED", name="Saved name")
    lead(org, "WEBSITE")
    lead(org, "MANUAL")
    deleted = lead(org, "WHATSAPP", deleted=True)
    foreign = lead(other_org, "WHATSAPP", name="Must not leak")
    lead(org, "WHATSAPP", created_at=NOW - timedelta(days=3))
    for item in [ig, deleted, foreign]:
        LeadActivity.objects.create(lead=item, activity_type="STATUS_CHANGED")
    Conversation.objects.create(organization=org, customer=ig.customer, channel="INSTAGRAM", status="ACTIVE")
    Conversation.objects.create(organization=other_org, customer=foreign.customer, channel="WHATSAPP", status="ACTIVE")
    IntegrationConfig.objects.create(organization=org, provider="INSTAGRAM", is_active=True,
        credentials={"access_token": "test-secret-do-not-return"},
        metadata={"destination_id": "10001", "webhook_subscribed": True, "last_verified_at": NOW.isoformat()})
    LeadForm.objects.create(organization=org, name="Published", is_active=True)
    data = client.get("/api/v1/analytics/dashboard/?preset=this_month").json()
    assert data["leads"]["total_leads"] == 3
    assert data["leads"]["converted_leads"] == 1
    assert data["leads"]["lead_to_booking_conversion_rate"] == 33.33
    assert data["leads"]["open_conversations"] == 1
    assert data["leads"]["new_leads_today"] == 3
    assert data["leads_timeseries"] == [{"date": "2026-09-01", "total": 3, "converted": 1,
                                        "instagram": 1, "whatsapp": 0, "website": 1, "other": 1}]
    assert len(data["recent_leads"]) == 3
    assert any(row["customer"]["display_name"] == "Saved name" for row in data["recent_leads"])
    assert len(data["activities"]) == 1
    assert data["activities"][0]["lead_id"] == str(ig.id)
    assert data["activities"][0]["title"] == "Status Changed"
    assert [row["status"] for row in data["channels"]] == ["CONNECTED", "DISCONNECTED", "ACTIVE"]
    assert "Must not leak" not in str(data)
    assert "test-secret" not in str(data)
    assert data["timezone"] == "Asia/Kolkata"


def test_date_selection_and_refresh_use_saved_records(dashboard):
    client, org = dashboard
    lead(org, "WHATSAPP", created_at=NOW - timedelta(days=2))
    assert client.get("/api/v1/analytics/dashboard/?preset=today").json()["leads"]["total_leads"] == 0
    seven = client.get("/api/v1/analytics/dashboard/?preset=7d").json()
    assert seven["leads"]["total_leads"] == 1
    assert len(seven["leads_timeseries"]) == 7
    assert sum(row["whatsapp"] for row in seven["leads_timeseries"]) == 1
    lead(org, "INSTAGRAM")
    assert client.get("/api/v1/analytics/dashboard/?preset=today").json()["leads"]["total_leads"] == 1


@pytest.mark.parametrize("metadata,expected", [
    ({"token_expires_at": (NOW - timedelta(seconds=1)).isoformat()}, "TOKEN_EXPIRED"),
    ({"error_code": "permission_required"}, "PERMISSION_REQUIRED"),
    ({}, "CONFIGURED_UNVERIFIED"),
    ({"webhook_subscribed": False}, "CONFIGURATION_REQUIRED"),
])
def test_dashboard_does_not_claim_unverified_channels_connected(dashboard, metadata, expected):
    client, org = dashboard
    IntegrationConfig.objects.create(organization=org, provider="INSTAGRAM", is_active=True,
        credentials={"access_token": "private-test-token"}, metadata={"destination_id": "10001", **metadata})
    LeadForm.objects.create(organization=org, name="Deleted form", is_active=True, is_deleted=True)
    data = client.get("/api/v1/analytics/dashboard/?preset=today").json()
    assert data["channels"][0]["status"] == expected
    assert data["channels"][2]["status"] == "NOT_CONFIGURED"


def test_admin_revenue_keeps_currencies_separate_and_excludes_failed_payments(dashboard):
    client, org = dashboard
    for currency, amount, status in [("INR", "399.00", "success"), ("USD", "5.00", "success"), ("INR", "8000.00", "failed")]:
        BillingTransaction.objects.create(organization=org, currency=currency, amount=amount, status=status)
    revenue = client.get("/api/v1/admin/revenue/").json()
    assert revenue["summary"]["by_currency"]["total"] == {"INR": "399.00", "USD": "5.00"}
    assert revenue["summary"]["total_revenue_usd"] == "5.00"
    assert all(row["amount_inr"] is None for row in revenue["ledger"] if row["currency"] == "USD")
    kpis = client.get("/api/v1/admin/kpis/").json()
    assert kpis["revenue_by_currency"] == {"INR": "399.00", "USD": "5.00"}
    trend = client.get("/api/v1/admin/analytics/").json()["revenue_growth"]
    assert {(row["currency"], row["amount"]) for row in trend} == {("INR", "399.00"), ("USD", "5.00")}


def test_admin_user_payment_history_uses_recorded_currency(dashboard):
    from apps.accounts.models import User
    client, _ = dashboard
    user = User.objects.create_user(email="payment-owner@example.test")
    org = make_organization(owner=user, name="Payment workspace")
    url = f"/api/v1/admin/users/{user.id}/"
    initial = client.get(url)
    assert initial.status_code == 200
    subscription_id = initial.json()["subscription"]["id"]
    from apps.subscriptions.models import UsageRecord
    UsageRecord.objects.filter(subscription_id=subscription_id).update(total_leads_count=3)
    BillingTransaction.objects.create(organization=org, subscription_id=subscription_id,
                                      amount="399.00", currency="INR", status="success")
    detail = client.get(url).json()
    payment = detail["payment_history"][0]
    assert payment["amount"] == payment["amount_inr"] == "399.00"
    assert payment["amount_usd"] is None
    assert detail["usage"]["usage_percentage"] == round(3 / detail["usage"]["lead_limit"] * 100, 1)
    listing = client.get("/api/v1/admin/users/?search=payment-owner")
    assert listing.status_code == 200
    assert listing.json()["results"][0]["usage"]["usage_percentage"] == detail["usage"]["usage_percentage"]
