import uuid
from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.mixins import TenantViewSetMixin
from apps.organizations.models import Organization, OrganizationMembership, OrganizationInvitation
from apps.organizations.permissions import IsOrganizationMember, IsOrganizationAdmin, IsOrganizationOwner
from apps.organizations.serializers import (
    OrganizationSerializer,
    OrganizationMembershipSerializer,
    OrganizationInvitationSerializer,
    InviteMemberSerializer,
    AcceptInviteSerializer
)

class OrganizationViewSet(viewsets.GenericViewSet):
    """
    Manage the active organization settings.
    Requires Admin or Owner permissions to modify.
    """
    serializer_class = OrganizationSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'partial_update_current']:
            return [IsAuthenticated(), IsOrganizationAdmin()]
        return [IsAuthenticated(), IsOrganizationMember()]

    def get_object(self):
        return self.request.organization

    @action(detail=False, methods=['get'])
    def current(self, request):
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    @current.mapping.patch
    def partial_update_current(self, request):
        org = self.get_object()
        serializer = self.get_serializer(org, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TeamViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = OrganizationMembership.objects.all()
    """
    Manage organization team members.
    Admins can modify/remove members (except Owners).
    """
    serializer_class = OrganizationMembershipSerializer

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Use invitations to add a team member."}, status=405)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOrganizationAdmin()]
        return [IsAuthenticated(), IsOrganizationMember()]

    def get_queryset(self):
        qs = OrganizationMembership.objects.all().order_by("created_at", "id")
        if not hasattr(self.request, "organization") or not self.request.organization:
            return qs.none()
        return qs.filter(organization=self.request.organization).select_related("user")

    def perform_update(self, serializer):
        membership = self.get_object()
        if membership.role == OrganizationMembership.Role.OWNER:
            raise PermissionDenied("Cannot modify the OWNER of the organization.")
        
        # Don't allow changing role to OWNER
        if serializer.validated_data.get('role') == OrganizationMembership.Role.OWNER:
            raise ValidationError("Cannot assign OWNER role.")

        serializer.save()

    def perform_destroy(self, instance):
        if instance.role == OrganizationMembership.Role.OWNER:
            raise PermissionDenied("Cannot remove the OWNER of the organization.")
        instance.delete()


class InvitationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]
    queryset = OrganizationInvitation.objects.all()
    """
    Manage invitations.
    Admins can invite and revoke.
    Public can accept with token.
    """
    def get_permissions(self):
        if self.action == 'accept':
            return [IsAuthenticated()]
        if self.action in ['create', 'destroy']:
            return [IsAuthenticated(), IsOrganizationAdmin()]
        return [IsAuthenticated(), IsOrganizationMember()]

    def get_queryset(self):
        qs = OrganizationInvitation.objects.all()
        if not hasattr(self.request, "organization") or not self.request.organization:
            return qs.none()
        return qs.filter(organization=self.request.organization).select_related("invited_by").order_by("-created_at")

    def get_serializer_class(self):
        if self.action == 'create':
            return InviteMemberSerializer
        if self.action == 'accept':
            return AcceptInviteSerializer
        return OrganizationInvitationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        role = serializer.validated_data['role']
        
        # Check if user is already a member
        from apps.accounts.models import User
        user = User.objects.filter(email=email).first()
        if user and OrganizationMembership.objects.filter(organization=request.organization, user=user).exists():
            return Response({"detail": "User is already a member of this organization."}, status=status.HTTP_400_BAD_REQUEST)
            
        from django.conf import settings
        from django.core.mail import send_mail
        if not settings.EMAIL_HOST and "locmem" not in settings.EMAIL_BACKEND:
            return Response({"detail": "Invitation email is not configured. Contact your administrator."}, status=503)

        # Update or create invitation
        invitation, created = OrganizationInvitation.objects.update_or_create(
            organization=request.organization,
            email=email,
            defaults={
                'role': role,
                'invited_by': request.user,
                'status': OrganizationInvitation.Status.PENDING,
                'expires_at': timezone.now() + timedelta(days=7),
                'token': uuid.uuid4()
            }
        )
        
        try:
            url = f"{settings.FRONTEND_URL}/accept-invite?token={invitation.token}"
            send_mail("Join your V4 Studio team", f"You were invited to {request.organization.name}. Sign in with this email address, then open:\n{url}\nThis invitation expires in seven days.", settings.DEFAULT_FROM_EMAIL, [invitation.email])
        except Exception:
            return Response({"detail": "Invitation was saved but email delivery failed. Retry to send a new invitation."}, status=503)
        
        result_serializer = OrganizationInvitationSerializer(invitation)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def accept(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            invitation = OrganizationInvitation.objects.get(
                token=token, 
                status=OrganizationInvitation.Status.PENDING,
                expires_at__gt=timezone.now()
            )
        except OrganizationInvitation.DoesNotExist:
            return Response({"detail": "Invalid or expired invitation token."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Ensure the user's email matches the invitation email (or just allow if they click the link)
        if request.user.email.casefold() != invitation.email.casefold():
            return Response({"detail": "This invitation was sent to a different email address."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Create membership
        OrganizationMembership.objects.update_or_create(
            organization=invitation.organization,
            user=request.user,
            defaults={
                'role': invitation.role,
                'is_active': True
            }
        )
        
        invitation.status = OrganizationInvitation.Status.ACCEPTED
        invitation.save()
        
        return Response({"detail": "Invitation accepted successfully.", "organization_id": str(invitation.organization_id)})
