

from django.contrib import admin
from django.urls import path,include
from .views import UserRegister
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
urlpatterns = [
    path("register/",UserRegister.as_view()),
    path("login/",TokenObtainPairView.as_view()),
    path("refresh/",TokenRefreshView.as_view())
]
