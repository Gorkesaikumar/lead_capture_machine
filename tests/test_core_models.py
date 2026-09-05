from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
"""
Tests for abstract base models.
"""
import uuid
import pytest
from django.db import models
from apps.core.models import CoreModel, SoftDeletableModel, TimeStampedModel, UUIDModel


# Create concrete models dynamically for testing abstract classes
class SampleUUIDModel(UUIDModel):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class SampleSoftDeleteModel(SoftDeletableModel):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


@pytest.mark.django_db
def test_uuid_model_structure():
    """Verify UUIDModel provides a UUID pk."""
    pk_field = UUIDModel._meta.get_field("id")
    assert isinstance(pk_field, models.UUIDField)
    assert pk_field.primary_key is True
    assert pk_field.editable is False


def test_timestamped_model_structure():
    """Verify TimeStampedModel provides created_at and updated_at."""
    created_at = TimeStampedModel._meta.get_field("created_at")
    updated_at = TimeStampedModel._meta.get_field("updated_at")
    assert isinstance(created_at, models.DateTimeField)
    assert created_at.auto_now_add is True
    assert created_at.db_index is True
    assert isinstance(updated_at, models.DateTimeField)
    assert updated_at.auto_now is True
