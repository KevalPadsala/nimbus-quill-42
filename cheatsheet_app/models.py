from django.db import models

from accounts_app.models import User


# =====================================================================
# 1) NORMAL CRUD EXAMPLE  (Category -> Product)
#    Copy this when the task is "build an API for X" (tasks, books, products...)
# =====================================================================

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    # who created it -> used to show "only my products"
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="products")

    # null=True -> allowed empty in DB, blank=True -> allowed empty in forms/serializers
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)  # set once on create
    updated_at = models.DateTimeField(auto_now=True)      # set on every save

    class Meta:
        ordering = ["-created_at"]  # newest first (also needed for clean pagination)

    def __str__(self):
        return self.name


# =====================================================================
# 2) LLM EXAMPLE  - save every question/answer the user asked the LLM
# =====================================================================

class ChatLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_logs")
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# =====================================================================
# 3) RAG EXAMPLE  - document -> chunks (each chunk keeps its embedding)
# =====================================================================

class KnowledgeDoc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="knowledge_docs")
    title = models.CharField(max_length=200)
    content = models.TextField()  # full extracted text
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(KnowledgeDoc, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    # embedding is just a list of floats -> JSONField is the simplest way to store it
    # (in production you would use pgvector / FAISS / Chroma)
    embedding = models.JSONField(default=list)

    class Meta:
        ordering = ["document", "chunk_index"]
