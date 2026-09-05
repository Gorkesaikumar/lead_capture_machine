from rest_framework.exceptions import PermissionDenied

class TenantViewSetMixin:
    """
    Mixin for DRF ViewSets to enforce tenant isolation.
    Ensures that get_queryset is filtered by the active organization,
    and perform_create automatically assigns the active organization.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        if not hasattr(self.request, "organization") or not self.request.organization:
            # Prevent accidental data leakage if middleware fails or org is missing
            return qs.none()
        
        return qs.filter(organization=self.request.organization)

    def perform_create(self, serializer):
        if not hasattr(self.request, "organization") or not self.request.organization:
            raise PermissionDenied("An active organization context is required to create records.")
        serializer.save(organization=self.request.organization)
