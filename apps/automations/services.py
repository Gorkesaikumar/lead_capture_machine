from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import APIException
from apps.conversations.models import Message
from apps.conversations.outbound import queue_message
from apps.leads.models import Lead, LeadActivity
from apps.leads.services import LeadManagementService
from .models import Automation, AutomationExecution


def matches(automation, text, message_type="TEXT", first=False, lead=None, new_lead=False):
    text, keyword = text.casefold().strip(), automation.trigger_value.casefold().strip()
    trigger = {"INCOMING": True, "EXACT": text == keyword, "CONTAINS": bool(keyword) and keyword in text, "FIRST_INTERACTION": first, "NEW_CONVERSATION": first, "NEW_LEAD": new_lead}.get(automation.trigger_type, False)
    if not trigger:
        return False
    c = automation.conditions
    return not (
        ("lead_status" in c and (not lead or lead.status != c["lead_status"])) or
        ("has_tag" in c and (not lead or c["has_tag"] not in lead.tags)) or
        ("message_type" in c and message_type != c["message_type"]) or
        ("unassigned" in c and bool(lead and not lead.assigned_staff_id) != c["unassigned"])
    )


def evaluate_message(message, new_lead=False):
    if message.direction != "INBOUND" or not message.conversation.organization_id:
        return
    conversation = message.conversation
    org = conversation.organization
    if not org.has_feature("can_use_automations"):
        return
    first = not conversation.messages.filter(direction="INBOUND").exclude(pk=message.pk).exists()
    for automation in Automation.objects.filter(organization=org, channel=conversation.channel, enabled=True).prefetch_related("actions"):
        conversation.refresh_from_db()
        if not matches(automation, message.text, message.message_type, first, conversation.lead, new_lead):
            continue
        with transaction.atomic():
            from apps.organizations.models import Organization
            from .usage import reserve_run
            Organization.objects.select_for_update().get(pk=org.pk)
            execution, created = AutomationExecution.objects.get_or_create(
                automation=automation, trigger_message=message,
                defaults={"organization": org, "automation_name": automation.name, "conversation": conversation, "lead": conversation.lead},
            )
            if not created:
                continue
            quota_error = reserve_run(org)
            if quota_error:
                execution.status = "BLOCKED"
                execution.error = quota_error
                execution.save()
                continue
            results = []
            for action in automation.actions.all():
                config, kind = action.configuration, action.action_type
                try:
                    with transaction.atomic():
                        lead = conversation.lead
                        if not lead and kind != "SEND_REPLY":
                            from apps.leads.capture import capture_message_lead
                            lead, _ = capture_message_lead(message)
                            conversation.refresh_from_db()
                            if not lead:
                                raise ValueError("Lead quota or subscription prevents this action.")
                        outcome = {"action": kind, "status": "COMPLETED"}
                        if kind == "CHANGE_STATUS":
                            LeadManagementService.update_status(lead, config["status"])
                        elif kind == "ADD_TAG":
                            lead = Lead.objects.select_for_update().get(pk=lead.pk)
                            lead.tags = list(dict.fromkeys([*lead.tags, config["tag"].strip()]))
                            lead.save(update_fields=["tags", "updated_at"])
                        elif kind == "ASSIGN":
                            from apps.organizations.models import OrganizationMembership
                            membership = OrganizationMembership.objects.get(organization=org, user_id=config["user_id"], is_active=True, user__is_active=True)
                            LeadManagementService.assign_staff(lead, membership.user)
                        elif kind in ("SEND_REPLY", "BOOKING_LINK"):
                            text = config.get("text", "Choose a time for your appointment:")
                            if kind == "BOOKING_LINK":
                                from apps.bookings.services import BookingLinkService
                                link = BookingLinkService.create_for_lead(lead=lead, service=lead.service, expires_in_days=7)
                                text = f"{text}\n{settings.FRONTEND_URL}/book/{link.token}"
                            outgoing = queue_message(conversation, {"text": text}, request_id=f"automation:{execution.pk}:{action.pk}")
                            outcome.update(status="QUEUED", message_id=str(outgoing.pk))
                        results.append(outcome)
                        conversation.refresh_from_db()
                except (APIException, ValueError) as exc:
                    execution.status = "BLOCKED"
                    execution.error = str(exc)
                    results.append({"action": kind, "status": "BLOCKED"})
                    break
                except Exception:
                    execution.status = "FAILED"
                    execution.error = "Action failed. Review its configuration and workspace membership."
                    results.append({"action": kind, "status": "FAILED"})
                    break
            else:
                execution.status = "QUEUED" if any(r["status"] == "QUEUED" for r in results) else "COMPLETED"
            execution.result = results
            execution.lead = conversation.lead
            execution.save()
