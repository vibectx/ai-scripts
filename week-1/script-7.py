"""
День 7 — весь бот поддержки в одном файле: RAG + GigaChat + ссылка на источник.

Это итог недели: найти в документах → ответить строго по ним → показать, откуда взято.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-1/scripts/script-7.py
"""

import math
import os
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-1/scripts/script-7.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"

# (источник, текст) — чтобы показать клиенту, откуда взят ответ.
DOCS = [
    ("Доставка", "Доставка по Москве — 300 рублей, бесплатно от 5000 рублей."),
    ("Возврат", "Вернуть товар можно в течение 14 дней, если он не использовался."),
    ("Гарантия", "Гарантия на технику — 12 месяцев по чеку."),
]


def giga(messages, temperature=0.1):
    token = httpx.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers={"Authorization": f"Basic {AUTH}", "RqUID": str(uuid.uuid4()),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"scope": "GIGACHAT_API_PERS"}, verify=VERIFY, timeout=20,
    ).json()["access_token"]
    r = httpx.post(
        "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "GigaChat", "messages": messages, "temperature": temperature},
        verify=VERIFY, timeout=60,
    )
    return r.json()["choices"][0]["message"]["content"].strip()


def embed(text, prefix):
    return ollama.embeddings(model="nomic-embed-text", prompt=prefix + text)["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


VECS = [embed(text, "search_document: ") for _, text in DOCS]


def answer(question):
    qv = embed(question, "search_query: ")
    src, text = max(zip(DOCS, VECS), key=lambda dv: cosine(qv, dv[1]))[0]   # самый близкий
    reply = giga([
        {"role": "system", "content": "Ответь на вопрос строго по тексту источника, не выдумывай."},
        {"role": "user", "content": f"Источник: {text}\n\nВопрос: {question}"},
    ])
    return f"{reply}\n\n📄 Источник: {src}"


if __name__ == "__main__":
    for q in ["Когда можно вернуть товар?", "Доставка в Москве платная?"]:
        print(f"\n❓ {q}\n💬 {answer(q)}")
