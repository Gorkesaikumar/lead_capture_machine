from rest_framework.routers import DefaultRouter
from .views import AutomationViewSet, ExecutionViewSet

router = DefaultRouter()
router.register("history", ExecutionViewSet, basename="automation-history")
router.register("", AutomationViewSet, basename="automation")
urlpatterns = router.urls
