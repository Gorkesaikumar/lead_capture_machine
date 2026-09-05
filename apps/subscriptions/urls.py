from django.urls import path
from .recurring_views import RecurringCheckoutView, RecurringVerifyView, RecurringSyncView, RecurringCancelView, RecurringWebhookView
from apps.subscriptions.views import (
    PlanListView,
    CurrentSubscriptionView,
    CheckoutView,
    VerifyPaymentView,
    CancelSubscriptionView,
    PaymentHistoryView,
    RazorpayWebhookView,
)

app_name = "subscriptions"

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="plans"),
    path("current/", CurrentSubscriptionView.as_view(), name="current"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("verify-payment/", VerifyPaymentView.as_view(), name="verify_payment"),
    path("cancel/", CancelSubscriptionView.as_view(), name="cancel"),
    path("history/", PaymentHistoryView.as_view(), name="history"),
    path("webhooks/razorpay/", RecurringWebhookView.as_view(), name="webhook_razorpay"),
    path("recurring/checkout/", RecurringCheckoutView.as_view(), name="recurring_checkout"),
    path("recurring/verify/", RecurringVerifyView.as_view(), name="recurring_verify"),
    path("recurring/sync/", RecurringSyncView.as_view(), name="recurring_sync"),
    path("recurring/cancel/", RecurringCancelView.as_view(), name="recurring_cancel"),
]
