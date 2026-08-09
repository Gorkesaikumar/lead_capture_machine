"""
Comprehensive tests for Backend Analytics & Dashboard APIs.
Tests metric calculations, conversion funnels, source breakdown, popular services,
preset and custom date ranges, and PostgreSQL aggregation query efficiency.
"""
from datetime import timedelta
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.analytics.services import AnalyticsDateRange, AnalyticsService
from apps.bookings.models import Booking
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.services.models import PhotographyService


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email="analytics_admin@v4studio.com",
        password="AdminSecurePassword123!",
        full_name="Analytics Admin",
    )


@pytest.fixture
def analytics_test_data():
    """
    Sets up a realistic dataset of customers, services, leads, and bookings across various dates.
    """
    now = timezone.now()
    today_noon = now.replace(hour=12, minute=0, second=0, microsecond=0)

    # 1. Services
    service_portrait = PhotographyService.objects.create(
        name="Portrait Session",
        slug="portrait-session",
        duration_minutes=60,
        base_price=200.00,
    )
    service_wedding = PhotographyService.objects.create(
        name="Wedding Package",
        slug="wedding-package",
        duration_minutes=240,
        base_price=1500.00,
    )
    service_maternity = PhotographyService.objects.create(
        name="Maternity Shoot",
        slug="maternity-shoot",
        duration_minutes=90,
        base_price=350.00,
    )

    # 2. Customers
    c1 = Customer.objects.create(display_name="Alice Smith", email="alice@example.com")
    c2 = Customer.objects.create(display_name="Bob Jones", email="bob@example.com")
    c3 = Customer.objects.create(display_name="Charlie Brown", email="charlie@example.com")
    c4 = Customer.objects.create(display_name="Diana Prince", email="diana@example.com")
    c5 = Customer.objects.create(display_name="Evan Wright", email="evan@example.com")

    # 3. Leads
    # Lead 1: Instagram, Booked (Converted)
    l1 = Lead.objects.create(
        customer=c1,
        source_channel="INSTAGRAM",
        service=service_portrait,
        status=Lead.Status.BOOKED,
        qualified_at=now - timedelta(days=2),
    )
    # Lead 2: Instagram, New (Today)
    l2 = Lead.objects.create(
        customer=c2,
        source_channel="INSTAGRAM",
        service=service_portrait,
        status=Lead.Status.NEW,
    )
    # Lead 3: WhatsApp, Booking Link Sent (Qualified)
    l3 = Lead.objects.create(
        customer=c3,
        source_channel="WHATSAPP",
        service=service_wedding,
        status=Lead.Status.BOOKING_LINK_SENT,
        qualified_at=now - timedelta(days=1),
    )
    # Lead 4: WhatsApp, Completed (Converted)
    l4 = Lead.objects.create(
        customer=c4,
        source_channel="WHATSAPP",
        service=service_maternity,
        status=Lead.Status.COMPLETED,
        qualified_at=now - timedelta(days=5),
    )
    # Lead 5: WhatsApp, Lost
    l5 = Lead.objects.create(
        customer=c5,
        source_channel="WHATSAPP",
        service=service_portrait,
        status=Lead.Status.LOST,
    )

    # 4. Bookings
    # Booking 1: Today (Confirmed, Portrait) - 2 hours from now so it is upcoming today
    b1_start = now + timedelta(hours=2)
    b1 = Booking.objects.create(
        customer=c1,
        lead=l1,
        service=service_portrait,
        starts_at=b1_start,
        ends_at=b1_start + timedelta(minutes=60),
        status=Booking.Status.CONFIRMED,
    )
    # Booking 2: Tomorrow (Confirmed, Wedding)
    tomorrow_start = now + timedelta(days=1)
    b2 = Booking.objects.create(
        customer=c3,
        lead=l3,
        service=service_wedding,
        starts_at=tomorrow_start,
        ends_at=tomorrow_start + timedelta(minutes=240),
        status=Booking.Status.CONFIRMED,
    )
    # Booking 3: Past Completed (Maternity)
    past_date = now - timedelta(days=3)
    b3 = Booking.objects.create(
        customer=c4,
        lead=l4,
        service=service_maternity,
        starts_at=past_date,
        ends_at=past_date + timedelta(minutes=90),
        status=Booking.Status.COMPLETED,
    )
    # Booking 4: Cancelled (Portrait)
    b4 = Booking.objects.create(
        customer=c2,
        lead=l2,
        service=service_portrait,
        starts_at=now + timedelta(days=5),
        ends_at=now + timedelta(days=5, minutes=60),
        status=Booking.Status.CANCELLED,
    )

    return {
        "services": {
            "portrait": service_portrait,
            "wedding": service_wedding,
            "maternity": service_maternity,
        },
        "customers": [c1, c2, c3, c4, c5],
        "leads": [l1, l2, l3, l4, l5],
        "bookings": [b1, b2, b3, b4],
    }


