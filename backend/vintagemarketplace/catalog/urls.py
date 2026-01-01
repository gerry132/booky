from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, BrandViewSet, TagViewSet

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="catalog-categories")
router.register(r"brands", BrandViewSet, basename="catalog-brands")
router.register(r"tags", TagViewSet, basename="catalog-tags")

urlpatterns = router.urls
