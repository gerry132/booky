# messaging/urls.py
from rest_framework.routers import DefaultRouter
from .views import (
    ConversationViewSet,
    MessageViewSet,
    UserBlockViewSet,
    UserReportViewSet)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename="conversation")
router.register(r'messages', MessageViewSet, basename="messages")
router.register(r'blocks', UserBlockViewSet, basename="blocks")
router.register(r'reports', UserReportViewSet, basename="reports")

urlpatterns = router.urls
