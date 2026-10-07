from rest_framework import serializers

from .models import Conversation, Document, DocumentChunk, Message


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "name", "file", "created_at"]
        read_only_fields = ["id", "created_at"]


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ["id", "document", "content", "chunk_index"]
        read_only_fields = ["id"]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id","conversation","document","question","answer","created_at"]
        read_only_fields = ["id", "answer", "created_at"]