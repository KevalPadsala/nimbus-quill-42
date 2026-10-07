from django.db import models

# Create your models here.
from accounts_app.models import User

class Conversation(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="conversation")
    title = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    

class Document(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="document")
    name  = models.CharField(max_length=20)
    file = models.FileField(upload_to="documents/")
    created_at = models.DateTimeField(auto_now_add=True)

class DocumentChunk(models.Model):
    document = models.ForeignKey(Document,on_delete=models.CASCADE, related_name="chunks")
    content = models.TextField()
    chunk_index = models.PositiveIntegerField()

class Message(models.Model):
    conversation = models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name="messages")
    document = models.ManyToManyField(Document,blank=True,related_name="messages")
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


