import os

import faiss
import numpy as np
from openai import OpenAI

from .models import DocumentChunk


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    return response.data[0].embedding


def build_faiss_index(chunks):
    vectors = []

    for chunk in chunks:
        vector = get_embedding(chunk.content)
        vectors.append(vector)

    if not vectors:
        return None

    vectors = np.array(vectors).astype("float32")

    index = faiss.IndexFlatL2(len(vectors[0]))
    index.add(vectors)

    return index


def search_chunks(question, chunks, top_k=3):
    index = build_faiss_index(chunks)

    if index is None:
        return []

    question_vector = get_embedding(question)

    question_vector = np.array(
        [question_vector]
    ).astype("float32")

    distances, indexes = index.search(
        question_vector,
        min(top_k, len(chunks))
    )

    results = []

    for index_number in indexes[0]:
        results.append(chunks[index_number])

    return results


def generate_answer(question, chunks):
    context = ""

    for chunk in chunks:
        context += chunk.content + "\n\n"

    prompt = f"""
Answer the question using only the provided context.

Context:
{context}

Question:
{question}

If the answer is not present in the context, say:
"I could not find the answer in the provided documents."
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


def ask_question(question, document_ids):
    chunks = DocumentChunk.objects.filter(
        document_id__in=document_ids
    ).order_by("chunk_index")

    relevant_chunks = search_chunks(
        question,
        list(chunks)
    )

    answer = generate_answer(
        question,
        relevant_chunks
    )

    return answer