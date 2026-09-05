from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.organizations.views import OrganizationViewSet, TeamViewSet, InvitationViewSet

router = DefaultRouter()
router.register(r'', OrganizationViewSet, basename='organizations')
router.register(r'team', TeamViewSet, basename='team')
router.register(r'invitations', InvitationViewSet, basename='invitations')

urlpatterns = [
    path('', include(router.urls)),
]
