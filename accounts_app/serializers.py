

from rest_framework import serializers
from .models import User
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ['username', 'email', 'password','company']

    def create(self,validated_data):
        return User.objects.create(**validated_data)
        
