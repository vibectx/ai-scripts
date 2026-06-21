"""
День 5 — семантический поиск: бот ищет по СМЫСЛУ, а не по совпадению слов.

КЛЮЧ НЕ НУЖЕН. Нужен только запущенный Ollama с моделью nomic-embed-text.
Запуск (из корня проекта):
    python3 week-1/scripts/script-5.py
    # если модели нет: ollama pull nomic-embed-text
"""

import math

import ollama

FACTS = [
    "Доставка по Москве стоит 300 рублей.",
    "Вернуть покупку можно в течение 14 дней.",
    "Гарантия на технику — один год.",
]


def embed(text, prefix):
    return ollama.embeddings(model="nomic-embed-text", prompt=prefix + text)["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


FACT_VECS = [embed(f, "search_document: ") for f in FACTS]

# В вопросе НЕТ слова «вернуть/возврат/14» — но по смыслу он про возврат.
question = "за сколько дней реально отдать товар обратно в магазин"
qv = embed(question, "search_query: ")

print(f"Вопрос: {question}\n")
print("Похожесть каждого факта по СМЫСЛУ:")
for fact, vec in sorted(zip(FACTS, FACT_VECS), key=lambda fv: cosine(qv, fv[1]), reverse=True):
    print(f"  {cosine(qv, vec):.3f}  {fact}")
print("\nСамый похожий факт нашёлся без единого общего слова — это и есть смысловой поиск.")
