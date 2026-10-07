from rest_framework import serializers

from .models import Category, Product, ChatLog, KnowledgeDoc, KnowledgeChunk


# ---------------------------------------------------------------------
# ModelSerializer = auto fields from the model (most common)
# ---------------------------------------------------------------------
class CategorySerializer(serializers.ModelSerializer):
    # extra computed field -> needs get_<field_name> method
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "product_count", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_product_count(self, obj):
        return obj.products.count()


class ProductSerializer(serializers.ModelSerializer):
    # show a field from a related model (read only)
    category_name = serializers.ReadOnlyField(source="category.name")
    # show who owns it, but user is set in the view (perform_create), not by the client
    username = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Product
        fields = [
            "id", "username", "category", "category_name", "name", "description",
            "price", "stock", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # field level validation -> validate_<field_name>
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value

    # object level validation -> check several fields together
    def validate(self, data):
        if data.get("is_active") and data.get("stock") == 0:
            raise serializers.ValidationError("Active product must have stock.")
        return data


# ---------------------------------------------------------------------
# Plain Serializer = for input that is NOT a model (e.g. LLM prompt)
# ---------------------------------------------------------------------
class ChatInputSerializer(serializers.Serializer):
    question = serializers.CharField()
    system_prompt = serializers.CharField(required=False, default="You are a helpful assistant.")


class SummarizeInputSerializer(serializers.Serializer):
    text = serializers.CharField()
    max_words = serializers.IntegerField(required=False, default=100, min_value=10, max_value=500)


class ChatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatLog
        fields = ["id", "question", "answer", "created_at"]


# ---------------------------------------------------------------------
# RAG serializers
# ---------------------------------------------------------------------
class KnowledgeChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeChunk
        fields = ["id", "chunk_index", "content"]  # never return the embedding, it is huge


class KnowledgeDocSerializer(serializers.ModelSerializer):
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeDoc
        fields = ["id", "title", "chunk_count", "created_at"]

    def get_chunk_count(self, obj):
        return obj.chunks.count()


class DocUploadSerializer(serializers.Serializer):
    """Send either a file (pdf / txt) OR raw text."""
    title = serializers.CharField(max_length=200)
    file = serializers.FileField(required=False)
    text = serializers.CharField(required=False)

    def validate(self, data):
        if not data.get("file") and not data.get("text"):
            raise serializers.ValidationError("Send a 'file' or 'text'.")
        return data


class AskInputSerializer(serializers.Serializer):
    question = serializers.CharField()
    top_k = serializers.IntegerField(required=False, default=3, min_value=1, max_value=10)
    # optional: only search inside these documents
    document_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
