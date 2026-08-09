"""
Authentication and staff management business service layer for Studio Admin accounts.
"""
import logging
from typing import Any, Dict, Optional
from django.contrib.auth.models import update_last_login
from django.db import transaction
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import AuditService

logger = logging.getLogger("apps.accounts")


class AuthService:
    """
    Encapsulates core authentication, credential verification, token management, and staff role management.
    """

    @classmethod
    def authenticate_admin(cls, email: str, password: str, ip_address: str = None) -> tuple[User, str]:
        """
        Authenticate an Admin by email and password, generate/retrieve token,
        and update last_login timestamp.

        Raises:
            AuthenticationFailed: If credentials are invalid or user is inactive.
        """
        if not email or not password:
            raise AuthenticationFailed("Email and password are required.")

        normalized_email = User.objects.normalize_email(email)
        user = User.objects.filter(email__iexact=normalized_email).first()

        if user is None or not user.check_password(password):
            logger.warning(
                "Authentication failed for email=%s ip=%s",
                normalized_email,
                ip_address or "unknown",
            )
            # Generic error to prevent account enumeration
            raise AuthenticationFailed("Invalid email or password.")

        if not user.is_active:
            logger.warning(
                "Authentication rejected for inactive user id=%s email=%s",
                user.id,
                user.email,
            )
            raise AuthenticationFailed("User account is disabled.")

        with transaction.atomic():
            update_last_login(None, user)
            token, _ = Token.objects.get_or_create(user=user)

        AuditService.record_event(
            action=AuditEvent.Action.USER_LOGIN,
            entity_type="User",
            entity_id=user.id,
            actor=user,
            metadata={"email": user.email},
            ip_address=ip_address,
        )

        logger.info(
            "Admin user authenticated successfully id=%s email=%s ip=%s",
            user.id,
            user.email,
            ip_address or "unknown",
        )
        return user, token.key

    @classmethod
    def logout_admin(cls, user: User, ip_address: Optional[str] = None) -> None:
        """
        Invalidate all active DRF authentication tokens for the given Admin user.
        """
        if user and user.is_authenticated:
            deleted_count, _ = Token.objects.filter(user=user).delete()
            AuditService.record_event(
                action=AuditEvent.Action.USER_LOGOUT,
                entity_type="User",
                entity_id=user.id,
                actor=user,
                metadata={"email": user.email, "revoked_tokens": deleted_count},
                ip_address=ip_address,
            )
            logger.info(
                "Admin user logged out id=%s email=%s (revoked %d token(s))",
                user.id,
                user.email,
                deleted_count,
            )

    @classmethod
    def update_staff_role(
        cls,
        target_user: User,
        is_staff: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        is_active: Optional[bool] = None,
        actor: Optional[User] = None,
        request: Optional[Any] = None,
    ) -> User:
        """
        Updates permissions/roles for a staff user and records an immutable audit trail.
        """
        changes: Dict[str, Any] = {}
        update_fields = ["updated_at"]

        if is_staff is not None and target_user.is_staff != is_staff:
            changes["is_staff"] = {"old": target_user.is_staff, "new": is_staff}
            target_user.is_staff = is_staff
            update_fields.append("is_staff")

        if is_superuser is not None and target_user.is_superuser != is_superuser:
            changes["is_superuser"] = {"old": target_user.is_superuser, "new": is_superuser}
            target_user.is_superuser = is_superuser
            update_fields.append("is_superuser")

        if is_active is not None and target_user.is_active != is_active:
            changes["is_active"] = {"old": target_user.is_active, "new": is_active}
            target_user.is_active = is_active
            update_fields.append("is_active")

        if changes:
            with transaction.atomic():
                target_user.save(update_fields=update_fields)
                AuditService.record_staff_role_changed(
                    target_user=target_user,
                    role_changes=changes,
                    actor=actor,
                    request=request,
                )
            logger.info(
                "Updated staff roles for user id=%s (%s) by actor=%s: %s",
                target_user.id,
                target_user.email,
                actor.email if actor else "System",
                changes,
            )

        return target_user

