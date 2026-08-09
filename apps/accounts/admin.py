"""
Django Admin integration for custom User model.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for the single-role Admin User model.
    """

    list_display = (
        "email",
        "full_name",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
        "created_at",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    search_fields = ("email", "full_name")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("full_name",)}),
        (
            _("Permissions & Status"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )

    readonly_fields = ("created_at", "updated_at", "last_login")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2", "is_active", "is_staff", "is_superuser"),
            },
        ),
    )
