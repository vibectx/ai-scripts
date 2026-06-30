"""
День 10 — доверие к боту: он показывает ИСТОЧНИК. Каждый ответ помечен файлом
и точным фрагментом, по которому он составлен. Клиент может проверить — это и есть
главное отличие RAG-бота от «болтливой» нейросети.

Скрипт отвечает на вопрос и рядом показывает: из какого документа взят ответ,
какой именно фрагмент и насколько он близок к вопросу (похожесть).

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-2/scripts/script-3.py
    # нужен запущенный Ollama с моделью nomic-embed-text
    # нет сертификата Минцифры? добавь GIGACHAT_VERIFY_SSL=0
"""

import math
import os
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-2/scripts/script-3.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"

# (файл-источник, текст). В реальном боте сюда приходят куски из документов клиента.
DOCS = [
    ("delivery.md", "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей."),
    ("returns.md", "Вернуть товар можно в течение 14 дней, если он не был в использовании."),
    ("warranty.md", "Гарантия на технику — 12 месяцев, оформляется по кассовому чеку."),
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
    score, (src, text) = max(((cosine(qv, v), d) for v, d in zip(VECS, DOCS)),
                             key=lambda x: x[0])
    reply = giga([
        {"role": "system", "content": "Ответь на вопрос строго по тексту источника, "
                                      "не добавляй ничего от себя."},
        {"role": "user", "content": f"Источник: {text}\n\nВопрос: {question}"},
    ])
    # Ответ + проверяемая ссылка: файл, фрагмент и близость — клиент может перепроверить.
    return (f"💬 {reply}\n"
            f"   📄 источник: {src}  (похожесть {score:.2f})\n"
            f"   ❝{text}❞")


if __name__ == "__main__":
    for q in ["Когда можно вернуть товар?", "Сколько действует гарантия?"]:
        print(f"\n❓ {q}\n{answer(q)}")
