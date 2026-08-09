"""
Customer resolution and identity management service.
Handles concurrent webhook processing and identity resolution across Instagram and WhatsApp.
"""
import logging
from typing import Any, Dict, Optional, Tuple
from django.db import IntegrityError, transaction
from django.utils import timezone
from apps.customers.models import Customer, CustomerIdentity

logger = logging.getLogger("apps.customers")


class CustomerResolutionService:
    """
    Service for resolving or creating Customers based on external communication channel identities.
    Provides strict concurrency protection and idempotency against duplicate webhook deliveries.
    """

    @classmethod
    def resolve_customer(
        cls,
        channel: str,
        external_user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        display_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Tuple[Customer, bool]:
        """
        Resolves a Customer by channel and external_user_id.
        If the identity already exists, returns the associated Customer and updates interaction metadata.
        If unknown, atomically creates both Customer and CustomerIdentity.
        Handles concurrent race conditions safely via database uniqueness constraints and subtransaction recovery.

        Returns:
            Tuple[Customer, bool]: (Customer instance, created boolean)
        """
        if not channel or not external_user_id:
            raise ValueError("Channel and external_user_id are required for customer resolution.")

        channel = channel.upper().strip()
        external_user_id = str(external_user_id).strip()
        metadata = metadata or {}
        now = timezone.now()

        # 1. Fast path: check if identity already exists
        existing_identity = (
            CustomerIdentity.objects.select_related("customer")
            .filter(channel=channel, external_user_id=external_user_id)
            .first()
        )

        if existing_identity:
            logger.info(
                "[DIAGNOSTIC] resolve_customer FOUND EXISTING identity. channel=%s, external_user_id=%s, customer_id=%s",
                channel, external_user_id, existing_identity.customer.id
            )
            customer = existing_identity.customer
            cls._update_existing_identity_and_customer(
                customer=customer,
                identity=existing_identity,
                display_name=display_name,
                phone_number=phone_number,
                username=username,
                metadata=metadata,
                timestamp=now,
            )
            logger.info(
                "Resolved existing customer id=%s for channel=%s external_user_id=%s",
                customer.id,
                channel,
                external_user_id,
            )
            return customer, False

        logger.info(
            "[DIAGNOSTIC] resolve_customer CREATING NEW identity. channel=%s, external_user_id=%s",
            channel, external_user_id
        )

        # 2. Slow path: Create new Customer and CustomerIdentity atomically with race condition handling
        try:
            # Dynamically fetch profile for Instagram if missing
            if channel == "INSTAGRAM" and not display_name and not username:
                try:
                    from apps.integrations.meta.instagram.provider import InstagramMessagingProvider
                    profile = InstagramMessagingProvider().get_user_profile(external_user_id)
                    if profile:
                        display_name = profile.get("name", display_name)
                        username = profile.get("username", username)
                except Exception as e:
                    logger.warning("Could not fetch Instagram profile for %s: %s", external_user_id, e)

            with transaction.atomic():
                # Derive initial display name if not explicitly provided
                if display_name:
                    derived_display_name = display_name
                elif username:
                    derived_display_name = username
                elif channel == "INSTAGRAM":
                    suffix = external_user_id[-4:] if len(external_user_id) >= 4 else external_user_id
                    derived_display_name = f"Instagram User ({suffix})"
                elif channel == "WHATSAPP":
                    derived_display_name = f"WhatsApp ({phone_number or external_user_id})"
                else:
                    derived_display_name = "Customer"

                normalized_phone = phone_number or ("+" + external_user_id if channel == "WHATSAPP" else "")

                customer = Customer.objects.create(
                    display_name=derived_display_name,
                    primary_phone=normalized_phone,
                    first_seen_at=now,
                    last_seen_at=now,
                )

                CustomerIdentity.objects.create(
                    customer=customer,
                    channel=channel,
                    external_user_id=external_user_id,
                    username=username or "",
                    normalized_phone=normalized_phone,
                    metadata=metadata,
                )

                logger.info(
                    "Created new customer id=%s and identity for channel=%s external_user_id=%s",
                    customer.id,
                    channel,
                    external_user_id,
                )
                return customer, True

        except IntegrityError:
            # 3. Race condition recovery: Another concurrent process/thread inserted this identity
            logger.warning(
                "Concurrent identity insertion detected for channel=%s external_user_id=%s. Recovering existing record.",
                channel,
                external_user_id,
            )
            resolved_identity = (
                CustomerIdentity.objects.select_related("customer")
                .filter(channel=channel, external_user_id=external_user_id)
                .first()
            )
            if resolved_identity:
                customer = resolved_identity.customer
                cls._update_existing_identity_and_customer(
                    customer=customer,
                    identity=resolved_identity,
                    display_name=display_name,
                    phone_number=phone_number,
                    username=username,
                    metadata=metadata,
                    timestamp=now,
                )
                return customer, False

            # Unexpected edge case: re-raise if query still yields nothing
            raise

    @classmethod
    def _update_existing_identity_and_customer(
        cls,
        customer: Customer,
        identity: CustomerIdentity,
        display_name: Optional[str],
        phone_number: Optional[str],
        username: Optional[str],
        metadata: Dict[str, Any],
        timestamp: Any,
    ) -> None:
        """
        Updates customer and identity with latest incoming interaction details.
        """
        customer_updated = False
        identity_updated = False

        # Update last_seen_at
        customer.last_seen_at = timestamp
        customer_updated = True

        # Fill or upgrade display name if placeholder, username, or previously unset
        is_placeholder_name = (
            not customer.display_name
            or customer.display_name.startswith("Instagram User")
            or customer.display_name == "Unknown"
            or customer.display_name == identity.username
            or (username and customer.display_name == username)
        )
        if display_name and is_placeholder_name:
            customer.display_name = display_name
            customer_updated = True
        elif username and (not customer.display_name or customer.display_name.startswith("Instagram User")):
            customer.display_name = username
            customer_updated = True

        # Update username on identity if provided
        if username and identity.username != username:
            identity.username = username
            identity_updated = True

        # Update normalized phone on identity and customer if provided
        if phone_number:
            normalized = phone_number if phone_number.startswith("+") else f"+{phone_number}"
            if not customer.primary_phone:
                customer.primary_phone = normalized
                customer_updated = True
            if not identity.normalized_phone:
                identity.normalized_phone = normalized
                identity_updated = True

        if metadata:
            identity.metadata.update(metadata)
            identity_updated = True

        if customer_updated:
            customer.save(update_fields=["display_name", "primary_phone", "last_seen_at", "updated_at"])

        if identity_updated:
            identity.save(update_fields=["username", "normalized_phone", "metadata", "updated_at"])
