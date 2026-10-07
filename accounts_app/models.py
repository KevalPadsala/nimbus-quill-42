from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    company = models.CharField(max_length=20,null=True,blank=True)
    phone = models.CharField(max_length=20,null=True,blank=True)