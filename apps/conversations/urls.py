"""
URL configuration for Conversations endpoints.
"""
from rest_framework.routers import DefaultRouter
from apps.conversations.views import ConversationViewSet

app_name = "conversations"

router = DefaultRouter()
router.register("", ConversationViewSet, basename="conversation")

urlpatterns = router.urls
