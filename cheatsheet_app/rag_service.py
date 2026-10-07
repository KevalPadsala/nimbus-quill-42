"""
RAG = Retrieval Augmented Generation

  UPLOAD:  file -> extract text -> split into chunks -> embed each chunk -> save in DB
  ASK:     question -> embed question -> find most similar chunks -> send chunks + question to LLM

Only numpy is used for search (cosine similarity) so it is easy to read.
For many documents use FAISS / Chroma / pgvector instead (see main_app/rag_service.py for FAISS).
"""
import numpy as np
from pypdf import PdfReader

from .llm_service import chat, get_embedding, get_embeddings
from .models import KnowledgeDoc, KnowledgeChunk


# ---------------------------------------------------------------------
# STEP 1: extract text from an uploaded file
# ---------------------------------------------------------------------
def extract_text(uploaded_file):
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text

    # .txt / .md / anything text
    return uploaded_file.read().decode("utf-8", errors="ignore")


# ---------------------------------------------------------------------
# STEP 2: split text into chunks
#   chunk_size = how many characters per chunk
#   overlap    = repeat some characters so a sentence is not cut in half
# ---------------------------------------------------------------------
def split_text(text, chunk_size=500, overlap=50):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap

    return chunks


# ---------------------------------------------------------------------
# STEP 3: create document + chunks + embeddings
# ---------------------------------------------------------------------
def index_document(user, title, text):
    document = KnowledgeDoc.objects.create(user=user, title=title, content=text)

    chunks = split_text(text)
    if not chunks:
        return document

    embeddings = get_embeddings(chunks)  # one API call for all chunks

    for i in range(len(chunks)):
        KnowledgeChunk.objects.create(
            document=document,
            chunk_index=i,
            content=chunks[i],
            embedding=embeddings[i],
        )

    return document


# ---------------------------------------------------------------------
# STEP 4: similarity search
#   cosine similarity: 1 = same meaning, 0 = unrelated
# ---------------------------------------------------------------------
def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_chunks(user, question, top_k=3, document_ids=None):
    chunks = KnowledgeChunk.objects.filter(document__user=user).select_related("document")
    if document_ids:
        chunks = chunks.filter(document_id__in=document_ids)

    question_embedding = get_embedding(question)

    scored = []
    for chunk in chunks:
        score = cosine_similarity(question_embedding, chunk.embedding)
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)  # highest score first
    return scored[:top_k]


# ---------------------------------------------------------------------
# STEP 5: build prompt with context and ask the LLM
# ---------------------------------------------------------------------
RAG_SYSTEM_PROMPT = (
    "You answer questions using ONLY the given context. "
    "If the answer is not in the context, say: "
    "\"I could not find the answer in the provided documents.\""
)


def answer_question(user, question, top_k=3, document_ids=None):
    results = search_chunks(user, question, top_k, document_ids)

    if not results:
        return {"answer": "No documents found. Upload a document first.", "sources": []}

    context = ""
    for score, chunk in results:
        context += f"[{chunk.document.title} - part {chunk.chunk_index}]\n{chunk.content}\n\n"

    prompt = f"Context:\n{context}\nQuestion: {question}"
    answer = chat(prompt, system_prompt=RAG_SYSTEM_PROMPT, temperature=0)

    # return sources too -> user can check where the answer came from
    sources = []
    for score, chunk in results:
        sources.append({
            "document_id": chunk.document.id,
            "document_title": chunk.document.title,
            "chunk_index": chunk.chunk_index,
            "score": round(score, 3),
            "content": chunk.content[:200],
        })

    return {"answer": answer, "sources": sources}
