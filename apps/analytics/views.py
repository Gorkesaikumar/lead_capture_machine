"""
DRF Views for Backend Analytics and Dashboard APIs.
"""
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.analytics.serializers import (
    BookingsMetricsSerializer,
    DashboardSummarySerializer,
    LeadsMetricsSerializer,
    PopularServiceItemSerializer,
    SourceBreakdownItemSerializer,
)
from apps.analytics.services import AnalyticsDateRange, AnalyticsService
from apps.organizations.permissions import IsOrganizationMember


class DashboardSummaryAPIView(APIView):
    """
    GET /api/v1/analytics/dashboard/
    GET /api/v1/analytics/summary/
    Returns aggregated dashboard metrics including lead volume, conversion, bookings, and services.
    """
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get(self, request, *args, **kwargs):
        if not hasattr(request, "organization") or not request.organization:
            raise PermissionDenied("An active organization context is required.")

        date_range = AnalyticsDateRange.from_params(
            start_date=request.query_params.get("start_date"),
            end_date=request.query_params.get("end_date"),
            preset=request.query_params.get("preset"),
        )
        data = AnalyticsService.get_dashboard_summary(date_range, request.organization)
        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeadsAnalyticsAPIView(APIView):
    """
    GET /api/v1/analytics/leads/
    Returns lead volume, channel counts, and conversion metrics.
    """
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get(self, request, *args, **kwargs):
        if not hasattr(request, "organization") or not request.organization:
            raise PermissionDenied("An active organization context is required.")

        date_range = AnalyticsDateRange.from_params(
            start_date=request.query_params.get("start_date"),
            end_date=request.query_params.get("end_date"),
            preset=request.query_params.get("preset"),
        )
        leads_data = AnalyticsService.get_leads_metrics(date_range, request.organization)
        sources_data = AnalyticsService.get_lead_source_breakdown(date_range, request.organization)

        return Response(
            {
                "date_range": {
                    "preset": date_range.preset,
                    "start": date_range.start_datetime.isoformat() if date_range.start_datetime else None,
                    "end": date_range.end_datetime.isoformat() if date_range.end_datetime else None,
                },
                "metrics": LeadsMetricsSerializer(leads_data).data,
                "source_breakdown": SourceBreakdownItemSerializer(sources_data, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class BookingsAnalyticsAPIView(APIView):
    """
    GET /api/v1/analytics/bookings/
    Returns booking counts, statuses, and upcoming session calendar figures.
    """
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get(self, request, *args, **kwargs):
        if not hasattr(request, "organization") or not request.organization:
            raise PermissionDenied("An active organization context is required.")

        date_range = AnalyticsDateRange.from_params(
            start_date=request.query_params.get("start_date"),
            end_date=request.query_params.get("end_date"),
            preset=request.query_params.get("preset"),
        )
        bookings_data = AnalyticsService.get_bookings_metrics(date_range, request.organization)

        return Response(
            {
                "date_range": {
                    "preset": date_range.preset,
                    "start": date_range.start_datetime.isoformat() if date_range.start_datetime else None,
                    "end": date_range.end_datetime.isoformat() if date_range.end_datetime else None,
                },
                "metrics": BookingsMetricsSerializer(bookings_data).data,
            },
            status=status.HTTP_200_OK,
        )


class ServicesAnalyticsAPIView(APIView):
    """
    GET /api/v1/analytics/services/
    Returns rankings of photography services by booking count and revenue.
    """
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]

    def get(self, request, *args, **kwargs):
        if not hasattr(request, "organization") or not request.organization:
            raise PermissionDenied("An active organization context is required.")

        date_range = AnalyticsDateRange.from_params(
            start_date=request.query_params.get("start_date"),
            end_date=request.query_params.get("end_date"),
            preset=request.query_params.get("preset"),
        )
        limit = int(request.query_params.get("limit", 10))
        services_data = AnalyticsService.get_popular_services(date_range, request.organization, limit=limit)

        return Response(
            {
                "date_range": {
                    "preset": date_range.preset,
                    "start": date_range.start_datetime.isoformat() if date_range.start_datetime else None,
                    "end": date_range.end_datetime.isoformat() if date_range.end_datetime else None,
                },
                "popular_services": PopularServiceItemSerializer(services_data, many=True).data,
            },
            status=status.HTTP_200_OK,
        )
