"""
Django admin integration for Photography Services and Packages.
"""
from django.contrib import admin
from apps.services.models import Package, PhotographyService


class PackageInline(admin.TabularInline):
    model = Package
    extra = 0
    fields = ("name", "price", "duration_minutes_override", "is_active", "sort_order")
    ordering = ("sort_order", "price")


@admin.register(PhotographyService)
class PhotographyServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "duration_minutes",
        "buffer_before_minutes",
        "buffer_after_minutes",
        "base_price",
        "sort_order",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [PackageInline]
    ordering = ("sort_order", "name")


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "service",
        "price",
        "duration_minutes_override",
        "sort_order",
        "is_active",
        "created_at",
    )
    list_filter = ("service", "is_active", "created_at")
    search_fields = ("name", "description", "service__name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("service", "sort_order", "price")
