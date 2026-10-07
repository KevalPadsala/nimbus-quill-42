"""
Run:  python manage.py test cheatsheet_app

LLM calls are MOCKED (fake) -> tests run without an API key and cost nothing.
"""
from unittest.mock import patch

from rest_framework.test import APITestCase

from accounts_app.models import User

from .models import Category, KnowledgeChunk, Product
from .rag_service import cosine_similarity, split_text


class ProductApiTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client.force_authenticate(user=self.user)  # skip JWT login in tests
        self.category = Category.objects.create(name="Electronics")

    def test_create_product(self):
        data = {"name": "Phone", "price": "199.99", "stock": 5, "category": self.category.id}
        response = self.client.post("/cheatsheet/products/", data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(response.data["category_name"], "Electronics")

    def test_price_validation(self):
        data = {"name": "Bad", "price": "0", "stock": 5}
        response = self.client.post("/cheatsheet/products/", data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_pagination_and_filter(self):
        for i in range(7):
            Product.objects.create(user=self.user, name=f"P{i}", price=10 + i, stock=1)

        response = self.client.get("/cheatsheet/products/")
        self.assertEqual(response.data["count"], 7)
        self.assertEqual(len(response.data["results"]), 5)  # page_size = 5

        response = self.client.get("/cheatsheet/products/?min_price=15")
        self.assertEqual(response.data["count"], 2)

    def test_other_user_cannot_see_my_products(self):
        other = User.objects.create_user(username="other", password="pass12345")
        Product.objects.create(user=other, name="Secret", price=10, stock=1)

        response = self.client.get("/cheatsheet/products/")
        self.assertEqual(response.data["count"], 0)

    def test_login_required(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/cheatsheet/products/")
        self.assertEqual(response.status_code, 401)


class LlmApiTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client.force_authenticate(user=self.user)

    # patch the function where it is USED (cheatsheet_app.llm_service.chat)
    @patch("cheatsheet_app.llm_service.chat", return_value="Hello from fake LLM")
    def test_chat(self, mock_chat):
        response = self.client.post("/cheatsheet/chat/", {"question": "hi"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["answer"], "Hello from fake LLM")
        mock_chat.assert_called_once()


class RagTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client.force_authenticate(user=self.user)

    def test_split_text(self):
        chunks = split_text("a" * 1200, chunk_size=500, overlap=50)
        self.assertEqual(len(chunks), 3)

    def test_cosine_similarity(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)

    @patch("cheatsheet_app.rag_service.chat", return_value="Django is a web framework.")
    @patch("cheatsheet_app.rag_service.get_embedding", return_value=[1.0, 0.0])
    @patch("cheatsheet_app.rag_service.get_embeddings")
    def test_upload_and_ask(self, mock_embeddings, mock_embedding, mock_chat):
        mock_embeddings.side_effect = lambda texts: [[1.0, 0.0] for _ in texts]

        response = self.client.post(
            "/cheatsheet/docs/upload/",
            {"title": "Notes", "text": "Django is a Python web framework."},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(KnowledgeChunk.objects.count(), 1)

        response = self.client.post("/cheatsheet/ask/", {"question": "What is Django?"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["answer"], "Django is a web framework.")
        self.assertEqual(len(response.data["sources"]), 1)
