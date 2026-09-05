"""
DRF Serializers for backend analytics responses.
"""
from rest_framework import serializers


class DateRangeInfoSerializer(serializers.Serializer):
    preset = serializers.CharField(allow_null=True)
    start = serializers.CharField(allow_null=True)
    end = serializers.CharField(allow_null=True)


class LeadsMetricsSerializer(serializers.Serializer):
    total_leads = serializers.IntegerField()
    new_leads_today = serializers.IntegerField()
    instagram_leads = serializers.IntegerField()
    whatsapp_leads = serializers.IntegerField()
    website_leads = serializers.IntegerField()
    open_conversations = serializers.IntegerField()
    qualified_leads = serializers.IntegerField()
    booking_links_sent = serializers.IntegerField()
    converted_leads = serializers.IntegerField()
    lead_to_booking_conversion_rate = serializers.FloatField()
    status_new = serializers.IntegerField()
    status_contacted = serializers.IntegerField()
    status_qualified = serializers.IntegerField()
    status_lost = serializers.IntegerField()


class BookingsMetricsSerializer(serializers.Serializer):
    total_bookings = serializers.IntegerField()
    bookings_today = serializers.IntegerField()
    bookings_tomorrow = serializers.IntegerField()
    upcoming_bookings = serializers.IntegerField()
    completed_bookings = serializers.IntegerField()
    cancelled_bookings = serializers.IntegerField()
    confirmed_bookings = serializers.IntegerField()
    pending_bookings = serializers.IntegerField()
    no_show_bookings = serializers.IntegerField()


class SourceBreakdownItemSerializer(serializers.Serializer):
    source_channel = serializers.CharField()
    total_leads = serializers.IntegerField()
    share_percentage = serializers.FloatField()
    qualified_leads = serializers.IntegerField()
    converted_leads = serializers.IntegerField()
    conversion_rate_percentage = serializers.FloatField()


class PopularServiceItemSerializer(serializers.Serializer):
    service_id = serializers.CharField()
    service_name = serializers.CharField()
    service_slug = serializers.CharField()
    booking_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    share_percentage = serializers.FloatField()
    estimated_revenue = serializers.FloatField()



class TimeseriesItemSerializer(serializers.Serializer):
    date = serializers.CharField()
    total = serializers.IntegerField()
    completed = serializers.IntegerField(required=False)
    cancelled = serializers.IntegerField(required=False)
    converted = serializers.IntegerField(required=False)


class LeadTimeseriesItemSerializer(TimeseriesItemSerializer):
    instagram = serializers.IntegerField()
    whatsapp = serializers.IntegerField()
    website = serializers.IntegerField()
    other = serializers.IntegerField()


class DashboardChannelSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    status = serializers.CharField()
    leadCount = serializers.IntegerField()


class DashboardActivitySerializer(serializers.Serializer):
    id = serializers.CharField()
    lead_id = serializers.CharField()
    type = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True)
    created_at = serializers.CharField()


class DashboardSummarySerializer(serializers.Serializer):
    date_range = DateRangeInfoSerializer()
    leads = LeadsMetricsSerializer()
    bookings = BookingsMetricsSerializer()
    lead_source_breakdown = SourceBreakdownItemSerializer(many=True)
    popular_services = PopularServiceItemSerializer(many=True)
    timeseries = TimeseriesItemSerializer(many=True)
    leads_timeseries = LeadTimeseriesItemSerializer(many=True)
    channels = DashboardChannelSerializer(many=True)
    recent_leads = serializers.ListField(child=serializers.DictField())
    activities = DashboardActivitySerializer(many=True)
    generated_at = serializers.CharField()
    timezone = serializers.CharField()

