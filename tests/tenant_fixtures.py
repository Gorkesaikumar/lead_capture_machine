"""Explicit tenant factories for tests migrated from the single-studio schema.

Only test data is defaulted; production APIs always require workspace membership.
"""
from uuid import uuid4
from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMembership


def test_owner():
    user, _ = User.objects.get_or_create(email="fixture-owner@v4studio.test", defaults={"full_name": "Fixture owner", "is_active": True})
    return user


def test_workspace():
    org, _ = Organization.objects.get_or_create(slug="fixture-studio", defaults={"name": "Fixture Studio", "timezone": __import__("django.conf", fromlist=["settings"]).settings.TIME_ZONE, "owner": test_owner()})
    OrganizationMembership.objects.get_or_create(organization=org, user=org.owner, defaults={"role": "OWNER"})
    return org


def make_organization(**kwargs):
    kwargs.setdefault("owner", test_owner())
    kwargs.setdefault("slug", f"fixture-{uuid4().hex}")
    return Organization.objects.create(**kwargs)


def add_member(user, organization=None):
    OrganizationMembership.objects.get_or_create(organization=organization or test_workspace(), user=user, defaults={"role": "OWNER"})


def create_lead(**kwargs):
    from apps.leads.models import Lead
    conversation = kwargs.pop("conversation", None)
    kwargs.setdefault("organization", getattr(kwargs.get("customer"), "organization", None) or test_workspace())
    lead = Lead.objects.create(**kwargs)
    if conversation:
        conversation.lead = lead
        conversation.save(update_fields=["lead", "updated_at"])
    return lead


def configure_channel(organization=None, channel="INSTAGRAM", destination="90001"):
    from apps.integrations.models import IntegrationConfig
    from apps.core.utils.crypto import encrypt_string
    org = organization or test_workspace()
    config, _ = IntegrationConfig.objects.update_or_create(organization=org, provider=channel, defaults={"is_active": True, "credentials": {"access_token": encrypt_string("mock-test-token")}, "metadata": {"destination_id": str(destination)}})
    return config


def route_payload(payload, organization=None):
    channel = "WHATSAPP" if payload.get("object") == "whatsapp_business_account" else "INSTAGRAM"
    entry = payload.get("entry", [{}])[0]
    destination = entry.get("id")
    if channel == "WHATSAPP":
        destination = entry.get("changes", [{}])[0].get("value", {}).get("metadata", {}).get("phone_number_id")
    if destination:
        configure_channel(organization, channel, destination)


def process_test_webhook_payload(*args, **kwargs):
    from apps.integrations.pipeline import InboundPipelineService
    route_payload(kwargs.get("payload") or args[2])
    return InboundPipelineService.process_webhook_payload(*args, **kwargs)

test_owner.__test__ = False
test_workspace.__test__ = False
