from django.core.management.base import BaseCommand
from apps.subscriptions.tasks import reconcile_recurring_payments


class Command(BaseCommand):
    help = "Dispatch a bounded recovery batch for pending payment events and recurring mandates."

    def handle(self, *args, **options):
        reconcile_recurring_payments()
        self.stdout.write(self.style.SUCCESS("Payment recovery batch dispatched. Check worker logs and billing event errors."))
