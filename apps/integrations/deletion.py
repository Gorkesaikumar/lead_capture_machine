"""Durable signed-request deletion of locally stored Instagram integration data."""
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import DataDeletionRequest, RawWebhookEvent


def enqueue_deletion(request_id):
    try:
        delete_instagram_data.delay(str(request_id))
    except Exception:
        pass  # Durable request is recovered by beat, never falsely marked complete.


@shared_task
@transaction.atomic
def delete_instagram_data(request_id):
    from apps.conversations.models import Conversation, MessageReceipt
    from apps.customers.models import Customer, CustomerIdentity
    from apps.leads.models import Lead
    from apps.notifications.models import Notification
    receipt = DataDeletionRequest.objects.select_for_update().get(pk=request_id)
    if receipt.status == "COMPLETED":
        return
    for scope in receipt.scopes:
        org, account = scope["organization"], scope["account"]
        customer_ids = list(CustomerIdentity.objects.filter(organization_id=org, channel="INSTAGRAM").values_list("customer_id", flat=True))
        Conversation.objects.filter(organization_id=org, channel="INSTAGRAM").delete()
        MessageReceipt.objects.filter(organization_id=org, channel="INSTAGRAM").delete()
        Notification.objects.filter(customer__organization_id=org, channel="INSTAGRAM").delete()
        Lead.objects.filter(organization_id=org, source_channel="INSTAGRAM").delete()
        CustomerIdentity.objects.filter(organization_id=org, channel="INSTAGRAM").delete()
        for customer in Customer.objects.filter(organization_id=org, pk__in=customer_ids):
            if not customer.identities.exists() and not customer.leads.exists() and not customer.bookings.exists():
                customer.delete()
        # Mixed account batches preserve every unrelated entry.
        for event in RawWebhookEvent.objects.filter(channel="INSTAGRAM").iterator():
            entries = event.payload.get("entry", [])
            remaining = [entry for entry in entries if str(entry.get("id", "")) != account and not any(str(m.get("recipient", {}).get("id", "")) == account for m in entry.get("messaging", []))]
            if len(remaining) != len(entries):
                if remaining:
                    event.payload = {**event.payload, "entry": remaining}
                    event.signature = ""
                    event.save(update_fields=["payload", "signature", "updated_at"])
                else:
                    event.delete()
    receipt.status = "COMPLETED"
    receipt.scopes = []
    receipt.completed_at = timezone.now()
    receipt.save(update_fields=["status", "scopes", "completed_at", "updated_at"])


@shared_task
def recover_deletion_requests():
    for request_id in DataDeletionRequest.objects.filter(status="PENDING").values_list("pk", flat=True)[:100]:
        enqueue_deletion(request_id)


class DataDeletionStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, code):
        receipt = get_object_or_404(DataDeletionRequest, pk=code)
        return Response({"confirmation_code": str(receipt.pk), "status": receipt.status, "completed_at": receipt.completed_at})
