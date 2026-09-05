import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.organizations.models import Organization
from apps.integrations.models import IntegrationConfig
from apps.core.utils.crypto import encrypt_string


class Command(BaseCommand):
    help = "Save an encrypted workspace channel token from an environment variable. Does not verify Meta access."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True)
        parser.add_argument("--channel", choices=["INSTAGRAM", "WHATSAPP"], required=True)
        parser.add_argument("--destination", required=True, help="Instagram professional account ID or WhatsApp phone-number ID")
        parser.add_argument("--token-env", default="META_CHANNEL_ACCESS_TOKEN")

    @transaction.atomic
    def handle(self, *args, **options):
        token = os.environ.get(options["token_env"], "")
        if not token or not options["destination"].isdigit():
            raise CommandError("Set the token environment variable and provide a numeric destination ID.")
        org = Organization.objects.select_for_update().get(pk=options["organization"], is_active=True)
        from apps.integrations.models import DataDeletionRequest
        if DataDeletionRequest.objects.filter(status="PENDING", scopes__contains=[{"organization": str(org.pk)}]).exists():
            raise CommandError("Wait for pending data deletion to complete before reconnecting.")
        if IntegrationConfig.objects.filter(provider=options["channel"], metadata__destination_id=options["destination"], is_active=True).exclude(organization=org).exists():
            raise CommandError("This destination is already assigned to another workspace.")
        IntegrationConfig.objects.update_or_create(organization=org, provider=options["channel"], defaults={"is_active": True, "credentials": {"access_token": encrypt_string(token)}, "metadata": {"destination_id": options["destination"], "account_id": options["destination"] if options["channel"] == "INSTAGRAM" else ""}})
        self.stdout.write("Credentials saved: CONFIGURED_UNVERIFIED. Configure webhook subscriptions and perform the live acceptance checklist.")
