"""
Admin API views for monitoring and managing outbound notifications.
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.customers.models import Customer
from apps.notifications.models import Notification
from apps.notifications.serializers import (
    NotificationCreateSerializer,
    NotificationSerializer,
)
from apps.notifications.services import NotificationService


class NotificationListView(generics.ListCreateAPIView):
    """
    GET: List notifications with filtering by channel, status, type, and customer.
    POST: Ad-hoc creation and dispatch of a notification by studio admin.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = Notification.objects.select_related("customer").all()
        channel = self.request.query_params.get("channel")
        status_filter = self.request.query_params.get("status")
        notif_type = self.request.query_params.get("notification_type")
        customer_id = self.request.query_params.get("customer_id")

        if channel:
            qs = qs.filter(channel=channel.upper())
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if notif_type:
            qs = qs.filter(notification_type=notif_type.upper())
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            customer = Customer.objects.get(id=data["customer_id"])
        except Customer.DoesNotExist:
            return Response({"detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        notification, was_created = NotificationService.send_notification(
            customer=customer,
            channel=data.get("channel") or NotificationService._detect_best_channel(customer),
            notification_type=data.get("notification_type", Notification.NotificationType.GENERAL),
            context=data.get("context", {}),
            idempotency_key=data.get("idempotency_key") or None,
            async_delivery=True,
        )

        resp_serializer = NotificationSerializer(notification)
        http_status = status.HTTP_201_CREATED if was_created else status.HTTP_200_OK
        return Response(resp_serializer.data, status=http_status)


class NotificationDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve detailed notification record by ID.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    queryset = Notification.objects.select_related("customer").all()


class NotificationRetryView(APIView):
    """
    POST: Manually trigger a retry for a failed notification.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            notification = Notification.objects.get(id=pk)
        except Notification.DoesNotExist:
            return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)

        # Clear permanent error flag for manual retry
        notification.is_permanent_error = False
        notification.status = Notification.Status.PENDING
        notification.save(update_fields=["is_permanent_error", "status", "updated_at"])

        try:
            updated = NotificationService.dispatch_now(str(notification.id))
            return Response(NotificationSerializer(updated).data, status=status.HTTP_200_OK)
        except Exception as exc:
            notification.refresh_from_db()
            return Response(
                {
                    "detail": f"Retry failed: {str(exc)}",
                    "notification": NotificationSerializer(notification).data,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
