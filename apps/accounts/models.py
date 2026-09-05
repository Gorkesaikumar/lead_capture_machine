"""
Custom User model and UserManager for Admin-only Photo Studio Platform.
"""
import uuid
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier for authentication.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a standard Admin user with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email field must be set"))

        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser Admin with all permissions.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model representing an authenticated Administrator.
    This is a single-role application: all authenticated users are Studio Admins.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier (UUIDv4)"),
    )
    email = models.EmailField(
        _("email address"),
        unique=True,
        db_index=True,
        error_messages={
            "unique": _("An account with this email already exists."),
        },
    )
    full_name = models.CharField(
        _("full name"),
        max_length=255,
        blank=True,
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active."),
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into the Django admin site."),
    )
    is_superuser = models.BooleanField(
        _("superuser status"),
        default=False,
        help_text=_("Designates that this user has all permissions without explicitly assigning them."),
    )
    email_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        auto_now=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = _("admin user")
        verbose_name_plural = _("admin users")
        ordering = ["-created_at"]

    def __str__(self):
        if self.full_name:
            return f"{self.full_name} <{self.email}>"
        return self.email

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email


class AdminAuditLog(models.Model):
    """
    Audit log for tracking all sensitive super admin actions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="admin_audit_logs")
    admin_email = models.EmailField(_("admin email"), max_length=255)
    action = models.CharField(_("action name"), max_length=100)
    target_type = models.CharField(_("target entity type"), max_length=100, blank=True)
    target_id = models.CharField(_("target entity ID"), max_length=255, blank=True)
    target_name = models.CharField(_("target name"), max_length=255, blank=True)
    previous_state = models.JSONField(_("previous state"), default=dict, blank=True)
    new_state = models.JSONField(_("new state"), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("admin audit log")
        verbose_name_plural = _("admin audit logs")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.admin_email} - {self.action} on {self.target_name or self.target_id} at {self.created_at}"
