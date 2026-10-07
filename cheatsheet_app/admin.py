from django.contrib import admin

from .models import Category, ChatLog, KnowledgeChunk, KnowledgeDoc, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "created_at"]
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "price", "stock", "is_active", "category", "user"]
    list_filter = ["is_active", "category"]
    search_fields = ["name", "description"]
    list_per_page = 20  # pagination in admin


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "question", "created_at"]


@admin.register(KnowledgeDoc)
class KnowledgeDocAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "user", "created_at"]


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ["id", "document", "chunk_index"]
    exclude = ["embedding"]  # too big to show
