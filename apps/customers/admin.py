"""
Django admin configuration for Customer and CustomerIdentity.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from apps.customers.models import Customer, CustomerIdentity


class CustomerIdentityInline(admin.TabularInline):
    model = CustomerIdentity
    extra = 0
    fields = ("channel", "external_user_id", "username", "normalized_phone", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "primary_phone",
        "email",
        "first_seen_at",
        "last_seen_at",
        "is_deleted",
    )
    list_filter = ("is_deleted", "first_seen_at", "last_seen_at")
    search_fields = (
        "display_name",
        "primary_phone",
        "email",
        "identities__external_user_id",
        "identities__username",
    )
    readonly_fields = ("created_at", "updated_at", "first_seen_at")
    inlines = [CustomerIdentityInline]
    ordering = ("-last_seen_at",)


@admin.register(CustomerIdentity)
class CustomerIdentityAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "channel",
        "external_user_id",
        "username",
        "normalized_phone",
        "created_at",
    )
    list_filter = ("channel", "created_at")
    search_fields = ("external_user_id", "username", "normalized_phone", "customer__display_name")
    readonly_fields = ("created_at", "updated_at")
