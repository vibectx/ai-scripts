"""
День 13 — «а вдруг бот тихо отвечает плохо?». Не угадываем — ПРОВЕРЯЕМ.
Набор контрольных вопросов с ожидаемым смыслом прогоняется через бота, а вторая
LLM-«экзаменатор» выносит вердикт верно/неверно. Получаем оценку качества в цифрах
ещё до того, как бота увидит клиент.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-2/scripts/script-6.py
    # нужен запущенный Ollama с моделью nomic-embed-text
"""

import math
import os
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-2/scripts/script-6.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"

DOCS = [
    "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей.",
    "Вернуть товар можно в течение 14 дней, если он не был в использовании.",
    "Гарантия на технику — 12 месяцев, оформляется по кассовому чеку.",
]

# Контрольный набор: вопрос → что в правильном ответе обязано прозвучать.
EVAL = [
    ("Сколько стоит доставка по Москве?", "300 рублей"),
    ("За сколько дней можно вернуть товар?", "14 дней"),
    ("Какой срок гарантии на технику?", "12 месяцев"),
    ("А вы продаёте кофемашины?", "не знаю / нет информации"),
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


def answer(question):
    qv = embed(question, "search_query: ")
    context = "\n".join(sorted(DOCS, key=lambda d: cosine(qv, VECS[DOCS.index(d)]),
                               reverse=True)[:2])
    return giga([
        {"role": "system", "content": "Отвечай строго по документам ниже. Нет ответа — "
                                      "скажи «не знаю». Не выдумывай."},
        {"role": "user", "content": f"Документы:\n{context}\n\nВопрос: {question}"},
    ])


def judge(question, expected, got):
    """LLM-экзаменатор: совпал ли смысл ответа с ожиданием. Возвращает PASS/FAIL."""
    verdict = giga([
        {"role": "system", "content": "Ты проверяешь ответ бота. Сравни его с эталоном по "
                                      "СМЫСЛУ. Ответь одним словом: PASS или FAIL."},
        {"role": "user", "content": f"Вопрос: {question}\nЭталон: {expected}\n"
                                    f"Ответ бота: {got}"},
    ], temperature=0.0)
    return "PASS" if "PASS" in verdict.upper() else "FAIL"


if __name__ == "__main__":
    passed = 0
    for question, expected in EVAL:
        got = answer(question)
        verdict = judge(question, expected, got)
        passed += verdict == "PASS"
        mark = "✅" if verdict == "PASS" else "❌"
        print(f"{mark} {verdict}  {question}\n      ожидали: {expected}\n      ответ:   {got}\n")

    print(f"ИТОГ: {passed}/{len(EVAL)} пройдено "
          f"({passed / len(EVAL) * 100:.0f}%). Эту цифру и несём клиенту вместо «доверьтесь».")
