import hashlib
import hmac
import json
import logging
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.organizations.permissions import IsOrganizationMember, IsOrganizationAdmin

from apps.subscriptions.models import Plan, Subscription, UsageRecord, BillingTransaction, PaymentWebhookEvent
from apps.subscriptions.serializers import (
    PlanSerializer,
    SubscriptionSerializer,
    BillingTransactionSerializer,
)
from apps.subscriptions.services import (
    SubscriptionEntitlementService,
    CurrencyService,
)

logger = logging.getLogger("apps.subscriptions")


class PlanListView(APIView):
    """
    GET /api/v1/subscriptions/plans/?country=IN
    Returns active plans with prices converted for requested country (INR or USD).
    """
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request, *args, **kwargs):
        SubscriptionEntitlementService.seed_default_plans()

        requested_country = request.query_params.get("country", "").strip().upper()
        country, currency = CurrencyService.resolve_billing_country_and_currency(
            requested_country=requested_country,
            organization=getattr(request, "organization", None),
        )

        plans = Plan.objects.filter(is_active=True).order_by("display_order", "price_usd")
        serializer = PlanSerializer(
            plans,
            many=True,
            context={"country": country, "currency": currency},
        )
        return Response(
            {
                "country": country,
                "currency": currency,
                "plans": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class CurrentSubscriptionView(APIView):
    """
    GET /api/v1/subscriptions/current/
    Returns the active subscription and usage metrics for the request organization.
    """
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if not org and hasattr(request.user, "memberships"):
            membership = request.user.memberships.filter(is_active=True).first()
            if membership:
                org = membership.organization

        if not org:
            return Response(
                {"detail": "No active workspace organization found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        subscription = SubscriptionEntitlementService.get_or_create_active_subscription(org)
        serializer = SubscriptionSerializer(subscription, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CancelSubscriptionView(APIView):
    """
    POST /api/v1/subscriptions/cancel/
    Schedules subscription cancellation at the end of the current billing period.
    """
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        from .recurring import agreements, cancel_recurring, TERMINAL
        if org and agreements(org).exclude(status__in=TERMINAL).exists():
            return Response(cancel_recurring(org))
        if not org and hasattr(request.user, "memberships"):
            membership = request.user.memberships.filter(is_active=True).first()
            if membership:
                org = membership.organization

        if not org or not hasattr(org, "subscription"):
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        subscription = org.subscription
        subscription.cancel_at_period_end = True
        subscription.save()

        return Response(
            {
                "status": "success",
                "message": f"Subscription scheduled for cancellation on {subscription.current_period_end.strftime('%B %d, %Y') if subscription.current_period_end else 'period end'}.",
                "cancel_at_period_end": True,
            },
            status=status.HTTP_200_OK,
        )


class PaymentHistoryView(APIView):
    """
    GET /api/v1/subscriptions/history/
    Returns billing transactions history.
    """
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if not org and hasattr(request.user, "memberships"):
            membership = request.user.memberships.filter(is_active=True).first()
            if membership:
                org = membership.organization

        if not org:
            return Response({"results": []}, status=status.HTTP_200_OK)

        transactions = BillingTransaction.objects.filter(organization=org).order_by("-created_at")
        serializer = BillingTransactionSerializer(transactions, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)


from .payment_views import CheckoutView, VerifyPaymentView, RazorpayWebhookView
