"""
Business logic and safe deletion management for Services and Packages.
"""
import logging
from typing import Tuple
from django.db import transaction
from apps.services.models import Package, PhotographyService

logger = logging.getLogger("apps.services")


class PhotographyServiceManager:
    """
    Manages service lifecycle, package management, and safe deletion.
    """

    @classmethod
    def delete_service(cls, service: PhotographyService, force: bool = False) -> Tuple[bool, str]:
        """
        Safely deletes or deactivates a photography service.

        If historical dependencies (leads, triggers, packages) exist,
        it deactivates and soft-deletes the service to preserve foreign key references
        and audit records.
        """
        with transaction.atomic():
            has_dependencies = service.has_historical_dependencies()

            if has_dependencies and not force:
                service.is_active = False
                service.save(update_fields=["is_active", "updated_at"])
                service.soft_delete()

                # Soft-delete child packages as well
                for pkg in service.packages.filter(is_deleted=False):
                    pkg.is_active = False
                    pkg.save(update_fields=["is_active", "updated_at"])
                    pkg.soft_delete()

                msg = "Service has historical records; it was safely deactivated and soft-deleted."
                logger.info("Service id=%s safely soft-deleted with deactivation", service.id)
                return True, msg

            # Hard delete if explicitly forced and no unhandled database constraints
            service.soft_delete()
            return True, "Service successfully soft-deleted."

    @classmethod
    def delete_package(cls, package: Package, force: bool = False) -> Tuple[bool, str]:
        """
        Safely deletes or deactivates a package.
        """
        with transaction.atomic():
            package.is_active = False
            package.save(update_fields=["is_active", "updated_at"])
            package.soft_delete()
            logger.info("Package id=%s safely soft-deleted", package.id)
            return True, "Package successfully soft-deleted."
