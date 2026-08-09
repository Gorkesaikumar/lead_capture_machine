"""
Django admin configuration for Bookings and Booking Links.
"""
from django.contrib import admin
from apps.bookings.models import Booking, BookingLink


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "service",
        "package",
        "starts_at",
        "ends_at",
        "status",
        "booked_at",
        "created_at",
    )
    list_filter = ("status", "service", "starts_at", "booked_at")
    search_fields = ("customer__display_name", "customer_notes", "internal_notes")
    ordering = ("-starts_at",)


@admin.register(BookingLink)
class BookingLinkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "lead",
        "service",
        "token",
        "expires_at",
        "is_used",
        "is_revoked",
        "created_at",
    )
    list_filter = ("is_used", "is_revoked", "expires_at", "created_at")
    search_fields = ("token", "lead__customer__display_name")
    ordering = ("-created_at",)
