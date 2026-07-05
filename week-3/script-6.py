"""
День 20 — карточка готовности пилота. Прежде чем обещать бизнесу бота, показываем
конкретную картину: на что бот по ИХ документам уже отвечает, где база пустая и что
стоит дослать. Клиент видит не «доверьтесь», а «из ваших документов бот уже закрывает
12 из 15 частых вопросов».

Как работает: берём загруженную базу (индекс из script-1.py, если он есть, иначе —
демо-документы), прогоняем список типовых вопросов бизнеса и по каждому решаем —
уверенно ли бот отвечает. Критерий: нашёлся близкий кусок (похожесть выше порога) И
модель-судья подтвердила, что во фрагменте есть ответ. На выходе — отчёт-карточка.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-3/scripts/script-6.py
    # нужен Ollama с nomic-embed-text; нет сертификата Минцифры? GIGACHAT_VERIFY_SSL=0
    # если сначала запустить script-1.py — карточка соберётся по client_index.json
"""

import json
import math
import os
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-3/scripts/script-6.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"
INDEX_PATH = os.path.join(os.path.dirname(__file__), "client_index.json")
SCORE_MIN = 0.55          # порог похожести: ниже — считаем, что в базе ничего похожего нет

# Типовые вопросы, которые задаёт клиент бизнесу. Под конкретную нишу — свой список.
TYPICAL_QUESTIONS = [
    "Сколько стоит доставка?",
    "Есть ли бесплатная доставка?",
    "Как вернуть товар?",
    "Какая гарантия на товар?",
    "Есть ли скидки постоянным клиентам?",
    "Можно ли оплатить картой?",
    "Где вы находитесь?",
]

SAMPLE_DOCS = [
    ("delivery", "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей. "
                 "В регионы — транспортной компанией за 3–7 рабочих дней."),
    ("returns", "Вернуть товар можно в течение 14 дней, если он не был в использовании."),
    ("warranty", "Гарантия на технику — 12 месяцев по кассовому чеку."),
]


def embed(text, prefix):
    return ollama.embeddings(model="nomic-embed-text", prompt=prefix + text)["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def giga(messages):
    token = httpx.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers={"Authorization": f"Basic {AUTH}", "RqUID": str(uuid.uuid4()),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"scope": "GIGACHAT_API_PERS"}, verify=VERIFY, timeout=20,
    ).json()["access_token"]
    r = httpx.post(
        "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "GigaChat", "messages": messages, "temperature": 0.0},
        verify=VERIFY, timeout=60,
    )
    return r.json()["choices"][0]["message"]["content"].strip()


def load_index():
    """Индекс клиента из script-1.py, если есть; иначе — демо-документы."""
    if os.path.exists(INDEX_PATH):
        rows = json.load(open(INDEX_PATH, encoding="utf-8"))
        print(f"📇 База: {INDEX_PATH} ({len(rows)} кусков)\n")
        return [(r["source"], r["text"], r["embedding"]) for r in rows]
    print("📇 Индекса клиента нет — беру демо-документы (сначала запусти script-1.py "
          "для своей папки)\n")
    return [(src, text, embed(text, "search_document: ")) for src, text in SAMPLE_DOCS]


def covered(question, index) -> tuple[bool, float, str]:
    """Отвечает ли база на вопрос: близкий кусок есть И судья подтвердил ответ в нём."""
    qv = embed(question, "search_query: ")
    score, src, text = max(((cosine(qv, emb), src, txt) for src, txt, emb in index),
                           key=lambda x: x[0])
    if score < SCORE_MIN:
        return False, score, src
    verdict = giga([
        {"role": "system", "content": "Есть ли во фрагменте ответ на вопрос? "
                                      "Ответь одним словом: ДА или НЕТ."},
        {"role": "user", "content": f"Фрагмент: {text}\n\nВопрос: {question}"},
    ])
    return "ДА" in verdict.upper(), score, src


if __name__ == "__main__":
    index = load_index()
    print("🔍 Карточка готовности пилота — что бот уже умеет по документам:\n")

    ok, gaps = [], []
    for q in TYPICAL_QUESTIONS:
        is_cov, score, src = covered(q, index)
        if is_cov:
            ok.append(q)
            print(f"  ✅ {q}   → есть в «{src}» (похожесть {score:.2f})")
        else:
            gaps.append(q)
            print(f"  ❌ {q}   → в базе нет (лучшая похожесть {score:.2f})")

    n = len(TYPICAL_QUESTIONS)
    print(f"\n📋 ИТОГ: бот уже закрывает {len(ok)} из {n} типовых вопросов "
          f"({len(ok) / n * 100:.0f}%).")
    if gaps:
        print("   Дослать в базу документы по темам:")
        for q in gaps:
            print(f"     • {q}")
    print("\nЭту карточку показываем клиенту ДО пилота: видно, что получит, без обещаний.")
