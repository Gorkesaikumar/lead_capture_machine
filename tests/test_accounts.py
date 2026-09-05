from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
"""
Tests for Custom User model and UserManager.
"""
import uuid
import pytest
from django.db import IntegrityError
from apps.accounts.models import User


@pytest.mark.django_db
class TestUserModelAndManager:
    def test_admin_user_creation(self):
        """1. Admin creation with email, full_name, and UUID pk."""
        user = User.objects.create_user(
            email="manager@v4studio.test",
            full_name="Studio Admin",
            password="SecurePassword123!",
        )
        assert user.pk is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.email == "manager@v4studio.test"
        assert user.full_name == "Studio Admin"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("SecurePassword123!") is True
        assert str(user) == "Studio Admin <manager@v4studio.test>"
        assert user.get_short_name() == "Studio"

    def test_superuser_creation(self, admin_user):
        """2. Superuser creation with full administrative privileges."""
        assert admin_user.is_superuser is True
        assert admin_user.is_staff is True
        assert admin_user.is_active is True
        assert admin_user.check_password("TestAdminPassword123!") is True

    def test_email_normalization(self):
        """3. Email domain normalization."""
        user = User.objects.create_user(
            email="OWNER@V4STUDIO.TEST",
            password="SecurePassword123!",
        )
        assert user.email == "OWNER@v4studio.test"

    def test_duplicate_email_rejection(self):
        """4. Duplicate email rejection at database constraint level."""
        User.objects.create_user(
            email="duplicate@v4studio.test",
            password="SecurePassword123!",
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="duplicate@v4studio.test",
                password="DifferentPassword456!",
            )

    def test_password_hashing(self):
        """5. Password is never saved in plaintext; proper hashing applied."""
        raw_password = "MySuperSecretPassword789!"
        user = User.objects.create_user(
            email="secure@v4studio.test",
            password=raw_password,
        )
        assert user.password != raw_password
        assert any(user.password.startswith(prefix) for prefix in ("pbkdf2_", "argon2", "md5$", "bcrypt"))
        assert user.check_password(raw_password) is True
        assert user.check_password("WrongPassword") is False

    def test_missing_email_raises_error(self):
        """Verify create_user requires an email address."""
        with pytest.raises(ValueError, match="The Email field must be set"):
            User.objects.create_user(email="", password="SomePassword123!")

    def test_superuser_invalid_staff_flag(self):
        """Verify create_superuser enforces is_staff=True."""
        with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
            User.objects.create_superuser(
                email="bad_admin@v4studio.test",
                password="Password123!",
                is_staff=False,
            )

    def test_superuser_invalid_superuser_flag(self):
        """Verify create_superuser enforces is_superuser=True."""
        with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
            User.objects.create_superuser(
                email="bad_admin2@v4studio.test",
                password="Password123!",
                is_superuser=False,
            )
