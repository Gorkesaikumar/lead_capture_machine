from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import CoreModel, SoftDeletableModel

class Organization(CoreModel, SoftDeletableModel):
    """
    Represents a tenant or workspace in the SaaS platform.
    Every major data record will belong to an Organization.
    """
    name = models.CharField(
        _("organization name"),
        max_length=255,
        help_text=_("Display name of the organization or studio"),
    )
    slug = models.SlugField(
        _("organization slug"),
        max_length=255,
        unique=True,
        help_text=_("Unique URL-friendly identifier"),
    )
    owner = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="owned_organizations",
        help_text=_("The primary billing owner of the organization"),
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
        help_text=_("Whether the organization is currently active and can access the platform"),
    )
    logo = models.URLField(
        _("logo URL"),
        max_length=1000,
        blank=True,
        null=True,
        help_text=_("URL to the organization's logo image"),
    )
    contact_email = models.EmailField(
        _("contact email"),
        blank=True,
        help_text=_("Primary public contact email"),
    )
    contact_phone = models.CharField(
        _("contact phone"),
        max_length=50,
        blank=True,
        help_text=_("Primary public contact phone number"),
    )
    timezone = models.CharField(
        _("timezone"),
        max_length=100,
        default="Asia/Kolkata",
        help_text=_("Primary timezone for the organization (e.g. America/New_York)"),
    )

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def has_feature(self, feature_name: str) -> bool:
        """
        Checks if this organization's active subscription plan grants access to the specified feature.
        """
        if feature_name == "can_use_automations":
            return hasattr(self, "subscription") and self.subscription.automation_entitled
        if not hasattr(self, 'subscription') or not self.subscription.is_valid:
            return False
            
        return getattr(self.subscription.plan, feature_name, False)

    def check_limit(self, limit_name: str, current_usage: int) -> bool:
        """
        Checks if this organization's active subscription allows for more usage of a limited resource.
        """
        if not hasattr(self, 'subscription') or not self.subscription.is_valid:
            return False
            
        limit = getattr(self.subscription.plan, limit_name, None)
        if limit is None:
            return True  # Unlimited
            
        return current_usage < limit


class OrganizationMembership(CoreModel):
    """
    Links a User to an Organization with a specific role.
    """
    class Role(models.TextChoices):
        OWNER = "OWNER", _("Owner")
        ADMIN = "ADMIN", _("Admin")
        MEMBER = "MEMBER", _("Member")

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
    )

    class Meta:
        verbose_name = _("organization membership")
        verbose_name_plural = _("organization memberships")
        unique_together = [("organization", "user")]

    def __str__(self):
        return f"{self.user} in {self.organization} ({self.get_role_display()})"


class OrganizationInvitation(CoreModel):
    """
    Tracks pending invitations to an organization.
    """
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        ACCEPTED = "ACCEPTED", _("Accepted")
        EXPIRED = "EXPIRED", _("Expired")

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField(
        _("email address"),
        db_index=True,
    )
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=OrganizationMembership.Role.choices,
        default=OrganizationMembership.Role.MEMBER,
    )
    invited_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invitations",
    )
    token = models.UUIDField(
        _("invitation token"),
        unique=True,
        editable=False,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField(
        _("expires at"),
    )

    class Meta:
        verbose_name = _("organization invitation")
        verbose_name_plural = _("organization invitations")
        unique_together = [("organization", "email")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite to {self.email} for {self.organization}"
