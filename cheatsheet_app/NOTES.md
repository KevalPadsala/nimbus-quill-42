# Interview Cheat Sheet: Django + DRF + LLM + RAG

Code for everything below lives in this app:

| File | What to copy from it |
|---|---|
| `models.py` | FK, null/blank, Decimal, auto_now, Meta ordering, JSONField |
| `serializers.py` | ModelSerializer, SerializerMethodField, `source=`, validation, plain Serializer |
| `views.py` | @api_view, APIView, generics, ModelViewSet, filters, search, ordering, @action, aggregate |
| `pagination.py` | PageNumber + LimitOffset pagination |
| `permissions.py` | IsOwner, IsOwnerOrReadOnly |
| `llm_service.py` | chat, chat history, summarize, JSON output, embeddings |
| `rag_service.py` | extract → chunk → embed → search → answer |
| `tests.py` | APITestCase, force_authenticate, mocking the LLM |

---

## 1. Steps for any "build an API" task (remember this order)

```
1. python manage.py startapp blog_app
2. settings.py  -> INSTALLED_APPS += "blog_app"
3. models.py    -> write models
4. python manage.py makemigrations && python manage.py migrate
5. serializers.py
6. views.py     (ModelViewSet for CRUD)
7. urls.py      (router.register) + include in project urls.py
8. admin.py     (register models, easy way to add test data)
9. test with Postman / curl
```

Talk while you code: *"I'll start with the models, then serializers, then a ViewSet, and filter by the logged-in user."*

---

## 2. Django ORM quick reference

```python
Product.objects.all()
Product.objects.filter(price__gte=100, is_active=True)   # AND
Product.objects.exclude(stock=0)
Product.objects.get(id=1)                                 # error if 0 or many rows
Product.objects.filter(name__icontains="phone")           # LIKE %phone% (case insensitive)
Product.objects.filter(category__name="Books")            # join through FK with __
Product.objects.filter(id__in=[1, 2, 3])
Product.objects.order_by("-price")                         # "-" = DESC
Product.objects.filter(...).first() / .count() / .exists()

from django.db.models import Q, F, Count, Sum, Avg
Product.objects.filter(Q(price__lt=10) | Q(stock=0))      # OR
Product.objects.filter(stock__lt=F("min_stock"))          # compare two columns
Product.objects.update(price=F("price") * 1.1)            # update in DB

Product.objects.aggregate(total=Sum("stock"))             # one result -> dict
Category.objects.annotate(n=Count("products"))            # value per row
Product.objects.values("category__name").annotate(n=Count("id"))   # GROUP BY

# N+1 problem fix
Product.objects.select_related("category")    # FK / OneToOne  (SQL JOIN)
Category.objects.prefetch_related("products") # reverse FK / M2M (2nd query)
```

`on_delete`: `CASCADE` (delete children too), `SET_NULL` (needs `null=True`), `PROTECT` (block delete).
`null=True` is for the database, `blank=True` is for validation.

---

## 3. DRF quick reference

**Which view?**
- Full CRUD on a model → `ModelViewSet` + router
- Only list / only create / detail → `generics.ListAPIView`, `CreateAPIView`, `RetrieveUpdateDestroyAPIView`
- Custom logic (LLM call, upload, calculations) → `APIView`
- Tiny endpoint → `@api_view`

**Common ViewSet hooks**
```python
def get_queryset(self):            # filter by user / query params
def perform_create(self, s):       # s.save(user=self.request.user)
def get_serializer_class(self):    # different serializer per action
@action(detail=True, methods=["post"])   # /products/1/toggle_active/
@action(detail=False)                    # /products/stats/
```

**Query params:** `request.query_params.get("x")` (GET). **Body:** `request.data` (POST/PUT).

**Validation:** `validate_<field>(self, value)` or `validate(self, data)`, raise `serializers.ValidationError`.
`serializer.is_valid(raise_exception=True)` returns a 400 response automatically.

**Status codes:** 200 OK, 201 Created, 204 No Content (delete), 400 Bad Request, 401 Not logged in,
403 Forbidden, 404 Not Found, 500 Server error, 502 Upstream (LLM) error.

**Pagination:** set `pagination_class` on the view, or set it globally in settings. In an APIView:
`paginator.paginate_queryset(qs, request)` and then `paginator.get_paginated_response(data)`.

**Filter / search / order:**
```python
filter_backends = [filters.SearchFilter, filters.OrderingFilter]
search_fields = ["name"]          # ?search=abc
ordering_fields = ["price"]       # ?ordering=-price
```

---

## 4. Auth (JWT) — already in accounts_app

```
POST /register/  {"username","email","password"}
POST /login/     {"username","password"}  -> {"access": "...", "refresh": "..."}
POST /refresh/   {"refresh": "..."}       -> new access token
Every request:   Header  Authorization: Bearer <access>
```
- Access token: short life (5 min by default). Refresh token: long life, used to get a new access token.
- JWT = header.payload.signature. The server does not store sessions (stateless).
- Always hash passwords: `User.objects.create_user(...)` or `user.set_password(pw)`.

---

## 5. LLM concepts

