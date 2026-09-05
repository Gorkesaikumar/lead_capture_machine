from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.subscriptions.payments import gateway, payment_available
from apps.subscriptions.models import PaymentWebhookEvent, RecurringAgreement


class Command(BaseCommand):
    help = "Check recurring billing configuration without displaying secrets or creating payments."

    def add_arguments(self, parser):
        parser.add_argument("--probe", action="store_true", help="Verify credentials with a read-only Razorpay API call.")
        parser.add_argument("--deploy", action="store_true", help="Require webhook configuration and asynchronous workers.")

    def handle(self, *args, **options):
        errors = []
        if not payment_available(): errors.append("Set RAZORPAY_API_KEY and RAZORPAY_SECRET_KEY.")
        mode = "test" if settings.RAZORPAY_KEY_ID.startswith("rzp_test_") else "live"
        self.stdout.write(f"Payment mode: {mode if payment_available() else 'unconfigured'}")
        if not 1 <= settings.RAZORPAY_SUBSCRIPTION_CYCLES <= 1200:
            errors.append("RAZORPAY_SUBSCRIPTION_CYCLES must be between 1 and 1200.")
        self.stdout.write(f"Webhook secret: {'configured' if settings.RAZORPAY_WEBHOOK_SECRET else 'missing'}")
        if options["deploy"]:
            if len(settings.RAZORPAY_WEBHOOK_SECRET) < 24: errors.append("Set a strong, separate webhook secret (at least 24 characters).")
            if settings.CELERY_TASK_ALWAYS_EAGER: errors.append("Set CELERY_TASK_ALWAYS_EAGER=False and run Celery worker and beat.")
        if options["probe"] and payment_available():
            try:
                gateway("GET", "plans?count=1")
                self.stdout.write("Razorpay credential probe: accepted")
            except Exception:
                errors.append("Razorpay credential probe failed; check credentials, account access and connectivity.")
        self.stdout.write(f"Unprocessed webhook events: {PaymentWebhookEvent.objects.filter(is_processed=False).count()}")
        self.stdout.write(f"Unresolved checkout intents: {RecurringAgreement.objects.filter(status='creating').count()}")
        if errors: raise CommandError(" ".join(errors))
        self.stdout.write(self.style.SUCCESS("Configuration checks passed. Dashboard webhook delivery must still be tested separately."))
