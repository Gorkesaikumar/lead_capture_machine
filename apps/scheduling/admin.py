"""
Django admin integration for Scheduling and Availability.
"""
from django.contrib import admin
from apps.scheduling.models import BlockedPeriod, HolidayClosure, SpecialAvailability, WeeklyAvailability


@admin.register(WeeklyAvailability)
class WeeklyAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("weekday", "start_time", "end_time", "is_active", "created_at")
    list_filter = ("weekday", "is_active")
    ordering = ("weekday", "start_time")


@admin.register(SpecialAvailability)
class SpecialAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("date", "start_time", "end_time", "reason", "is_active", "created_at")
    list_filter = ("is_active", "date")
    search_fields = ("reason",)
    ordering = ("date", "start_time")


@admin.register(BlockedPeriod)
class BlockedPeriodAdmin(admin.ModelAdmin):
    list_display = ("starts_at", "ends_at", "reason", "service", "is_active", "created_at")
    list_filter = ("is_active", "service")
    search_fields = ("reason",)
    ordering = ("starts_at",)


@admin.register(HolidayClosure)
class HolidayClosureAdmin(admin.ModelAdmin):
    list_display = ("date", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("date",)
