from rest_framework.permissions import BasePermission

class IsSuperAdminUser(BasePermission):
    """
    Allows access only to super admin users (is_superuser=True or is_staff=True).
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.is_staff)
        )