@pytest.mark.django_db
class TestAnalyticsServiceCalculations:
    """Tests core business analytics computations and conversion rates."""

    def test_leads_metrics_aggregation(self, analytics_test_data):
        dr = AnalyticsDateRange.from_params(preset="all_time")
        metrics = AnalyticsService.get_leads_metrics(dr)

        assert metrics["total_leads"] == 5
        assert metrics["instagram_leads"] == 2
        assert metrics["whatsapp_leads"] == 3
        # l1 (BOOKED), l3 (BOOKING_LINK_SENT), l4 (COMPLETED) are qualified
        assert metrics["qualified_leads"] == 3
        # l3, l1, l4 reached booking link sent or higher
        assert metrics["booking_links_sent"] == 3
        # l1 (BOOKED) + l4 (COMPLETED) = 2 converted
        assert metrics["converted_leads"] == 2
        # Conversion rate: 2 / 5 * 100 = 40.0%
        assert metrics["lead_to_booking_conversion_rate"] == 40.0
        assert metrics["new_leads_today"] >= 1

    def test_bookings_metrics_aggregation(self, analytics_test_data):
        dr = AnalyticsDateRange.from_params(preset="all_time")
        metrics = AnalyticsService.get_bookings_metrics(dr)

        assert metrics["total_bookings"] == 4
        assert metrics["confirmed_bookings"] == 2
        assert metrics["completed_bookings"] == 1
        assert metrics["cancelled_bookings"] == 1
        assert metrics["bookings_today"] == 1
        assert metrics["bookings_tomorrow"] == 1
        # Today's confirmed + tomorrow's confirmed = 2 upcoming active
        assert metrics["upcoming_bookings"] == 2

    def test_lead_source_breakdown_and_conversion_by_source(self, analytics_test_data):
        dr = AnalyticsDateRange.from_params(preset="all_time")
        breakdown = AnalyticsService.get_lead_source_breakdown(dr)

        assert len(breakdown) == 2
        # WhatsApp: 3 leads, 1 converted (l4), 33.33% conv rate, 60% share
        wa = next(b for b in breakdown if b["source_channel"] == "WHATSAPP")
        assert wa["total_leads"] == 3
        assert wa["converted_leads"] == 1
        assert wa["share_percentage"] == 60.0
        assert wa["conversion_rate_percentage"] == 33.33

        # Instagram: 2 leads, 1 converted (l1), 50.0% conv rate, 40% share
        ig = next(b for b in breakdown if b["source_channel"] == "INSTAGRAM")
        assert ig["total_leads"] == 2
        assert ig["converted_leads"] == 1
        assert ig["share_percentage"] == 40.0
        assert ig["conversion_rate_percentage"] == 50.0

    def test_popular_services_ranking_and_revenue(self, analytics_test_data):
        dr = AnalyticsDateRange.from_params(preset="all_time")
        popular = AnalyticsService.get_popular_services(dr, limit=5)

        # Cancelled booking excluded from active popular ranking
        # Portrait (1 confirmed), Wedding (1 confirmed), Maternity (1 completed)
        assert len(popular) == 3
        service_names = [p["service_name"] for p in popular]
        assert "Portrait Session" in service_names
        assert "Wedding Package" in service_names
        assert "Maternity Shoot" in service_names

        # Wedding revenue: 1 booking * 1500 = 1500.0
        wedding = next(p for p in popular if p["service_name"] == "Wedding Package")
        assert wedding["booking_count"] == 1
        assert wedding["estimated_revenue"] == 1500.00


