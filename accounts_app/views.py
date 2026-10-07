from django.shortcuts import render
# Create your views here.
from rest_framework import viewsets,generics
from .serializers import UserSerializer
from .models import User


class UserRegister(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
