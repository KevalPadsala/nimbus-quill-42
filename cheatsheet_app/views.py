"""
4 ways to write an API in DRF (from most manual -> most automatic):

  1. @api_view function      -> tiny endpoints (health check, one-off actions)
  2. APIView                 -> full control, you write get/post yourself
  3. generics.XxxAPIView     -> standard list/create/detail with little code
  4. ModelViewSet + router   -> full CRUD (list, create, retrieve, update, delete) in ~5 lines
"""
from django.db.models import Avg, Count, Sum
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import llm_service, rag_service
from .models import Category, ChatLog, KnowledgeDoc, Product
from .pagination import SmallPagination
from .permissions import IsOwner
from .serializers import (
    AskInputSerializer,
    CategorySerializer,
    ChatInputSerializer,
    ChatLogSerializer,
    DocUploadSerializer,
    KnowledgeChunkSerializer,
    KnowledgeDocSerializer,
    ProductSerializer,
    SummarizeInputSerializer,
)


# =====================================================================
# 1) FUNCTION BASED VIEW
# =====================================================================
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})


# =====================================================================
# 2) APIView - write everything yourself (incl. manual pagination)
# =====================================================================
class CategoryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = Category.objects.all().order_by("name")

        # optional search: ?search=elec
        search = request.query_params.get("search")
        if search:
            categories = categories.filter(name__icontains=search)

        # manual pagination inside APIView
        paginator = SmallPagination()
        page = paginator.paginate_queryset(categories, request)
        serializer = CategorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# 3) GENERIC VIEW - detail (GET / PUT / PATCH / DELETE one category)
# =====================================================================
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


# =====================================================================
# 4) MODEL VIEWSET - full CRUD + filter + search + ordering + pagination
#
#   GET    /products/                      list (paginated)
#   POST   /products/                      create
#   GET    /products/1/                    retrieve
#   PUT    /products/1/  PATCH /products/1/ update
#   DELETE /products/1/                    delete
#
#   GET /products/?category=1&min_price=10&max_price=500&is_active=true
#   GET /products/?search=phone            (search in name/description)
#   GET /products/?ordering=-price         (sort, "-" = descending)
#   GET /products/?page=2&page_size=10
#   GET  /products/stats/                  custom action (list level)
#   POST /products/1/toggle_active/        custom action (detail level)
# =====================================================================
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    pagination_class = SmallPagination

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "category__name"]
    ordering_fields = ["price", "created_at", "name", "stock"]

    def get_queryset(self):
        # only my products + select_related avoids extra query per row (N+1 problem)
        queryset = Product.objects.filter(user=self.request.user).select_related("category", "user")

        # manual filters from query params
        category = self.request.query_params.get("category")
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        is_active = self.request.query_params.get("is_active")

        if category:
            queryset = queryset.filter(category_id=category)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset

    def perform_create(self, serializer):
        # set the owner from the logged in user (client never sends user)
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        data = self.get_queryset().aggregate(
            total_products=Count("id"),
            total_stock=Sum("stock"),
            average_price=Avg("price"),
        )
        # group by: products per category
        data["per_category"] = list(
            self.get_queryset().values("category__name").annotate(count=Count("id"))
        )
        return Response(data)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        product = self.get_object()  # also runs IsOwner check
        product.is_active = not product.is_active
        product.save()
        return Response(ProductSerializer(product).data)


# =====================================================================
# 5) LLM APIs
# =====================================================================
class ChatView(APIView):
    """POST {"question": "...", "system_prompt": "..."} -> answer from the LLM"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # auto 400 response on error

        question = serializer.validated_data["question"]
        system_prompt = serializer.validated_data["system_prompt"]

        try:
            answer = llm_service.chat(question, system_prompt)
        except Exception as e:
            return Response({"error": f"LLM error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        log = ChatLog.objects.create(user=request.user, question=question, answer=answer)
        return Response(ChatLogSerializer(log).data, status=status.HTTP_201_CREATED)


class SummarizeView(APIView):
    """POST {"text": "...", "max_words": 50}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SummarizeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            summary = llm_service.summarize(
                serializer.validated_data["text"],
                serializer.validated_data["max_words"],
            )
        except Exception as e:
            return Response({"error": f"LLM error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"summary": summary})


class ChatHistoryView(generics.ListAPIView):
    """GET /chat/history/?page=1  -> my old questions (paginated)"""
    serializer_class = ChatLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        return ChatLog.objects.filter(user=self.request.user)


# =====================================================================
# 6) RAG APIs
# =====================================================================
class DocUploadView(APIView):
    """
    POST multipart:  title=My notes, file=@notes.pdf
    or   JSON:       {"title": "My notes", "text": "long text ..."}
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # accept files + json

    def post(self, request):
        serializer = DocUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data.get("file")
        if uploaded_file:
            text = rag_service.extract_text(uploaded_file)
        else:
            text = serializer.validated_data["text"]

        if not text.strip():
            return Response({"error": "No text found in the file."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            document = rag_service.index_document(request.user, serializer.validated_data["title"], text)
        except Exception as e:
            return Response({"error": f"Embedding error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(KnowledgeDocSerializer(document).data, status=status.HTTP_201_CREATED)


class KnowledgeDocViewSet(viewsets.ModelViewSet):
    """
    GET    /docs/           my documents (paginated)
    GET    /docs/1/         one document
    DELETE /docs/1/         delete document + its chunks (CASCADE)
    GET    /docs/1/chunks/  chunks of a document (paginated)
    (create is done by DocUploadView because it needs extract + embed)
    """
    serializer_class = KnowledgeDocSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SmallPagination
    http_method_names = ["get", "delete"]  # trick: allow only these methods

    def get_queryset(self):
        return KnowledgeDoc.objects.filter(user=self.request.user)

    @action(detail=True, methods=["get"])
    def chunks(self, request, pk=None):
        document = self.get_object()
        page = self.paginate_queryset(document.chunks.all())
        serializer = KnowledgeChunkSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class AskView(APIView):
    """POST {"question": "...", "top_k": 3, "document_ids": [1, 2]} -> answer + sources"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AskInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = rag_service.answer_question(
                user=request.user,
                question=serializer.validated_data["question"],
                top_k=serializer.validated_data["top_k"],
                document_ids=serializer.validated_data.get("document_ids"),
            )
        except Exception as e:
            return Response({"error": f"RAG error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(result)
