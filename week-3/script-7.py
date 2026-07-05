"""
День 21 — капстоун недели 3 в одном файле: весь конвейер под клиента.
Папка документов клиента → чтение любых форматов (День 8) → нарезка с нахлёстом
(День 9) → векторы с кэшем (День 12) → индекс → ответ по ВСЕЙ базе со ссылкой на
источник (День 17) → метрика каждого ответа: время и стоимость (День 19).

Подменяешь папку на документы конкретного бизнеса — и через день у него работающий
бот. Это и есть то, что я приношу на бесплатный пилот.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-3/scripts/script-7.py
    # своя папка: DOCS_DIR=путь/к/документам GIGACHAT_AUTH_KEY=... python3 ...
    # нужен Ollama с nomic-embed-text; нет сертификата Минцифры? GIGACHAT_VERIFY_SSL=0
"""

import glob
import hashlib
import json
import math
import os
import time
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-3/scripts/script-7.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"
DOCS_DIR = os.environ.get("DOCS_DIR", os.path.join(os.path.dirname(__file__), "sample_docs"))
CACHE_PATH = os.path.join(os.path.dirname(__file__), ".embed_cache.json")
RUB_PER_1K_TOKENS = 0.20


def read_file(path: str) -> str:
    low = path.lower()
    if low.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    if low.endswith(".docx"):
        import docx
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def chunk(text: str, size: int = 240, overlap: int = 60):
    text = " ".join(text.split())
    out, start = [], 0
    while start < len(text):
        piece = text[start:start + size].strip()
        if len(piece) > 30:
            out.append(piece)
        start += size - overlap
    return out


_cache = json.load(open(CACHE_PATH, encoding="utf-8")) if os.path.exists(CACHE_PATH) else {}


def embed(text, prefix):
    key = hashlib.sha1((prefix + text).encode()).hexdigest()
    if key not in _cache:
        _cache[key] = ollama.embeddings(model="nomic-embed-text", prompt=prefix + text)["embedding"]
    return _cache[key]


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
        json={"model": "GigaChat", "messages": messages, "temperature": 0.1},
        verify=VERIFY, timeout=60,
    ).json()
    text = r["choices"][0]["message"]["content"].strip()
    tokens = r.get("usage", {}).get("total_tokens", len(text) // 3)
    return text, tokens


def _make_sample_docs(docs_dir: str) -> None:
    os.makedirs(docs_dir, exist_ok=True)
    samples = {
        "delivery.txt": "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей. "
                        "В регионы — транспортной компанией за 3–7 рабочих дней.",
        "returns.txt": "Вернуть товар можно в течение 14 дней, если он не был в использовании. "
                       "Деньги возвращаются на карту в течение 10 дней.",
        "warranty.txt": "Гарантия на технику — 12 месяцев по кассовому чеку.",
    }
    for name, text in samples.items():
        with open(os.path.join(docs_dir, name), "w", encoding="utf-8") as f:
            f.write(text)


def build(docs_dir: str):
    """Папка → индекс: [(source, text, embedding)] по всем документам."""
    paths = [p for p in sorted(glob.glob(os.path.join(docs_dir, "**", "*"), recursive=True))
             if os.path.isfile(p) and p.lower().endswith((".pdf", ".docx", ".txt", ".md"))]
    index = []
    for path in paths:
        src = os.path.relpath(path, docs_dir)
        for piece in chunk(read_file(path)):
            index.append((src, piece, embed(piece, "search_document: ")))
    json.dump(_cache, open(CACHE_PATH, "w", encoding="utf-8"))
    return index


def answer(question, index):
    t0 = time.perf_counter()
    qv = embed(question, "search_query: ")
    score, src, text = max(((cosine(qv, emb), s, t) for s, t, emb in index), key=lambda x: x[0])
    reply, tokens = giga([
        {"role": "system", "content": "Ответь на вопрос строго по фрагменту. "
                                      "Если ответа во фрагменте нет — скажи «не знаю»."},
        {"role": "user", "content": f"Фрагмент: {text}\n\nВопрос: {question}"},
    ])
    dt = time.perf_counter() - t0
    cost = tokens / 1000 * RUB_PER_1K_TOKENS
    return (f"💬 {reply}\n   📄 {src} (похожесть {score:.2f}) · ⏱ {dt:.1f} сек · 💰 {cost:.3f} ₽")


if __name__ == "__main__":
    if not os.path.isdir(DOCS_DIR) or not os.listdir(DOCS_DIR):
        _make_sample_docs(DOCS_DIR)

    print(f"📥 Собираю бота из папки клиента: {DOCS_DIR}")
    index = build(DOCS_DIR)
    sources = sorted({s for s, _, _ in index})
    print(f"✅ Готов: {len(index)} кусков из {len(sources)} документов. Отвечаю по всей базе.\n")

    for q in ["Со скольки бесплатная доставка?",
              "За сколько дней можно вернуть товар?",
              "А вы ремонтируете автомобили?"]:
        print(f"❓ {q}\n{answer(q, index)}\n")

    print("Это весь конвейер недели в одном файле. Подменил DOCS_DIR на документы бизнеса —")
    print("и через день у него бот в Telegram или на сайте. Беру 1–2 на бесплатный пилот. 🙌")
