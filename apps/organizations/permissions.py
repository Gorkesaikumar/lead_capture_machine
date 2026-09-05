from rest_framework import permissions

def _resolve_tenant_context(request):
    """
    Lazily resolves the tenant context after DRF authentication runs.
    """
    if getattr(request, '_tenant_resolved', False):
        return

    from apps.organizations.models import OrganizationMembership

    if not hasattr(request, 'user') or not request.user.is_authenticated or not request.user.is_active:
        request.organization = None
        request.membership = None
        request._tenant_resolved = True
        return

    from uuid import UUID
    org_id = request.headers.get("X-Organization-ID")
    memberships = request.user.memberships.filter(is_active=True, organization__is_active=True, organization__is_deleted=False).select_related("organization")
    if org_id:
        try:
            memberships = memberships.filter(organization_id=UUID(org_id))
        except (ValueError, TypeError):
            memberships = memberships.none()
    membership = memberships.first()
    request.membership = membership
    request.organization = membership.organization if membership else None

    request._tenant_resolved = True


class IsOrganizationMember(permissions.BasePermission):
    """
    Allows access only to users who are active members of the requested organization.
    """
    def has_permission(self, request, view):
        _resolve_tenant_context(request)
        if not getattr(request, 'organization', None) or not getattr(request, 'membership', None):
            return False
        return request.membership.is_active


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Allows access only to users who are ADMIN or OWNER of the requested organization.
    """
    def has_permission(self, request, view):
        _resolve_tenant_context(request)
        if not getattr(request, 'organization', None) or not getattr(request, 'membership', None):
            return False
        
        if not request.membership.is_active:
            return False
            
        from apps.organizations.models import OrganizationMembership
        return request.membership.role in [
            OrganizationMembership.Role.ADMIN,
            OrganizationMembership.Role.OWNER,
        ]


class IsOrganizationOwner(permissions.BasePermission):
    """
    Allows access only to the OWNER of the requested organization.
    """
    def has_permission(self, request, view):
        _resolve_tenant_context(request)
        if not getattr(request, 'organization', None) or not getattr(request, 'membership', None):
            return False
        
        if not request.membership.is_active:
            return False
            
        from apps.organizations.models import OrganizationMembership
        return request.membership.role == OrganizationMembership.Role.OWNER