@pytest.mark.django_db
class TestAnalyticsDateRangeFiltering:
    """Tests preset ranges and custom start/end date boundaries."""

    def test_date_range_preset_parsing(self):
        dr_today = AnalyticsDateRange.from_params(preset="today")
        assert dr_today.preset == "today"
        assert dr_today.start_datetime is not None
        assert dr_today.end_datetime is not None

        dr_7d = AnalyticsDateRange.from_params(preset="7d")
        assert dr_7d.preset == "7d"
        assert (dr_7d.end_datetime - dr_7d.start_datetime).days >= 6

        dr_all = AnalyticsDateRange.from_params(preset="all_time")
        assert dr_all.start_datetime is None
        assert dr_all.end_datetime is None

    def test_custom_iso_date_filtering(self, analytics_test_data):
        today_str = timezone.localdate().strftime("%Y-%m-%d")
        dr = AnalyticsDateRange.from_params(start_date=today_str, end_date=today_str)
        summary = AnalyticsService.get_dashboard_summary(dr)

        assert summary["date_range"]["preset"] == "custom"
        assert summary["leads"]["total_leads"] >= 1


@pytest.mark.django_db
class TestAnalyticsQueryEfficiency:
    """Verifies that dashboard aggregations are computed with minimal database queries."""

    def test_dashboard_summary_uses_minimal_queries(self, analytics_test_data):
        dr = AnalyticsDateRange.from_params(preset="all_time")

        with CaptureQueriesContext(connection) as ctx:
            summary = AnalyticsService.get_dashboard_summary(dr)

        # Dashboard summary executes in exactly 5 database queries:
        # 1. Leads aggregate
        # 2. Bookings aggregate
        # 3. Channel breakdown group-by
        # 4. Popular services group-by
        # 5. Timeseries group-by
        query_count = len(ctx.captured_queries)
        assert query_count <= 5, f"Expected <= 5 queries for full dashboard summary, got {query_count}"
        assert summary["leads"]["total_leads"] == 5
        assert summary["bookings"]["total_bookings"] == 4


@pytest.mark.django_db
class TestAnalyticsAdminAPIEndpoints:
    """Tests DRF REST API endpoints for dashboard, leads, bookings, and services analytics."""

    def setup_method(self):
        self.client = APIClient()

    def test_unauthenticated_access_is_rejected(self):
        url = reverse("api_v1:analytics:dashboard-summary")
        res = self.client.get(url)
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dashboard_summary_endpoint(self, admin_user, analytics_test_data):
        self.client.force_authenticate(user=admin_user)
        url = reverse("api_v1:analytics:dashboard-summary")
        res = self.client.get(url, {"preset": "all_time"})

        assert res.status_code == status.HTTP_200_OK
        assert "leads" in res.data
        assert "bookings" in res.data
        assert "lead_source_breakdown" in res.data
        assert "popular_services" in res.data
        assert res.data["leads"]["total_leads"] == 5
        assert res.data["bookings"]["total_bookings"] == 4

    def test_leads_analytics_endpoint(self, admin_user, analytics_test_data):
        self.client.force_authenticate(user=admin_user)
        url = reverse("api_v1:analytics:leads-analytics")
        res = self.client.get(url, {"preset": "all_time"})

        assert res.status_code == status.HTTP_200_OK
        assert res.data["metrics"]["total_leads"] == 5
        assert len(res.data["source_breakdown"]) == 2

    def test_bookings_analytics_endpoint(self, admin_user, analytics_test_data):
        self.client.force_authenticate(user=admin_user)
        url = reverse("api_v1:analytics:bookings-analytics")
        res = self.client.get(url, {"preset": "all_time"})

        assert res.status_code == status.HTTP_200_OK
        assert res.data["metrics"]["total_bookings"] == 4
        assert res.data["metrics"]["confirmed_bookings"] == 2

    def test_services_analytics_endpoint(self, admin_user, analytics_test_data):
        self.client.force_authenticate(user=admin_user)
        url = reverse("api_v1:analytics:services-analytics")
        res = self.client.get(url, {"preset": "all_time", "limit": "3"})

        assert res.status_code == status.HTTP_200_OK
        assert "popular_services" in res.data
        assert len(res.data["popular_services"]) <= 3
