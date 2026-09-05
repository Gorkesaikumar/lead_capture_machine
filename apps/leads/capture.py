"""Capture every supported contact, independent of keyword rules, within quota."""
from django.db import transaction
from apps.customers.models import Customer
from apps.leads.models import Lead, LeadActivity
from apps.subscriptions.services import SubscriptionEntitlementService, QuotaExceededException


def capture_message_lead(message):
    conversation = message.conversation
    with transaction.atomic():
        Customer.objects.select_for_update().get(pk=conversation.customer_id)
        lead = Lead.objects.filter(customer_id=conversation.customer_id, organization=conversation.organization, status__in=Lead.ACTIVE_STATUSES, is_deleted=False).first()
        created = False
        if not lead:
            try:
                SubscriptionEntitlementService.check_and_consume_lead_quota(conversation.organization, conversation.channel)
            except QuotaExceededException:
                return None, False
            lead = Lead.objects.create(organization=conversation.organization, customer=conversation.customer, source_channel=conversation.channel, originating_message=message, summary=(message.text or f"{message.message_type} inquiry")[:255])
            LeadActivity.objects.create(lead=lead, message=message, activity_type="LEAD_CREATED", description="Lead captured from an incoming message.")
            created = True
        conversation.lead = lead
        conversation.save(update_fields=["lead", "updated_at"])
        return lead, created
