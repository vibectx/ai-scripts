"""
День 12 — «а это не разорит на счетах за ИИ?». Считаем стоимость и КЭШИРУЕМ
эмбеддинги: один раз посчитали векторы документов — и больше не пересчитываем.
Второй запуск бота становится мгновенным и бесплатным по эмбеддингам.

Скрипт эмбеддит набор фактов с кэшем на диске (JSON) и замеряет время первого
и повторного запуска. КЛЮЧ НЕ НУЖЕН — нужен только Ollama с nomic-embed-text.

Запуск (из корня проекта):
    python3 week-2/scripts/script-5.py        # первый раз — считает и кэширует
    python3 week-2/scripts/script-5.py        # второй раз — берёт из кэша, мгновенно
    # сбросить кэш: rm week-2/scripts/.embed_cache.json
"""

import hashlib
import json
import os
import time

import ollama

CACHE_PATH = os.path.join(os.path.dirname(__file__), ".embed_cache.json")

FACTS = [
    "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей.",
    "Вернуть товар можно в течение 14 дней, если он не был в использовании.",
    "Гарантия на технику — 12 месяцев, оформляется по кассовому чеку.",
    "Самовывоз со склада работает с 9:00 до 18:00 без выходных.",
]


def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)


_cache = _load_cache()


def embed_cached(text: str):
    """Вектор по тексту: если уже считали (по хешу) — берём с диска, иначе считаем."""
    key = hashlib.sha1(text.encode()).hexdigest()
    if key in _cache:
        return _cache[key], True                      # cache hit
    vec = ollama.embeddings(model="nomic-embed-text", prompt="search_document: " + text)["embedding"]
    _cache[key] = vec
    return vec, False                                 # cache miss


if __name__ == "__main__":
    start = time.time()
    hits = 0
    for fact in FACTS:
        _, cached = embed_cached(fact)
        hits += cached
    _save_cache(_cache)
    elapsed = time.time() - start

    print(f"Документов: {len(FACTS)} | из кэша: {hits} | посчитано заново: {len(FACTS) - hits}")
    print(f"Время: {elapsed:.3f} c")
    if hits == len(FACTS):
        print("\n✅ Всё взято из кэша — повторный запуск почти мгновенный и бесплатный.")
    else:
        print("\nℹ️  Векторы посчитаны и сохранены. Запусти скрипт ещё раз — будет из кэша.")

    # Прикидка стоимости генерации ответов (эмбеддинги локальные = бесплатны).
    # GigaChat ~200 руб за 1 млн токенов; типовой ответ бота ~700 токенов.
    rub_per_answer = 700 / 1_000_000 * 200
    print(f"\nСтоимость одного ответа GigaChat ≈ {rub_per_answer:.3f} ₽ "
          f"→ 1000 ответов в день ≈ {rub_per_answer * 1000:.0f} ₽.")
    print("Эмбеддинги считаются локально (Ollama) и в счёт не идут — отсюда дешёвая эксплуатация.")
