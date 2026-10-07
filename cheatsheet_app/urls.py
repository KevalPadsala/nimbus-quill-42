from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# router creates the CRUD urls for ViewSets automatically
router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="cs-product")
router.register("docs", views.KnowledgeDocViewSet, basename="cs-doc")

# all urls start with /cheatsheet/  (see knowledgehub/urls.py)
urlpatterns = [
    path("health/", views.health),

    path("categories/", views.CategoryListCreateView.as_view()),
    path("categories/<int:pk>/", views.CategoryDetailView.as_view()),

    path("chat/", views.ChatView.as_view()),
    path("chat/history/", views.ChatHistoryView.as_view()),
    path("summarize/", views.SummarizeView.as_view()),

    path("docs/upload/", views.DocUploadView.as_view()),
    path("ask/", views.AskView.as_view()),

    path("", include(router.urls)),
]
