from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Conversation, Document, DocumentChunk, Message
from .serializers import (
    ConversationSerializer,
    DocumentSerializer,
    DocumentChunkSerializer,
    MessageSerializer
)
from .rag_service import ask_question


class ConversationViewSet(viewsets.ModelViewSet):

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DocumentViewSet(viewsets.ModelViewSet):

    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DocumentChunkViewSet(viewsets.ModelViewSet):

    serializer_class = DocumentChunkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DocumentChunk.objects.filter(
            document__user=self.request.user
        )


class MessageViewSet(viewsets.ModelViewSet):

    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(
            conversation__user=self.request.user
        )

    def perform_create(self, serializer):

        conversation = serializer.validated_data["conversation"]
        documents = serializer.validated_data["document"]

        if conversation.user != self.request.user:
            raise PermissionError("You cannot use this conversation.")

        document_ids = []

        for document in documents:

            if document.user != self.request.user:
                raise PermissionError(
                    "You cannot use this document."
                )

            document_ids.append(document.id)

        question = serializer.validated_data["question"]

        answer = ask_question(
            question,
            document_ids
        )

        serializer.save(
            answer=answer
        )