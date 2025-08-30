from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProfileViewSet, UserProfileView

router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profile')

urlpatterns = [
    path('', include(router.urls)),
    path("profile/<str:username>/", UserProfileView.as_view()),
]
