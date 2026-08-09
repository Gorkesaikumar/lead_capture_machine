"""
URL configuration for Customers endpoints.
"""
from rest_framework.routers import DefaultRouter
from apps.customers.views import CustomerViewSet

app_name = "customers"

router = DefaultRouter()
router.register("", CustomerViewSet, basename="customer")

urlpatterns = router.urls
