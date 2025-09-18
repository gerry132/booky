from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, ItemImageViewSet, WishlistViewSet

router = DefaultRouter()
router.register(r'items', ItemViewSet)
router.register(r'item-images', ItemImageViewSet)
router.register(r"wishlist", WishlistViewSet, basename="wishlist")


urlpatterns = [
    path('', include(router.urls)),
]
