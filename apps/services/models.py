"""
Photography Service and Package domain models.
Defines catalog offerings, session durations, preparation buffers, pricing, and inclusions.
"""
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from apps.core.models import CoreModel, SoftDeletableModel


class PhotographyService(CoreModel, SoftDeletableModel):
    """
    Represents a core photography service (e.g. Newborn, Maternity, Wedding, Portrait).
    """

    name = models.CharField(
        _("service name"),
        max_length=255,
        unique=True,
        help_text=_("e.g. Newborn Baby Shoot, Maternity Photoshoot"),
    )
    slug = models.SlugField(
        _("slug"),
        max_length=255,
        unique=True,
        help_text=_("URL-friendly slug for service identification"),
    )
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Detailed overview of what the photography session entails"),
    )
    duration_minutes = models.PositiveIntegerField(
        _("session duration (minutes)"),
        default=60,
        validators=[MinValueValidator(1)],
        help_text=_("Standard duration of the photography session in minutes"),
    )
    buffer_before_minutes = models.PositiveIntegerField(
        _("buffer before (minutes)"),
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Preparation / setup buffer before session begins"),
    )
    buffer_after_minutes = models.PositiveIntegerField(
        _("buffer after (minutes)"),
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Tear-down / cleanup / reset buffer after session ends"),
    )
    base_price = models.DecimalField(
        _("base price"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Starting base price in studio currency"),
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
        db_index=True,
        help_text=_("Whether this service is currently offered to customers"),
    )
    sort_order = models.PositiveIntegerField(
        _("sort order"),
        default=0,
        db_index=True,
        help_text=_("Display order for public booking and admin catalog"),
    )

    class Meta:
        verbose_name = _("photography service")
        verbose_name_plural = _("photography services")
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["is_active", "sort_order"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def total_slot_duration_minutes(self) -> int:
        """Total blocked studio time including buffers."""
        return self.duration_minutes + self.buffer_before_minutes + self.buffer_after_minutes

    def has_historical_dependencies(self) -> bool:
        """Checks if historical leads or triggers depend on this service."""
        from apps.leads.models import Lead, LeadTrigger
        leads_exist = Lead.objects.filter(service=self).exists()
        triggers_exist = LeadTrigger.objects.filter(service=self).exists()
        packages_exist = self.packages.filter(is_deleted=False).exists()
        return leads_exist or triggers_exist or packages_exist


class Package(CoreModel, SoftDeletableModel):
    """
    Tiered pricing package within a photography service (e.g. Silver, Gold, Platinum).
    """

    service = models.ForeignKey(
        PhotographyService,
        on_delete=models.CASCADE,
        related_name="packages",
        help_text=_("The parent photography service offering"),
    )
    name = models.CharField(
        _("package name"),
        max_length=255,
        help_text=_("e.g. Standard Package, Premium Gold Package"),
    )
    slug = models.SlugField(
        _("slug"),
        max_length=255,
        blank=True,
        help_text=_("URL-friendly identifier for the package"),
    )
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Package overview and deliverables summary"),
    )
    price = models.DecimalField(
        _("package price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Fixed price for this package"),
    )
    duration_minutes_override = models.PositiveIntegerField(
        _("duration override (minutes)"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text=_("Optional duration override if this package differs from base service duration"),
    )
    inclusions = models.JSONField(
        _("package inclusions"),
        default=list,
        blank=True,
        help_text=_("List of deliverables/features included (e.g. ['20 Edited Photos', '2 Outfits'])"),
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
        db_index=True,
        help_text=_("Whether this package is available for customer booking"),
    )
    sort_order = models.PositiveIntegerField(
        _("sort order"),
        default=0,
        db_index=True,
        help_text=_("Display order within the parent service"),
    )

    class Meta:
        verbose_name = _("package")
        verbose_name_plural = _("packages")
        ordering = ["sort_order", "price", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_service_package_name",
            )
        ]
        indexes = [
            models.Index(fields=["service", "is_active", "sort_order"]),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name} ({self.price})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.service.name}-{self.name}")
        super().save(*args, **kwargs)

    @property
    def effective_duration_minutes(self) -> int:
        """Returns the specific package duration or defaults to the parent service duration."""
        return self.duration_minutes_override if self.duration_minutes_override else self.service.duration_minutes