- **Messages:** `system` (rules), `user` (question), `assistant` (old replies).
- **LLMs have no memory.** To keep a conversation, send the old messages again every time (`chat_with_history`).
- **temperature:** 0 gives the same answer every time (facts, RAG, JSON). Higher is more creative.
- **Tokens:** about 4 characters per token. You pay per token, and the context window has a limit, so long text must be chunked or summarized.
- **Prompt template:** an f-string with instructions plus the data (see `summarize`).
- **Structured output:** `response_format={"type": "json_object"}`, then `json.loads`.
- **Keep the API key in `.env`**, never in code. Load it with `python-dotenv`.
- **Handle errors:** wrap LLM calls in try/except and return a 502 with a message.
- **Keep LLM code in a service file**, not inside views. It is easier to test and to switch providers.
- Slow calls → use streaming, or a background task (Celery) for long jobs.

---

## 6. RAG concepts

**Why RAG?** The LLM does not know your private documents. Instead of training a model, find the relevant text and put it in the prompt.

```
INDEX (once):  document -> extract text -> chunks -> embeddings -> store
QUERY:         question -> embedding -> top-k similar chunks -> prompt(context + question) -> LLM
```

- **Embedding:** text converted to a vector (a list of numbers). Similar meaning gives close vectors.
- **Chunking:** split the text into about 300–1000 characters with an overlap (50–100) so sentences are not cut. If chunks are too big, the context gets noisy. If they are too small, meaning is lost.
- **Similarity:** cosine similarity (1 = same direction). FAISS `IndexFlatL2` uses L2 distance (smaller = closer).
- **top_k:** how many chunks to send to the LLM (usually 3–5).
- **Vector stores:** FAISS (in memory, fast), Chroma, pgvector (Postgres), Pinecone.
  This app stores the vectors in a JSONField and uses numpy, which is fine for small data.
- **Reduce hallucination:** "answer only from the context, otherwise say you don't know", temperature 0, return the sources.
- **Store the embeddings at upload time.** Do not re-embed every chunk for every question (the main_app version rebuilds the FAISS index on each question).
- **Improvements to mention:** metadata filters (by user/document), hybrid search (keyword + vector),
  re-ranking, a better chunker (LangChain `RecursiveCharacterTextSplitter`), caching embeddings.

---

## 7. Common interview questions (short answers)

- **select_related vs prefetch_related?** JOIN for FK/OneToOne vs a separate query for reverse FK/M2M.
- **APIView vs ViewSet?** APIView is manual methods. ViewSet gives actions plus a router that generates the URLs.
- **What is a serializer?** It converts model ↔ JSON and validates input.
- **What is middleware?** Code that runs on every request/response (auth, CSRF, CORS).
- **What are signals?** Code that runs on model events (`post_save`), e.g. create a profile when a user is created.
- **How do you make an API secure?** JWT auth, permissions, filter the queryset by user, validate input, keep secrets in env, rate limiting, HTTPS.
- **How do you make it faster?** select_related, indexes, pagination, caching (Redis), background tasks, `only()`/`values()`.
- **How does RAG differ from fine-tuning?** RAG adds knowledge at query time (cheap, easy to update). Fine-tuning changes the model's behaviour/style (costly).
- **What if the LLM API is down or slow?** try/except, a timeout, retries, a friendly error message, and Celery for background work.

---

## 8. Test it quickly (curl)

```bash
# login -> copy "access"
curl -X POST http://127.0.0.1:8000/login/ -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin\"}"

curl http://127.0.0.1:8000/cheatsheet/products/?page=1 -H "Authorization: Bearer <access>"

curl -X POST http://127.0.0.1:8000/cheatsheet/chat/ -H "Authorization: Bearer <access>" -H "Content-Type: application/json" -d "{\"question\":\"What is Django?\"}"

curl -X POST http://127.0.0.1:8000/cheatsheet/docs/upload/ -H "Authorization: Bearer <access>" -F "title=My notes" -F "file=@notes.pdf"

curl -X POST http://127.0.0.1:8000/cheatsheet/ask/ -H "Authorization: Bearer <access>" -H "Content-Type: application/json" -d "{\"question\":\"What is in my notes?\"}"
```

All endpoints (prefix `/cheatsheet/`):

| Method | URL | What |
|---|---|---|
| GET | `health/` | no auth |
| GET/POST | `categories/` | APIView + manual pagination, `?search=` |
| GET/PUT/PATCH/DELETE | `categories/<id>/` | generic view |
| CRUD | `products/` | ViewSet, `?category= &min_price= &max_price= &is_active= &search= &ordering= &page=` |
| GET | `products/stats/` | aggregate + group by |
| POST | `products/<id>/toggle_active/` | custom action |
| POST | `chat/` | LLM question (saved to ChatLog) |
| GET | `chat/history/` | paginated |
| POST | `summarize/` | LLM summary |
| POST | `docs/upload/` | file (pdf/txt) or text → chunks + embeddings |
| GET/DELETE | `docs/`, `docs/<id>/` | my documents |
| GET | `docs/<id>/chunks/` | paginated chunks |
| POST | `ask/` | RAG answer + sources |

Run the tests (no API key needed, the LLM is mocked):
```bash
python manage.py test cheatsheet_app
```
