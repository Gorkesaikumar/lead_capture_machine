"""
Management command to purge seed/test Instagram webhook data (USER_A, USER_B sender IDs)
and reset the database so that the next real Instagram inbound webhook creates real identities.

This command:
1. Identifies all CustomerIdentity records where external_user_id is a known test value
2. Cascades delete associated Messages, Conversations, Leads, and Customers (if no real data)
3. Deletes the corresponding RawWebhookEvents
4. Reports exactly what was removed

Usage:
    python manage.py purge_test_instagram_data --dry-run   (preview only)
    python manage.py purge_test_instagram_data             (execute)
"""
import logging
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

# These are the known fake/test sender IDs that were seeded manually and must be purged
TEST_SENDER_IDS = {"USER_A", "USER_B", "user_a", "user_b"}


class Command(BaseCommand):
    help = "Purge seed/test Instagram data (USER_A, USER_B) to prepare for real Instagram webhooks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Preview what would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        from apps.customers.models import Customer, CustomerIdentity
        from apps.conversations.models import Conversation, Message
        from apps.leads.models import Lead
        from apps.integrations.models import RawWebhookEvent

        self.stdout.write("\n=== Instagram Test Data Purge ===\n")

        # Find test identities
        test_identities = CustomerIdentity.objects.filter(
            channel="INSTAGRAM",
            external_user_id__in=TEST_SENDER_IDS,
        ).select_related("customer")

        if not test_identities.exists():
            self.stdout.write(self.style.SUCCESS("No test identities found. Database is clean."))
            return

        # Collect all affected records
        customer_ids = []
        for identity in test_identities:
            self.stdout.write(
                f"  [TEST IDENTITY] channel=INSTAGRAM | ext_id={identity.external_user_id} | "
                f"customer={identity.customer.display_name or identity.customer_id}"
            )
            customer_ids.append(identity.customer_id)

        # Find conversations
        test_conversations = Conversation.objects.filter(
            customer_id__in=customer_ids,
            channel="INSTAGRAM",
        )
        for conv in test_conversations:
            msg_count = conv.messages.count()
            self.stdout.write(f"  [TEST CONVERSATION] id={conv.id} | messages={msg_count}")

        # Find leads
        test_leads = Lead.objects.filter(customer_id__in=customer_ids)
        for lead in test_leads:
            self.stdout.write(f"  [TEST LEAD] id={lead.id} | status={lead.status} | summary={lead.summary}")

        # Find raw webhook events that used the test IDs
        import json
        test_events = []
        for event in RawWebhookEvent.objects.filter(channel="INSTAGRAM"):
            try:
                payload = event.payload
                entries = payload.get("entry", [])
                for entry in entries:
                    for msg_event in entry.get("messaging", []):
                        sender_id = msg_event.get("sender", {}).get("id", "")
                        if sender_id in TEST_SENDER_IDS:
                            test_events.append(event)
                            self.stdout.write(f"  [TEST WEBHOOK] event_id={event.event_id} | sender_id={sender_id}")
            except Exception:
                pass

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] Would delete: {test_identities.count()} identities, "
                    f"{test_conversations.count()} conversations, {test_leads.count()} leads, "
                    f"{len(test_events)} webhook events, and associated customer records."
                )
            )
            self.stdout.write(self.style.WARNING("Run without --dry-run to actually delete.\n"))
            return

        with transaction.atomic():
            # Delete in dependency order
            msg_count = Message.objects.filter(conversation__in=test_conversations).count()
            Message.objects.filter(conversation__in=test_conversations).delete()
            self.stdout.write(f"  Deleted {msg_count} test messages")

            lead_act_count = 0
            for lead in test_leads:
                lead_act_count += lead.activities.count()
                lead.activities.all().delete()
            test_leads.delete()
            self.stdout.write(f"  Deleted {test_leads.count() if hasattr(test_leads, 'count') else 0} leads (and {lead_act_count} activities)")

            conv_count = test_conversations.count()
            test_conversations.delete()
            self.stdout.write(f"  Deleted {conv_count} conversations")

            identity_count = test_identities.count()
            test_identities.delete()
            self.stdout.write(f"  Deleted {identity_count} test customer identities")

            # Delete customer records that have NO remaining identities (test-only customers)
            orphan_customers = Customer.objects.filter(
                id__in=customer_ids,
                identities__isnull=True,
            )
            orphan_count = orphan_customers.count()
            orphan_customers.delete()
            self.stdout.write(f"  Deleted {orphan_count} orphan customer records")

            # Delete test webhook events
            event_ids = [e.id for e in test_events]
            RawWebhookEvent.objects.filter(id__in=event_ids).delete()
            self.stdout.write(f"  Deleted {len(event_ids)} test webhook events")

        self.stdout.write(
            self.style.SUCCESS(
                "\n✓ Test data purged. The system is ready to receive real Instagram webhooks.\n"
                "  Next time a real Instagram user messages the business:\n"
                "  → The real Meta IGSID will be stored in CustomerIdentity.external_user_id\n"
                "  → The admin will be able to send outbound messages to that real user\n"
            )
        )
