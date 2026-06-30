"""
День 9 — почему бот «отвечает мимо». Дело не в модели, а в НАРЕЗКЕ документов.
Большой текст режем на куски с нахлёстом — и нужный факт находится точно.

Скрипт сравнивает два подхода на одном длинном документе:
  1) грубо — весь документ одним куском (модель тонет в лишнем);
  2) умно — небольшие куски с перекрытием (overlap), чтобы факт не разорвался на границе.
На один и тот же вопрос видно, как второй подход поднимает наверх правильный фрагмент.

КЛЮЧ НЕ НУЖЕН. Нужен только запущенный Ollama с моделью nomic-embed-text.
Запуск (из корня проекта):
    python3 week-2/scripts/script-2.py
    # если модели нет: ollama pull nomic-embed-text
"""

import math

import ollama

DOC = """Компания доставляет заказы по всей России. По Москве курьер привозит заказ
в день оформления, если он сделан до 14:00. Стоимость доставки по Москве — 300 рублей,
а при сумме заказа от 5000 рублей доставка бесплатная. В регионы отправка идёт
транспортной компанией, срок — от 3 до 7 рабочих дней, стоимость рассчитывается по тарифу
перевозчика. Самовывоз со склада на улице Складочной работает с 9:00 до 18:00 без выходных.
Вернуть товар надлежащего качества можно в течение 14 дней с момента покупки, если он не был
в употреблении и сохранён товарный вид. Возврат денег приходит на карту в течение 10 дней.
Гарантия на технику — 12 месяцев и оформляется по кассовому чеку."""


def embed(text: str, prefix: str):
    return ollama.embeddings(model="nomic-embed-text", prompt=prefix + text)["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def split_overlap(text: str, size: int = 220, overlap: int = 60):
    """Режем по символам кусками size с нахлёстом overlap — факт не теряется на стыке."""
    text = " ".join(text.split())            # убираем переносы строк
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def best(query: str, chunks: list[str]):
    qv = embed(query, "search_query: ")
    scored = sorted(((cosine(qv, embed(c, "search_document: ")), c) for c in chunks),
                    key=lambda x: x[0], reverse=True)
    return scored[0]


if __name__ == "__main__":
    question = "Со скольки работает самовывоз?"
    print(f"❓ Вопрос: {question}\n")

    score_whole, _ = best(question, [DOC])
    print(f"1) Весь документ одним куском — похожесть {score_whole:.3f}")
    print("   (модели приходится искать факт внутри простыни текста)\n")

    chunks = split_overlap(DOC)
    score_chunk, top = best(question, chunks)
    print(f"2) {len(chunks)} куска с нахлёстом — лучший кусок, похожесть {score_chunk:.3f}:")
    print(f"   «…{top.strip()}…»\n")

    print("Тот же текст, та же модель — разница только в нарезке. "
          "Правильный chunking и есть половина успеха бота по документам.")
