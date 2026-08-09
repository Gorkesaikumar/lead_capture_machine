"""
Django admin integration for Leads, Triggers, and LeadActivities.
"""
from django.contrib import admin
from apps.leads.models import Lead, LeadActivity, LeadTrigger


class LeadActivityInline(admin.TabularInline):
    model = LeadActivity
    extra = 0
    fields = ("activity_type", "actor", "description", "created_at")
    readonly_fields = ("activity_type", "actor", "description", "created_at")
    can_delete = False


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "service",
        "source_channel",
        "status",
        "priority",
        "assigned_staff",
        "created_at",
    )
    list_filter = ("status", "source_channel", "priority", "created_at", "service")
    search_fields = (
        "customer__display_name",
        "customer__primary_phone",
        "customer__email",
        "summary",
        "notes",
    )
    readonly_fields = ("created_at", "updated_at", "qualified_at", "closed_at")
    inlines = [LeadActivityInline]
    ordering = ("-created_at",)


@admin.register(LeadTrigger)
class LeadTriggerAdmin(admin.ModelAdmin):
    list_display = ("phrase", "match_type", "service", "priority", "is_active", "created_at")
    list_filter = ("match_type", "priority", "is_active", "service")
    search_fields = ("phrase", "service__name")


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ("lead", "activity_type", "actor", "created_at")
    list_filter = ("activity_type", "created_at")
    search_fields = ("lead__customer__display_name", "description")
    readonly_fields = ("created_at", "updated_at")
