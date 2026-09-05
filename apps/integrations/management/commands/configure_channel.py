"""Operator setup for approved test/live Meta assets; does not send messages."""
import os
from django.core.management.base import BaseCommand, CommandError
from apps.organizations.models import Organization
from apps.integrations.models import IntegrationConfig
from apps.core.utils.crypto import encrypt_string


class Command(BaseCommand):
    help = "Store an organization's channel credentials from environment variables, encrypted at rest."

    def add_arguments(self, parser):
        parser.add_argument("organization_id")
        parser.add_argument("channel", choices=["INSTAGRAM", "WHATSAPP"])

    def handle(self, organization_id, channel, **options):
        organization = Organization.objects.filter(pk=organization_id, is_active=True, is_deleted=False).first()
        if not organization:
            raise CommandError("Active organization not found.")
        token = os.getenv(f"{channel}_ACCESS_TOKEN", "")
        destination = os.getenv("INSTAGRAM_ACCOUNT_ID" if channel == "INSTAGRAM" else "WHATSAPP_PHONE_NUMBER_ID", "")
        if not token or not destination.isdigit():
            raise CommandError("Set the channel access token and numeric account/phone number ID in the environment.")
        if IntegrationConfig.objects.filter(provider=channel, metadata__destination_id=destination).exclude(organization=organization).exists():
            raise CommandError("This destination is already assigned to another workspace.")
        IntegrationConfig.objects.update_or_create(organization=organization, provider=channel, defaults={"is_active": True, "credentials": {"access_token": encrypt_string(token)}, "metadata": {"destination_id": destination, "account_id" if channel == "INSTAGRAM" else "phone_number_id": destination, "waba_id": os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "") if channel == "WHATSAPP" else ""}})
        self.stdout.write("Credentials stored. Status: CONFIGURED_UNVERIFIED. Configure webhook subscriptions and verify a real send before enabling production.")
