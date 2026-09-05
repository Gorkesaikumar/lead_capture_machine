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
from .models import PaymentWebhookEvent
from .payments import account_scope
from .recurring import create_recurring, verify_recurring, reconcile_agreement, cancel_recurring, agreements
from .serializers import SubscriptionSerializer


class RecurringInput(serializers.Serializer):
    product = serializers.ChoiceField(choices=["plan", "dm_automation"], default="plan")
    plan_code = serializers.CharField(max_length=50, allow_blank=True, default="")
    country = serializers.ChoiceField(choices=["IN", "US"], default="IN")
    accept_recurring = serializers.BooleanField()

    def validate_accept_recurring(self, value):
        if value is not True: raise serializers.ValidationError("Monthly automatic renewal must be accepted.")
        return value


class RecurringCheckoutView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]
    throttle_scope = "billing"
    def post(self, request):
        serializer = RecurringInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = dict(serializer.validated_data)
        fields.pop("accept_recurring")
        return Response(create_recurring(request.organization, **fields))


class RecurringVerifyView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]
    throttle_scope = "billing"
    def post(self, request):
        result = verify_recurring(request.organization, request.data.get("provider_subscription_id"),
            request.data.get("provider_payment_id"), request.data.get("provider_signature"))
        paid = result.charges.filter(period_start__lte=timezone.now(), period_end__gt=timezone.now(),
            transaction__status__in=["success", "partially_refunded"]).exists()
        return Response({"status": result.status, "paid": paid,
            "message": "Payment verified. Paid access is active." if paid else "Mandate confirmed. Access will activate after the first full payment is captured.",
            "subscription": SubscriptionSerializer(request.organization.subscription, context={"request": request}).data})


class RecurringSyncView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]
    throttle_scope = "billing"
    def post(self, request):
        from django.utils import timezone
        from .recurring import TERMINAL
        # A bounded explicit recovery action; the periodic task handles older ledgers.
        pending = agreements(request.organization).exclude(status__in=TERMINAL).order_by("created_at")[:5]
        for agreement in pending:
            reconcile_agreement(agreement.pk)
        return Response({"message": "Payment status updated.", "checked_at": timezone.now(),
            "subscription": SubscriptionSerializer(request.organization.subscription, context={"request": request}).data})


class RecurringCancelView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]
    throttle_scope = "billing"
    def post(self, request):
        product = request.data.get("product", "plan")
        if product not in ("plan", "dm_automation"):
            raise serializers.ValidationError("Invalid billing product.")
        return Response(cancel_recurring(request.organization, product))


class RecurringWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    def post(self, request):
        secret = settings.RAZORPAY_WEBHOOK_SECRET
        if not secret: return Response({"detail": "Payment webhook is not configured."}, status=503)
        body = request.body
        if len(body) > 256 * 1024: return Response({"detail": "Event too large."}, status=413)
        signature = request.headers.get("X-Razorpay-Signature", "")
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not re.fullmatch(r"[0-9a-f]{64}", signature) or not hmac.compare_digest(expected, signature):
            return Response({"detail": "Invalid payment signature."}, status=403)
        try:
            payload = json.loads(body)
            event_type = payload.get("event", "")
            entities = payload.get("payload", {})
            sub = entities.get("subscription", {}).get("entity", {})
            payment = entities.get("payment", {}).get("entity", {})
            invoice = entities.get("invoice", {}).get("entity", {})
            refund = entities.get("refund", {}).get("entity", {})
            minimal = {"account_scope": account_scope(), "subscription_id": sub.get("id") or invoice.get("subscription_id"),
                "invoice_id": invoice.get("id") or payment.get("invoice_id"),
                "payment_id": payment.get("id") or refund.get("payment_id"),
                "order_id": payment.get("order_id"), "event_type": event_type}
        except (ValueError, AttributeError, TypeError):
            return Response({"detail": "Invalid event."}, status=400)
        supported = {"subscription." + state for state in ("authenticated", "activated", "charged", "pending", "halted", "cancelled", "completed", "paused", "resumed", "updated")}
        supported |= {"invoice.paid", "payment.captured", "payment.failed", "payment.refunded", "refund.processed", "order.paid"}
        if event_type not in supported: return Response({"status": "ignored"})
        if not minimal["subscription_id"] and not minimal["invoice_id"] and minimal["order_id"]:
            from .models import BillingTransaction
            if BillingTransaction.objects.filter(provider_order_id=minimal["order_id"], payment_metadata__price_verified=True).exists():
                from .payment_views import RazorpayWebhookView
                return RazorpayWebhookView().post(request)
        # Header is Razorpay's event identity; prefixing scopes it to the configured merchant.
        event_id = request.headers.get("X-Razorpay-Event-Id") or hashlib.sha256(body).hexdigest()
        event_id = "recurring:" + account_scope()[:16] + ":" + hashlib.sha256(event_id.encode()).hexdigest()
        from .tasks import enqueue_webhook
        with transaction.atomic():
            event, _ = PaymentWebhookEvent.objects.get_or_create(event_id=event_id,
                defaults={"provider": "razorpay", "event_type": event_type, "payload": minimal})
            if event.is_processed: return Response({"status": "already_processed"})
            transaction.on_commit(lambda: enqueue_webhook(str(event.pk)))
        return Response({"status": "accepted"})
