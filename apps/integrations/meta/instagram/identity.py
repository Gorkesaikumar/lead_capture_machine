"""Account identifiers only; a customer's sender IGSID is never a routing alias."""
import re
from django.db.models import Q
from django.db.models.fields.json import KeyTextTransform


def account_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return ""
    value = str(value)
    return value if re.fullmatch(r"[1-9][0-9]{0,31}", value) else ""


def matching_configs(identifiers):
    from apps.integrations.models import IntegrationConfig
    ids = {value for identifier in identifiers if (value := account_id(identifier))}
    # oauth_user_id is deliberately not a standalone alias: token exchange alone
    # does not prove that it is the account identity returned by authenticated /me.
    # KeyTextTransform also handles numeric JSON IDs from older configurations.
    return IntegrationConfig.objects.annotate(
        routing_destination=KeyTextTransform("destination_id", "metadata"),
        routing_account=KeyTextTransform("account_id", "metadata"),
        routing_profile=KeyTextTransform("profile_id", "metadata"),
    ).filter(provider="INSTAGRAM", is_active=True, organization__is_active=True,
        organization__is_deleted=False).filter(
        Q(routing_destination__in=ids) | Q(routing_account__in=ids)
        | Q(metadata__auth_architecture="instagram_login", routing_profile__in=ids)
    )
