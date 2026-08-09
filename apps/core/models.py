"""
Base abstract models for the application.
"""
import uuid
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """
    Abstract model that provides a UUIDv4 primary key.
    Prevents sequential ID enumeration and enumeration attacks.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier (UUIDv4)",
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """
    Abstract model that provides self-updating created_at and updated_at fields.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SoftDeletableModel(models.Model):
    """
    Abstract model for soft-deleting records without permanent physical deletion.
    """
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Designates whether this record has been soft-deleted",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the record was soft-deleted",
    )

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark the instance as deleted with timestamp."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        """Restore the soft-deleted instance."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class CoreModel(UUIDModel, TimeStampedModel):
    """
    Standard base model combining UUIDv4 primary key and timestamp tracking.
    """
    class Meta:
        abstract = True
        ordering = ["-created_at"]
