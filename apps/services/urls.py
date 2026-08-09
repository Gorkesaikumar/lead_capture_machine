"""
URL configuration for Photography Services and Packages.
"""
from rest_framework.routers import DefaultRouter
from apps.services.views import PackageViewSet, PhotographyServiceViewSet

app_name = "services"

router = DefaultRouter()
router.register("packages", PackageViewSet, basename="package")
router.register("", PhotographyServiceViewSet, basename="service")

urlpatterns = router.urls
