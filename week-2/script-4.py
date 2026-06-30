"""
День 11 — живой диалог: клиент уточняет, а бот держит нить разговора.
Проблема: на вопрос «а бесплатная бывает?» нет контекста — непонятно, о чём речь.
Решение: перед поиском по документам бот ПЕРЕПИСЫВАЕТ уточняющий вопрос в полный,
опираясь на историю диалога, и только потом ищет ответ.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-2/scripts/script-4.py
    # нужен запущенный Ollama с моделью nomic-embed-text
"""

import math
import os
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-2/scripts/script-4.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"

DOCS = [
    "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей.",
    "В регионы доставка транспортной компанией, срок 3–7 рабочих дней.",
    "Вернуть товар можно в течение 14 дней, если он не был в использовании.",
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


VECS = [embed(d, "search_document: ") for d in DOCS]


def standalone(question, history):
    """Уточняющий вопрос → самостоятельный, с учётом предыдущих реплик."""
    if not history:
        return question
    chat = "\n".join(f"{role}: {text}" for role, text in history)
    return giga([
        {"role": "system", "content": "Перепиши последний вопрос пользователя в "
                                      "самостоятельный, подставив контекст из диалога. "
                                      "Верни ТОЛЬКО переписанный вопрос, без пояснений."},
        {"role": "user", "content": f"Диалог:\n{chat}\n\nПоследний вопрос: {question}"},
    ], temperature=0.2)


def retrieve(query):
    qv = embed(query, "search_query: ")
    return max(DOCS, key=lambda d: cosine(qv, VECS[DOCS.index(d)]))


def reply(question, history):
    query = standalone(question, history)          # ← ключевой шаг: восстановили контекст
    context = retrieve(query)
    ans = giga([
        {"role": "system", "content": "Отвечай кратко и только по документу ниже."},
        {"role": "user", "content": f"Документ: {context}\n\nВопрос: {query}"},
    ])
    return query, ans


if __name__ == "__main__":
    history = []
    for q in ["Сколько стоит доставка по Москве?",
              "А бесплатная бывает?",            # без контекста непонятно — про что
              "А в регионы как?"]:               # снова уточнение
        rewritten, ans = reply(q, history)
        print(f"\n🙋 {q}")
        if rewritten != q:
            print(f"   ↳ бот понял как: «{rewritten}»")
        print(f"🤖 {ans}")
        history += [("Клиент", q), ("Бот", ans)]   # копим память диалога
