from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationViewSet,
    DocumentViewSet,
    DocumentChunkViewSet,
    MessageViewSet
)


router = DefaultRouter()

router.register("conversations",ConversationViewSet,basename="conversation")
router.register("documents",DocumentViewSet,basename="document")
router.register("chunks",DocumentChunkViewSet,basename="chunk")
router.register("messages",MessageViewSet,basename="message")


urlpatterns = [
    path("", include(router.urls)),
]