"""
День 3 — RAG: бот отвечает СТРОГО по документам и не выдумывает.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-1/scripts/script-3.py
    # нужен запущенный Ollama с моделью nomic-embed-text (ollama pull nomic-embed-text)
"""

import math
import os
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-1/scripts/script-3.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"

# Документы «компании». Подставь сюда свои — логика не меняется.
DOCS = [
    "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей.",
    "Вернуть товар можно в течение 14 дней, если он не был в использовании.",
    "Гарантия на технику — 12 месяцев, оформляется по чеку.",
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


DOC_VECS = [embed(d, "search_document: ") for d in DOCS]   # считаем один раз на старте


def answer(question):
    qv = embed(question, "search_query: ")
    context = "\n".join(sorted(DOCS, key=lambda d: cosine(qv, DOC_VECS[DOCS.index(d)]),
                               reverse=True)[:2])
    return giga([
        {"role": "system", "content": "Отвечай СТРОГО по документам ниже. Если ответа в них "
                                      "нет — скажи «не знаю» и предложи менеджера. Не выдумывай."},
        {"role": "user", "content": f"Документы:\n{context}\n\nВопрос: {question}"},
    ])


if __name__ == "__main__":
    for q in ["Сколько стоит доставка по Москве?",   # есть в документах
              "А вы продаёте кофемашины?"]:           # этого НЕТ — бот должен отказаться
        print(f"\n❓ {q}\n💬 {answer(q)}")
