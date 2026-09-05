from tests.tenant_fixtures import test_workspace, make_organization, create_lead, add_member
"""
Tests for PhotographyService and Package models, validations, safe deletion, and APIs.
"""
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import status
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.services.models import Package, PhotographyService
from apps.services.services import PhotographyServiceManager


@pytest.mark.django_db
class TestServiceAndPackageModels:
    def test_service_creation_and_slot_duration(self):
        """Total slot duration accurately sums session time and setup/cleanup buffers."""
        service = PhotographyService.objects.create(organization=test_workspace(),
            name="Cake Smash Photoshoot",
            duration_minutes=60,
            buffer_before_minutes=15,
            buffer_after_minutes=20,
            base_price=Decimal("4500.00"),
        )
        assert service.slug == "cake-smash-photoshoot"
        assert service.total_slot_duration_minutes == 95  # 60 + 15 + 20

    def test_package_effective_duration(self):
        """Package uses duration override when set, otherwise falls back to parent service duration."""
        service = PhotographyService.objects.create(organization=test_workspace(),
            name="Graduation Shoot",
            duration_minutes=45,
            base_price=Decimal("3000.00"),
        )

        pkg_default = Package.objects.create(
            service=service,
            name="Standard",
            price=Decimal("3000.00"),
        )
        assert pkg_default.effective_duration_minutes == 45

        pkg_extended = Package.objects.create(
            service=service,
            name="VIP Extended",
            price=Decimal("6000.00"),
            duration_minutes_override=90,
        )
        assert pkg_extended.effective_duration_minutes == 90

    def test_package_duplicate_name_within_service_rejected(self):
        """UniqueConstraint prevents duplicate package names under the same service."""
        service = PhotographyService.objects.create(organization=test_workspace(),
            name="Family Portrait",
            duration_minutes=60,
            base_price=Decimal("4000.00"),
        )
        Package.objects.create(
            service=service,
            name="Gold Package",
            price=Decimal("5000.00"),
        )
        with pytest.raises(IntegrityError):
            Package.objects.create(
                service=service,
                name="Gold Package",
                price=Decimal("5500.00"),
            )

    def test_safe_deletion_with_historical_dependencies(self):
        """Services with linked leads/packages are safely deactivated and soft-deleted."""
        service = PhotographyService.objects.create(organization=test_workspace(),
            name="Maternity Shoot",
            duration_minutes=60,
            base_price=Decimal("7000.00"),
        )
        pkg = Package.objects.create(
            service=service,
            name="Silver",
            price=Decimal("7000.00"),
        )
        customer = Customer.objects.create(organization=test_workspace(), display_name="Kriti Sanon")
        create_lead(
            customer=customer,
            source_channel="INSTAGRAM",
            service=service,
            status=Lead.Status.NEW,
        )

        assert service.has_historical_dependencies() is True

        # Perform safe delete
        success, msg = PhotographyServiceManager.delete_service(service)
        assert success is True

        service.refresh_from_db()
        pkg.refresh_from_db()
        assert service.is_deleted is True
        assert service.is_active is False
        assert pkg.is_deleted is True
        assert pkg.is_active is False


@pytest.mark.django_db
class TestServicesAndPackagesAPI:
    def test_service_crud_lifecycle(self, authenticated_client):
        """Admin can create, list, retrieve, update, toggle active, and delete services."""
        # 1. CREATE
        create_resp = authenticated_client.post(
            "/api/v1/services/",
            data={
                "name": "Pre-Wedding Photoshoot",
                "description": "Romantic outdoor shoot for couples",
                "duration_minutes": 120,
                "buffer_before_minutes": 30,
                "buffer_after_minutes": 30,
                "base_price": "15000.00",
                "sort_order": 1,
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        service_id = create_resp.json()["id"]

        # 2. LIST
        list_resp = authenticated_client.get("/api/v1/services/")
        assert list_resp.status_code == status.HTTP_200_OK
        assert list_resp.json()["count"] >= 1

        # 3. RETRIEVE
        detail_resp = authenticated_client.get(f"/api/v1/services/{service_id}/")
        assert detail_resp.status_code == status.HTTP_200_OK
        assert detail_resp.json()["total_slot_duration_minutes"] == 180  # 120 + 30 + 30

        # 4. TOGGLE ACTIVE
        toggle_resp = authenticated_client.post(f"/api/v1/services/{service_id}/toggle-active/")
        assert toggle_resp.status_code == status.HTTP_200_OK
        assert toggle_resp.json()["is_active"] is False

        # 5. DELETE
        del_resp = authenticated_client.delete(f"/api/v1/services/{service_id}/")
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT
        assert PhotographyService.objects.get(id=service_id).is_deleted is True

    def test_package_crud_lifecycle(self, authenticated_client):
        """Admin can manage packages with inclusions and duration overrides."""
        service = PhotographyService.objects.create(organization=test_workspace(),
            name="Fashion Portfolio",
            duration_minutes=90,
            base_price=Decimal("10000.00"),
        )

        # 1. CREATE PACKAGE
        create_resp = authenticated_client.post(
            "/api/v1/services/packages/",
            data={
                "service": str(service.id),
                "name": "Platinum Model Tier",
                "description": "Full day portfolio with makeup and 4 outfit changes",
                "price": "25000.00",
                "duration_minutes_override": 240,
                "inclusions": [
                    "30 Retouched High-Res Photos",
                    "4 Outfit Changes",
                    "Professional Makeup Artist",
                ],
                "sort_order": 2,
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        package_id = create_resp.json()["id"]
        assert create_resp.json()["effective_duration_minutes"] == 240

        # 2. RETRIEVE NESTED IN SERVICE
        service_resp = authenticated_client.get(f"/api/v1/services/{service.id}/")
        assert service_resp.status_code == status.HTTP_200_OK
        assert len(service_resp.json()["packages"]) == 1
        assert service_resp.json()["packages"][0]["name"] == "Platinum Model Tier"

        # 3. DELETE PACKAGE
        del_resp = authenticated_client.delete(f"/api/v1/services/packages/{package_id}/")
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT
        assert Package.objects.get(id=package_id).is_deleted is True

    def test_service_validation_errors(self, authenticated_client):
        """Validates minimum duration and non-negative pricing."""
        resp = authenticated_client.post(
            "/api/v1/services/",
            data={
                "name": "Invalid Service",
                "duration_minutes": 0,  # Invalid
                "base_price": "-100.00",  # Invalid
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        errors = resp.json().get("errors", resp.json())
        assert "duration_minutes" in errors
        assert "base_price" in errors

    def test_unauthenticated_services_rejected(self, api_client):
        """Unauthenticated requests are rejected with 401."""
        assert api_client.get("/api/v1/services/").status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.get("/api/v1/services/packages/").status_code == status.HTTP_401_UNAUTHORIZED
