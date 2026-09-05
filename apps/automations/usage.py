"""App run quotas are independent of Meta's messaging limits and message fees."""
from calendar import monthrange
from django.utils import timezone
from apps.subscriptions.models import Subscription
from .models import AutomationUsage


def next_month(start):
    month = start.month % 12 + 1
    year = start.year + (start.month == 12)
    return start.replace(year=year, month=month, day=min(start.day, monthrange(year, month)[1]))


def period(subscription):
    if subscription.plan.code == "starter":
        return subscription.automation_addon_start, subscription.automation_addon_end
    start = subscription.current_period_start
    return start, subscription.current_period_end or next_month(start)


def automation_access(subscription):
    from apps.subscriptions.payments import payment_available
    entitled = subscription.automation_entitled
    start, end = period(subscription)
    used = 0
    if start and end:
        used = AutomationUsage.objects.filter(organization_id=subscription.organization_id,
            period_start=start, period_end=end).values_list("runs_started", flat=True).first() or 0
    limit = subscription.plan.automation_run_limit if entitled else 0
    from apps.subscriptions.recurring import agreements, TERMINAL
    addon = agreements(subscription.organization).filter(product="dm_automation").exclude(status__in=TERMINAL).first()
    return {
        "entitled": entitled, "included": subscription.plan.can_use_automations,
        "addon_available": subscription.plan.code == "starter",
        "addon_price_inr": "399.00", "addon_currency": "INR", "addon_runs": 1000,
        "addon_start": subscription.automation_addon_start, "addon_end": subscription.automation_addon_end,
        "auto_renews": bool(addon and not addon.cancel_at_period_end), "payment_available": payment_available(),
        "run_limit": limit, "runs_used": used,
        "runs_remaining": max(0, limit-used) if limit is not None else None,
        "period_start": start, "period_end": end,
        "meta_fees_included": False,
    }


def reserve_run(organization):
    """Caller holds the organization row lock and the execution transaction."""
    sub = Subscription.objects.select_related("plan").filter(organization=organization).first()
    if not sub or not sub.automation_entitled:
        return "DM Automation access is inactive. Review your subscription or add-on."
    start, end = period(sub)
    if not start or not end or not start <= timezone.now() < end:
        return "The automation usage period has ended. Renew your subscription or add-on."
    usage, _ = AutomationUsage.objects.get_or_create(organization=organization, period_start=start, period_end=end)
    limit = sub.plan.automation_run_limit
    if limit is not None and usage.runs_started >= limit:
        return f"Monthly automation limit reached ({limit:,} runs). New runs resume in your next paid period."
    usage.runs_started += 1
    usage.save(update_fields=["runs_started", "updated_at"])
    return None
