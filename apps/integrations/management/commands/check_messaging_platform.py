"""Read-only deployment diagnostics; never prints credentials or message bodies."""
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
from django.db.models import Count
from apps.integrations.models import IntegrationConfig, RawWebhookEvent
from apps.conversations.models import Message
from apps.conversations.outbound import configuration_status


class Command(BaseCommand):
    help = "Report channel configuration, durable queues and unowned legacy records."

    def handle(self, *args, **options):
        for key in ("META_APP_ID", "META_APP_SECRET", "META_VERIFY_TOKEN", "SECRET_KEY"):
            self.stdout.write(f"{key}: {'SET' if getattr(settings, key, '') else 'MISSING'}")
        for config in IntegrationConfig.objects.select_related("organization"):
            state, detail = configuration_status(config)
            self.stdout.write(f"{config.organization_id} {config.provider}: {state} — {detail}")
        for app, model in [("customers", "Customer"), ("customers", "CustomerIdentity"), ("conversations", "Conversation"), ("leads", "Lead"), ("services", "PhotographyService"), ("bookings", "Booking"), ("scheduling", "WeeklyAvailability"), ("scheduling", "SpecialAvailability"), ("scheduling", "HolidayClosure"), ("scheduling", "BlockedPeriod")]:
            count = apps.get_model(app, model).objects.filter(organization__isnull=True).count()
            self.stdout.write(f"Unowned {app}.{model}: {count}")
        self.stdout.write(f"Outbox: {list(Message.objects.filter(direction='OUTBOUND').values('delivery_status').annotate(count=Count('id')))}")
        self.stdout.write(f"Webhooks: {list(RawWebhookEvent.objects.values('status').annotate(count=Count('id')))}")
