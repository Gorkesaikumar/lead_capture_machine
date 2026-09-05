"""
Analytics aggregation engine and date range calculation utilities.
Uses PostgreSQL conditional aggregations for sub-millisecond query execution.
"""
from dataclasses import dataclass
from datetime import datetime, time, timedelta
import logging
from typing import Any, Dict, List, Optional
from django.db.models import Case, Count, F, FloatField, Q, Sum, Value, When
from django.utils import timezone
from apps.bookings.models import Booking
from apps.leads.models import Lead, LeadActivity, LeadForm
from apps.services.models import PhotographyService

logger = logging.getLogger("apps.analytics")


@dataclass
class AnalyticsDateRange:
    """
    Encapsulates start and end timestamps for analytics queries.
    """
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    preset: Optional[str] = None

    @classmethod
    def from_params(
        cls,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        preset: Optional[str] = None,
    ) -> "AnalyticsDateRange":
        """
        Parses query parameters into a validated date range.
        Supports presets: 'today', 'yesterday', '7d', '30d', 'this_month', 'last_month', 'this_year', 'all_time'.
        """
        now = timezone.localtime()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1) - timedelta(microseconds=1)

        preset_clean = (preset or "").strip().lower()

        if preset_clean == "today":
            return cls(start_datetime=today_start, end_datetime=today_end, preset="today")

        elif preset_clean == "yesterday":
            yesterday_start = today_start - timedelta(days=1)
            yesterday_end = today_start - timedelta(microseconds=1)
            return cls(start_datetime=yesterday_start, end_datetime=yesterday_end, preset="yesterday")

        elif preset_clean in ["7d", "last_7_days"]:
            seven_days_ago = today_start - timedelta(days=6)
            return cls(start_datetime=seven_days_ago, end_datetime=now, preset="7d")

        elif preset_clean in ["30d", "last_30_days"]:
            thirty_days_ago = today_start - timedelta(days=29)
            return cls(start_datetime=thirty_days_ago, end_datetime=now, preset="30d")

        elif preset_clean == "this_month":
            month_start = today_start.replace(day=1)
            return cls(start_datetime=month_start, end_datetime=now, preset="this_month")

        elif preset_clean == "last_month":
            first_this_month = today_start.replace(day=1)
            last_day_prev_month = first_this_month - timedelta(days=1)
            month_start = last_day_prev_month.replace(day=1)
            month_end = first_this_month - timedelta(microseconds=1)
            return cls(start_datetime=month_start, end_datetime=month_end, preset="last_month")

        elif preset_clean == "this_year":
            year_start = today_start.replace(month=1, day=1)
            return cls(start_datetime=year_start, end_datetime=now, preset="this_year")

        elif preset_clean == "all_time":
            return cls(start_datetime=None, end_datetime=None, preset="all_time")

        # Explicit date parsing (YYYY-MM-DD)
        start_dt = None
        end_dt = None
        current_tz = timezone.get_current_timezone()

        if start_date:
            try:
                d = datetime.strptime(start_date, "%Y-%m-%d").date()
                start_dt = timezone.make_aware(datetime.combine(d, time.min))
            except (ValueError, TypeError):
                logger.warning("Invalid start_date format: %s", start_date)

        if end_date:
            try:
                d = datetime.strptime(end_date, "%Y-%m-%d").date()
                end_dt = timezone.make_aware(datetime.combine(d, time.min)) + timedelta(days=1) - timedelta(microseconds=1)
            except (ValueError, TypeError):
                logger.warning("Invalid end_date format: %s", end_date)

        # Default fallback: all_time if neither preset nor dates provided
        preset_name = "custom" if (start_dt or end_dt) else "all_time"
        return cls(start_datetime=start_dt, end_datetime=end_dt, preset=preset_name)


from apps.conversations.models import Conversation

