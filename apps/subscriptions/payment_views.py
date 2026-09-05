import hashlib
import hmac
import json
import re
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.organizations.permissions import IsOrganizationAdmin
from .models import BillingTransaction, PaymentWebhookEvent
from .serializers import SubscriptionSerializer
from .payments import create_order, verify_checkout, apply_capture


class CheckoutInput(serializers.Serializer):
    product = serializers.ChoiceField(choices=["plan", "dm_automation"], default="plan")
    plan_code = serializers.CharField(max_length=50, allow_blank=True, default="")
    country = serializers.ChoiceField(choices=["IN", "US"], default="IN")


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        fields = CheckoutInput(data=request.data)
        fields.is_valid(raise_exception=True)
        return Response(create_order(request.organization, **fields.validated_data))


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        data = request.data
        sub = verify_checkout(request.organization, data.get("provider_order_id"),
            data.get("provider_payment_id"), data.get("provider_signature"))
        return Response({"message": "Payment verified. Paid access is active.", "subscription": SubscriptionSerializer(sub).data})


class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request):
        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
        if not secret:
            return Response({"detail": "Payment webhook is not configured."}, status=503)
        body = request.body
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        signature = request.headers.get("X-Razorpay-Signature", "")
        if not re.fullmatch(r"[0-9a-f]{64}", signature) or not hmac.compare_digest(expected, signature):
            return Response({"detail": "Invalid payment signature."}, status=403)
        try:
            payload = json.loads(body)
            payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
            event_type = payload.get("event", "")
            if not isinstance(payment, dict):
                raise ValueError()
        except (ValueError, AttributeError):
            return Response({"detail": "Invalid payment event."}, status=400)
        if event_type not in ("payment.captured", "order.paid"):
            return Response({"status": "ignored"})
        tx = BillingTransaction.objects.filter(provider="razorpay", provider_order_id=payment.get("order_id"),
            payment_metadata__price_verified=True).first()
        if not tx:
            return Response({"status": "unknown_order"})
        # Persist only the fields needed for billing reconciliation, not payer contact data.
        minimal = {k: payment.get(k) for k in ("id", "order_id", "amount", "currency", "status")}
        event_id = "razorpay:" + hashlib.sha256(body).hexdigest()
        with transaction.atomic():
            event, _ = PaymentWebhookEvent.objects.get_or_create(event_id=event_id,
                defaults={"provider": "razorpay", "event_type": event_type, "payload": minimal})
            if event.is_processed:
                return Response({"status": "already_processed"})
            apply_capture(tx.pk, payment)
            event.is_processed, event.processed_at = True, timezone.now()
            event.save()
        return Response({"status": "processed"})
