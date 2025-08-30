from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, ItemImageViewSet

router = DefaultRouter()
router.register(r'items', ItemViewSet)
router.register(r'item-images', ItemImageViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