class AnalyticsService:
    """
    High-performance backend analytics engine.
    Calculates aggregated CRM and scheduling metrics using PostgreSQL database aggregations.
    """

    @classmethod
    def get_dashboard_summary(cls, date_range: AnalyticsDateRange, organization) -> Dict[str, Any]:
        """
        Generates full summary of business metrics for the Admin Dashboard.
        """
        leads_metrics = cls.get_leads_metrics(date_range, organization)
        bookings_metrics = cls.get_bookings_metrics(date_range, organization)
        source_breakdown = cls.get_lead_source_breakdown(
            date_range, organization, total_leads_all=leads_metrics["total_leads"]
        )
        popular_services = cls.get_popular_services(
            date_range, organization, total_bookings_all=bookings_metrics["total_bookings"], limit=5
        )
        timeseries = cls.get_bookings_timeseries(date_range, organization)
        leads_timeseries = cls.get_leads_timeseries(date_range, organization)

        return {
            "date_range": {
                "preset": date_range.preset,
                "start": date_range.start_datetime.isoformat() if date_range.start_datetime else None,
                "end": date_range.end_datetime.isoformat() if date_range.end_datetime else None,
            },
            "leads": leads_metrics,
            "bookings": bookings_metrics,
            "lead_source_breakdown": source_breakdown,
            "popular_services": popular_services,
            "timeseries": timeseries,
            "leads_timeseries": leads_timeseries,
            "channels": cls.get_channels(organization, leads_metrics),
            "recent_leads": cls.get_recent_leads(date_range, organization),
            "activities": cls.get_activities(date_range, organization),
            "generated_at": timezone.now().isoformat(),
            "timezone": timezone.get_current_timezone_name(),
        }

    @staticmethod
    def _in_period(queryset, date_range):
        if date_range.start_datetime:
            queryset = queryset.filter(created_at__gte=date_range.start_datetime)
        if date_range.end_datetime:
            queryset = queryset.filter(created_at__lte=date_range.end_datetime)
        return queryset

    @classmethod
    def get_recent_leads(cls, date_range, organization):
        from apps.leads.serializers import LeadListSerializer
        leads = cls._in_period(Lead.objects.filter(organization=organization, is_deleted=False), date_range)
        return LeadListSerializer(leads.select_related("customer", "service", "assigned_staff", "trigger__service").order_by("-created_at", "-id")[:5], many=True).data

    @classmethod
    def get_activities(cls, date_range, organization):
        activities = cls._in_period(LeadActivity.objects.filter(
            lead__organization=organization, lead__is_deleted=False,
        ), date_range).select_related("lead__customer").order_by("-created_at", "-id")[:5]
        return [{
            "id": str(item.id), "lead_id": str(item.lead_id),
            "type": item.lead.source_channel.lower(),
            "title": item.get_activity_type_display(),
            "subtitle": item.lead.customer.display_name,
            "created_at": item.created_at.isoformat(),
        } for item in activities]

    @staticmethod
    def get_channels(organization, metrics):
        # Read the same persisted connection state as the Channels screen; no
        # provider calls or token refreshes are performed by dashboard polling.
        from apps.integrations.models import IntegrationConfig
        from apps.conversations.outbound import configuration_status
        configs = {c.provider: c for c in IntegrationConfig.objects.filter(organization=organization)}
        result = []
        for provider, name in (("INSTAGRAM", "Instagram Direct"), ("WHATSAPP", "WhatsApp Business")):
            state, _ = configuration_status(configs.get(provider))
            result.append({"id": provider.lower(), "name": name, "type": provider.lower(),
                           "status": state, "leadCount": metrics[f"{provider.lower()}_leads"]})
        result.append({"id": "website", "name": "Website Forms", "type": "website",
                       "status": "ACTIVE" if LeadForm.objects.filter(organization=organization, is_active=True, is_deleted=False).exists() else "NOT_CONFIGURED",
                       "leadCount": metrics["website_leads"]})
        return result

    @classmethod
    def get_leads_metrics(cls, date_range: AnalyticsDateRange, organization) -> Dict[str, Any]:
        """
        Aggregates lead volume, channel counts, qualification counts, and conversion rate.
        """
        qs = Lead.objects.filter(organization=organization, is_deleted=False)
        if date_range.start_datetime:
            qs = qs.filter(created_at__gte=date_range.start_datetime)
        if date_range.end_datetime:
            qs = qs.filter(created_at__lte=date_range.end_datetime)

        now = timezone.localtime()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # Open Conversations
        open_conversations = Conversation.objects.filter(
            organization=organization, is_deleted=False,
            status=Conversation.Status.ACTIVE
        ).count()

        # Single DB query conditional aggregate
        agg = qs.aggregate(
            total_leads=Count("id"),
            instagram_leads=Count("id", filter=Q(source_channel="INSTAGRAM")),
            whatsapp_leads=Count("id", filter=Q(source_channel="WHATSAPP")),
            website_leads=Count("id", filter=Q(source_channel="WEBSITE")),
            qualified_leads=Count(
                "id",
                filter=Q(status__in=[Lead.Status.QUALIFIED, Lead.Status.CONVERTED])
                | Q(qualified_at__isnull=False),
            ),
            converted_leads=Count(
                "id",
                filter=Q(status=Lead.Status.CONVERTED),
            ),
            new_leads_today=Count(
                "id",
                filter=Q(created_at__gte=today_start, created_at__lt=today_end),
            ),
            status_new=Count("id", filter=Q(status=Lead.Status.NEW)),
            status_contacted=Count("id", filter=Q(status=Lead.Status.CONTACTED)),
            status_qualified=Count("id", filter=Q(status=Lead.Status.QUALIFIED)),
            status_lost=Count("id", filter=Q(status=Lead.Status.LOST)),
        )

        total = agg["total_leads"] or 0
        converted = agg["converted_leads"] or 0
        conversion_rate = round((converted / total * 100), 2) if total > 0 else 0.0

        return {
            "total_leads": total,
            "new_leads_today": agg["new_leads_today"] or 0,
            "instagram_leads": agg["instagram_leads"] or 0,
            "whatsapp_leads": agg["whatsapp_leads"] or 0,
            "website_leads": agg["website_leads"] or 0,
            "open_conversations": open_conversations,
            "qualified_leads": agg["qualified_leads"] or 0,
            "booking_links_sent": cls._booking_links_sent(organization, date_range),
            "converted_leads": converted,
            "lead_to_booking_conversion_rate": conversion_rate,
            "status_new": agg["status_new"] or 0,
            "status_contacted": agg["status_contacted"] or 0,
            "status_qualified": agg["status_qualified"] or 0,
            "status_lost": agg["status_lost"] or 0,
        }

    @staticmethod
    def _booking_links_sent(organization, date_range):
        from apps.notifications.models import Notification
        sent = Notification.objects.filter(customer__organization=organization, notification_type="BOOKING_LINK", status__in=["SENT", "DELIVERED", "READ"])
        if date_range.start_datetime:
            sent = sent.filter(sent_at__gte=date_range.start_datetime)
        if date_range.end_datetime:
            sent = sent.filter(sent_at__lte=date_range.end_datetime)
        return sent.count()

    @classmethod
    def get_bookings_metrics(cls, date_range: AnalyticsDateRange, organization) -> Dict[str, Any]:
        """
        Aggregates booking volume, calendar day metrics, and statuses.
        """
        qs = Booking.objects.filter(customer__organization=organization, is_deleted=False)
        if date_range.start_datetime:
            qs = qs.filter(created_at__gte=date_range.start_datetime)
        if date_range.end_datetime:
            qs = qs.filter(created_at__lte=date_range.end_datetime)

        now = timezone.localtime()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        tomorrow_start = today_end
        tomorrow_end = tomorrow_start + timedelta(days=1)

        # Single DB query conditional aggregate
        agg = qs.aggregate(
            total_bookings=Count("id"),
            pending_bookings=Count("id", filter=Q(status=Booking.Status.PENDING)),
            confirmed_bookings=Count("id", filter=Q(status=Booking.Status.CONFIRMED)),
            completed_bookings=Count("id", filter=Q(status=Booking.Status.COMPLETED)),
            cancelled_bookings=Count("id", filter=Q(status=Booking.Status.CANCELLED)),
            no_show_bookings=Count("id", filter=Q(status=Booking.Status.NO_SHOW)),
            # Calendar queries relative to current studio date
            bookings_today=Count(
                "id",
                filter=Q(starts_at__gte=today_start, starts_at__lt=today_end)
                & ~Q(status=Booking.Status.CANCELLED),
            ),
            bookings_tomorrow=Count(
                "id",
                filter=Q(starts_at__gte=tomorrow_start, starts_at__lt=tomorrow_end)
                & ~Q(status=Booking.Status.CANCELLED),
            ),
            upcoming_bookings=Count(
                "id",
                filter=Q(starts_at__gte=now, status__in=[Booking.Status.CONFIRMED, Booking.Status.PENDING]),
            ),
        )

        return {
            "total_bookings": agg["total_bookings"] or 0,
            "bookings_today": agg["bookings_today"] or 0,
            "bookings_tomorrow": agg["bookings_tomorrow"] or 0,
            "upcoming_bookings": agg["upcoming_bookings"] or 0,
            "completed_bookings": agg["completed_bookings"] or 0,
            "cancelled_bookings": agg["cancelled_bookings"] or 0,
            "confirmed_bookings": agg["confirmed_bookings"] or 0,
            "pending_bookings": agg["pending_bookings"] or 0,
            "no_show_bookings": agg["no_show_bookings"] or 0,
        }

    @classmethod
    def get_lead_source_breakdown(
        cls, date_range: AnalyticsDateRange, organization, total_leads_all: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Groups leads by source channel (Instagram / WhatsApp / Website) and computes conversion by source.
        """
        qs = Lead.objects.filter(organization=organization, is_deleted=False)
        if date_range.start_datetime:
            qs = qs.filter(created_at__gte=date_range.start_datetime)
        if date_range.end_datetime:
            qs = qs.filter(created_at__lte=date_range.end_datetime)

        groups = list(
            qs.values("source_channel")
            .annotate(
                total=Count("id"),
                converted=Count(
                    "id",
                    filter=Q(status=Lead.Status.CONVERTED),
                ),
                qualified=Count(
                    "id",
                    filter=Q(
                        status__in=[
                            Lead.Status.QUALIFIED,
                            Lead.Status.CONVERTED,
                        ]
                    )
                    | Q(qualified_at__isnull=False),
                ),
            )
            .order_by("-total")
        )

        if total_leads_all is None:
            total_leads_all = sum(g["total"] for g in groups)

        results = []
        for g in groups:
            channel = g["source_channel"] or "UNKNOWN"
            count = g["total"]
            conv = g["converted"]
            qual = g["qualified"]

            share_pct = round((count / total_leads_all * 100), 2) if total_leads_all > 0 else 0.0
            conv_rate = round((conv / count * 100), 2) if count > 0 else 0.0

            results.append({
                "source_channel": channel,
                "total_leads": count,
                "share_percentage": share_pct,
                "qualified_leads": qual,
                "converted_leads": conv,
                "conversion_rate_percentage": conv_rate,
            })

        return results

    @classmethod
    def get_popular_services(
        cls,
        date_range: AnalyticsDateRange,
        organization,
        total_bookings_all: Optional[int] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Ranks photography services by active bookings and completed sessions.
        """
        qs = Booking.objects.filter(customer__organization=organization, is_deleted=False).exclude(status=Booking.Status.CANCELLED)
        if date_range.start_datetime:
            qs = qs.filter(created_at__gte=date_range.start_datetime)
        if date_range.end_datetime:
            qs = qs.filter(created_at__lte=date_range.end_datetime)

        service_groups = list(
            qs.values("service__id", "service__name", "service__slug", "service__base_price")
            .annotate(
                booking_count=Count("id"),
                completed_count=Count("id", filter=Q(status=Booking.Status.COMPLETED)),
            )
            .order_by("-booking_count")[:limit]
        )

        if total_bookings_all is None:
            total_bookings_all = sum(sg["booking_count"] for sg in service_groups)

        results = []
        for sg in service_groups:
            if not sg["service__id"]:
                continue

            count = sg["booking_count"]
            share_pct = round((count / total_bookings_all * 100), 2) if total_bookings_all > 0 else 0.0
            base_price = float(sg["service__base_price"] or 0.0)

            results.append({
                "service_id": str(sg["service__id"]),
                "service_name": sg["service__name"],
                "service_slug": sg["service__slug"],
                "booking_count": count,
                "completed_count": sg["completed_count"],
                "share_percentage": share_pct,
                "estimated_revenue": round(count * base_price, 2),
            })

        return results

    @classmethod
    def get_bookings_timeseries(cls, date_range: AnalyticsDateRange, organization) -> List[Dict[str, Any]]:
        from django.db.models.functions import TruncDate
        qs = Booking.objects.filter(customer__organization=organization, is_deleted=False)
        if date_range.start_datetime:
            qs = qs.filter(created_at__gte=date_range.start_datetime)
        if date_range.end_datetime:
            qs = qs.filter(created_at__lte=date_range.end_datetime)
        
        timeseries = list(
            qs.annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(status=Booking.Status.COMPLETED)),
                cancelled=Count('id', filter=Q(status=Booking.Status.CANCELLED))
            )
            .order_by('date')
        )
        
        results = []
        for row in timeseries:
            if not row['date']:
                continue
            results.append({
                "date": row['date'].isoformat(),
                "total": row['total'],
                "completed": row['completed'],
                "cancelled": row['cancelled']
            })
        return results

    @classmethod
    def get_leads_timeseries(cls, date_range: AnalyticsDateRange, organization) -> List[Dict[str, Any]]:
        from django.db.models.functions import TruncDate
        qs = Lead.objects.filter(organization=organization, is_deleted=False)
        if date_range.start_datetime:
            qs = qs.filter(created_at__gte=date_range.start_datetime)
        if date_range.end_datetime:
            qs = qs.filter(created_at__lte=date_range.end_datetime)

        timeseries = list(
            qs.annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total=Count('id'),
                converted=Count('id', filter=Q(status=Lead.Status.CONVERTED)),
                instagram=Count('id', filter=Q(source_channel="INSTAGRAM")),
                whatsapp=Count('id', filter=Q(source_channel="WHATSAPP")),
                website=Count('id', filter=Q(source_channel="WEBSITE")),
                other=Count('id', filter=~Q(source_channel__in=["INSTAGRAM", "WHATSAPP", "WEBSITE"])),
            )
            .order_by('date')
        )

        results = []
        for row in timeseries:
            if not row['date']:
                continue
            results.append({
                "date": row['date'].isoformat(),
                "total": row['total'],
                "converted": row['converted'],
                "instagram": row['instagram'],
                "whatsapp": row['whatsapp'],
                "website": row['website'],
                "other": row['other'],
            })
        if date_range.start_datetime and date_range.end_datetime:
            first = timezone.localtime(date_range.start_datetime).date()
            last = timezone.localtime(date_range.end_datetime).date()
            if 0 <= (last - first).days <= 366:
                by_date = {row["date"]: row for row in results}
                results = [by_date.get((first + timedelta(days=day)).isoformat(), {
                    "date": (first + timedelta(days=day)).isoformat(),
                    "total": 0, "converted": 0, "instagram": 0,
                    "whatsapp": 0, "website": 0, "other": 0,
                }) for day in range((last - first).days + 1)]
        return results
