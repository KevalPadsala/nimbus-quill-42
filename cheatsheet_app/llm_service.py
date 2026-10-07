"""
All LLM calls in ONE place. Views only call these functions.

Setup:
    pip install openai python-dotenv
    .env file  ->  OPENAI_API_KEY=sk-...
"""
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads .env into environment variables

CHAT_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"


def get_client():
    # created inside a function so the project still starts when the key is missing
    # OpenAI() reads OPENAI_API_KEY from the environment automatically
    return OpenAI()


# ---------------------------------------------------------------------
# 1) Simple question -> answer
# ---------------------------------------------------------------------
def chat(question, system_prompt="You are a helpful assistant.", temperature=0.3):
    client = get_client()
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=temperature,  # 0 = same answer every time, 1 = creative
        messages=[
            {"role": "system", "content": system_prompt},  # rules / personality
            {"role": "user", "content": question},          # the question
        ],
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------
# 2) Chat with history (LLM has no memory -> send old messages every time)
#    messages = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}, ...]
# ---------------------------------------------------------------------
def chat_with_history(messages, system_prompt="You are a helpful assistant."):
    client = get_client()
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "system", "content": system_prompt}] + messages,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------
# 3) Summarize  (just a prompt template around chat())
# ---------------------------------------------------------------------
def summarize(text, max_words=100):
    prompt = f"Summarize the following text in at most {max_words} words.\n\nText:\n{text}"
    return chat(prompt)


# ---------------------------------------------------------------------
# 4) Get structured JSON back (classification / extraction tasks)
#    example: extract_json("I want a refund, item broken",
#                          "Return {\"sentiment\": positive|negative, \"category\": string}")
# ---------------------------------------------------------------------
def extract_json(text, instructions):
    client = get_client()
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        response_format={"type": "json_object"},  # forces valid JSON
        messages=[
            {"role": "system", "content": "Reply only with JSON. " + instructions},
            {"role": "user", "content": text},
        ],
    )
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------
# 5) Embeddings (text -> list of numbers). Used by RAG.
# ---------------------------------------------------------------------
def get_embedding(text):
    client = get_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def get_embeddings(texts):
    # one API call for many texts = faster + cheaper than calling get_embedding in a loop
    client = get_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
