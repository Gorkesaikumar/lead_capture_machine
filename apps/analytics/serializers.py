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
    qualified_leads = serializers.IntegerField()
    booking_links_sent = serializers.IntegerField()
    converted_leads = serializers.IntegerField()
    lead_to_booking_conversion_rate = serializers.FloatField()


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
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()

class DashboardSummarySerializer(serializers.Serializer):
    date_range = DateRangeInfoSerializer()
    leads = LeadsMetricsSerializer()
    bookings = BookingsMetricsSerializer()
    lead_source_breakdown = SourceBreakdownItemSerializer(many=True)
    popular_services = PopularServiceItemSerializer(many=True)
    timeseries = TimeseriesItemSerializer(many=True)

