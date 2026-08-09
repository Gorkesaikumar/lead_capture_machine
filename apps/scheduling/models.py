"""
Scheduling and Availability models.
Configures studio business hours, break periods, blocked time windows, special dates, and holiday closures.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import CoreModel
from apps.services.models import PhotographyService


class Weekday(models.IntegerChoices):
    MONDAY = 0, _("Monday")
    TUESDAY = 1, _("Tuesday")
    WEDNESDAY = 2, _("Wednesday")
    THURSDAY = 3, _("Thursday")
    FRIDAY = 4, _("Friday")
    SATURDAY = 5, _("Saturday")
    SUNDAY = 6, _("Sunday")


class WeeklyAvailability(CoreModel):
    """
    Standard recurring weekly operating hours.
    Supports multiple active periods per day (e.g. 09:00-13:00 and 14:00-18:00 for lunch breaks).
    """

    weekday = models.PositiveSmallIntegerField(
        _("day of week"),
        choices=Weekday.choices,
        db_index=True,
    )
    start_time = models.TimeField(_("start time"))
    end_time = models.TimeField(_("end time"))
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)

    class Meta:
        verbose_name = _("weekly availability")
        verbose_name_plural = _("weekly availabilities")
        ordering = ["weekday", "start_time"]
        indexes = [
            models.Index(fields=["weekday", "is_active", "start_time"]),
        ]

    def __str__(self):
        return f"{self.get_weekday_display()}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": _("End time must be after start time.")})


class SpecialAvailability(CoreModel):
    """
    Overrides standard weekly availability for a specific date (e.g. holiday special opening hours).
    """

    date = models.DateField(_("override date"), db_index=True)
    start_time = models.TimeField(_("start time"))
    end_time = models.TimeField(_("end time"))
    reason = models.CharField(_("reason"), max_length=255, blank=True, help_text=_("e.g. Festival Special Shoot, Extended Weekend"))
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)

    class Meta:
        verbose_name = _("special availability")
        verbose_name_plural = _("special availabilities")
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["date", "is_active", "start_time"]),
        ]

    def __str__(self):
        return f"{self.date}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')} ({self.reason or 'Special Hours'})"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": _("End time must be after start time.")})


class BlockedPeriod(CoreModel):
    """
    Blocks studio time for maintenance, personal leaves, private events, or specific service restrictions.
    """

    starts_at = models.DateTimeField(_("starts at"), db_index=True)
    ends_at = models.DateTimeField(_("ends at"), db_index=True)
    reason = models.CharField(
        _("reason"),
        max_length=255,
        help_text=_("e.g. Studio Maintenance, Private Event, Personal Leave"),
    )
    service = models.ForeignKey(
        PhotographyService,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="blocked_periods",
        help_text=_("Optional specific service blocked. If blank, all services are blocked."),
    )
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)

    class Meta:
        verbose_name = _("blocked period")
        verbose_name_plural = _("blocked periods")
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["is_active", "starts_at", "ends_at"]),
        ]

    def __str__(self):
        svc_info = f" ({self.service.name})" if self.service else " (All Services)"
        return f"Blocked: {self.starts_at} to {self.ends_at} - {self.reason}{svc_info}"

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError({"ends_at": _("End datetime must be after start datetime.")})


class HolidayClosure(CoreModel):
    """
    Marks the studio as completely closed on a specific calendar date (e.g. National Holidays, Diwali, Christmas).
    """

    date = models.DateField(_("closure date"), unique=True, db_index=True)
    name = models.CharField(
        _("holiday / closure name"),
        max_length=255,
        help_text=_("e.g. Diwali, New Year's Day, Studio Renovation"),
    )
    is_active = models.BooleanField(_("is active"), default=True, db_index=True)

    class Meta:
        verbose_name = _("holiday / studio closure")
        verbose_name_plural = _("holidays & studio closures")
        ordering = ["date"]

    def __str__(self):
        return f"Closed: {self.date} - {self.name}"
