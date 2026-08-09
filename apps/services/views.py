"""
Views for Photography Services and Packages.
"""
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.audit.services import AuditService
from apps.services.models import Package, PhotographyService
from apps.services.serializers import (
    PackageSerializer,
    PhotographyServiceCreateUpdateSerializer,
    PhotographyServiceDetailSerializer,
    PhotographyServiceListSerializer,
)
from apps.services.services import PhotographyServiceManager


class PhotographyServiceViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoints for studio photography services.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["sort_order", "name", "base_price", "duration_minutes", "created_at"]
    ordering = ["sort_order", "name"]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        return PhotographyService.objects.filter(is_deleted=False).prefetch_related("packages")

    def get_serializer_class(self):
        if self.action == "list":
            return PhotographyServiceListSerializer
        if self.action == "retrieve":
            return PhotographyServiceDetailSerializer
        return PhotographyServiceCreateUpdateSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditService.record_service_changed(
            entity_type="PhotographyService",
            entity_id=instance.id,
            change_type="create",
            metadata={"name": instance.name, "base_price": str(instance.base_price)},
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditService.record_service_changed(
            entity_type="PhotographyService",
            entity_id=instance.id,
            change_type="update",
            metadata={"name": instance.name, "base_price": str(instance.base_price), "is_active": instance.is_active},
            request=self.request,
        )

    def perform_destroy(self, instance):
        AuditService.record_service_changed(
            entity_type="PhotographyService",
            entity_id=instance.id,
            change_type="delete",
            metadata={"name": instance.name},
            request=self.request,
        )
        PhotographyServiceManager.delete_service(instance)

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        """
        POST /api/v1/services/{id}/toggle-active/
        Toggles service availability.
        """
        service = self.get_object()
        service.is_active = not service.is_active
        service.save(update_fields=["is_active", "updated_at"])
        AuditService.record_service_changed(
            entity_type="PhotographyService",
            entity_id=service.id,
            change_type="toggle_active",
            metadata={"name": service.name, "is_active": service.is_active},
            request=request,
        )
        return Response(PhotographyServiceDetailSerializer(service).data, status=status.HTTP_200_OK)


class PackageViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoints for service pricing tiers and packages.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PackageSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["service", "is_active"]
    search_fields = ["name", "description", "service__name"]
    ordering_fields = ["sort_order", "price", "name", "created_at"]
    ordering = ["sort_order", "price"]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        return Package.objects.filter(is_deleted=False).select_related("service")

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditService.record_service_changed(
            entity_type="Package",
            entity_id=instance.id,
            change_type="create",
            metadata={"name": instance.name, "service_id": str(instance.service_id), "price": str(instance.price)},
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        AuditService.record_service_changed(
            entity_type="Package",
            entity_id=instance.id,
            change_type="update",
            metadata={"name": instance.name, "service_id": str(instance.service_id), "price": str(instance.price), "is_active": instance.is_active},
            request=self.request,
        )

    def perform_destroy(self, instance):
        AuditService.record_service_changed(
            entity_type="Package",
            entity_id=instance.id,
            change_type="delete",
            metadata={"name": instance.name, "service_id": str(instance.service_id)},
            request=self.request,
        )
        PhotographyServiceManager.delete_package(instance)

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        """
        POST /api/v1/packages/{id}/toggle-active/
        Toggles package availability.
        """
        package = self.get_object()
        package.is_active = not package.is_active
        package.save(update_fields=["is_active", "updated_at"])
        AuditService.record_service_changed(
            entity_type="Package",
            entity_id=package.id,
            change_type="toggle_active",
            metadata={"name": package.name, "is_active": package.is_active},
            request=request,
        )
        return Response(PackageSerializer(package).data, status=status.HTTP_200_OK)
