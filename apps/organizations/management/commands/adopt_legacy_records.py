"""Explicitly assign reviewed legacy records; never guess studio ownership."""
from uuid import UUID
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.organizations.models import Organization

ALLOWED = {"customers.Customer", "customers.CustomerIdentity", "conversations.Conversation", "leads.Lead", "services.PhotographyService", "bookings.Booking", "scheduling.WeeklyAvailability", "scheduling.SpecialAvailability", "scheduling.HolidayClosure", "scheduling.BlockedPeriod", "audit.AuditEvent"}


class Command(BaseCommand):
    help = "Dry-run by default: assign explicitly selected unowned legacy UUIDs to a reviewed workspace."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True)
        parser.add_argument("--model", required=True, choices=sorted(ALLOWED))
        parser.add_argument("--ids", nargs="+", required=True)
        parser.add_argument("--apply", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        org = Organization.objects.get(pk=options["organization"], is_active=True)
        try:
            ids = {UUID(value) for value in options["ids"]}
        except ValueError:
            raise CommandError("Every record ID must be a UUID.")
        model = apps.get_model(options["model"])
        rows = list(model.objects.select_for_update().filter(pk__in=ids, organization__isnull=True))
        if len(rows) != len(ids):
            raise CommandError("One or more selected records are missing or already owned. Nothing changed.")
        for row in rows:
            for relation in ("customer", "service", "lead"):
                related = getattr(row, relation, None)
                if related and hasattr(related, "organization_id") and related.organization_id != org.pk:
                    raise CommandError(f"Assign and verify the related {relation} in this workspace first. Nothing changed.")
        if options["apply"]:
            model.objects.filter(pk__in=ids, organization__isnull=True).update(organization=org)
        self.stdout.write(f"{'Assigned' if options['apply'] else 'Would assign'} {len(rows)} {options['model']} records to {org.pk}.")
