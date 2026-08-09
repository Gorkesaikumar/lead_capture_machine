"""
Tests for Celery configuration and tasks.
"""
import pytest
from config.celery import debug_task


def test_celery_debug_task():
    """Verify debug_task runs without error in eager test environment."""
    result = debug_task.apply()
    assert result.successful()
