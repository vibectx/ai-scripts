"""
День 14 — итог недели в одном файле: бот на РЕАЛЬНОМ публичном документе.
Полный конвейер: скачали документ → почистили → нарезали с нахлёстом → посчитали
векторы (с кэшем) → нашли нужный кусок → ответили строго по нему и показали источник.

Это всё приёмы недели 2 вместе: форматы (День 8), нарезка (9), цитата-источник (10),
кэш и стоимость (12). На этом же конвейере записывается демо «загрузил документ —
бот отвечает».

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-2/scripts/script-7.py
    # свой документ (PDF/URL/txt) — через DOC:
    DOC=https://site.ru/oferta GIGACHAT_AUTH_KEY=... python3 week-2/scripts/script-7.py
    # нужен Ollama с nomic-embed-text; нет сертификата Минцифры? GIGACHAT_VERIFY_SSL=0
"""

import hashlib
import json
import math
import os
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-2/scripts/script-7.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"
DOC = os.environ.get("DOC", "https://ru.wikipedia.org/wiki/Гарантийный_срок")
CACHE_PATH = os.path.join(os.path.dirname(__file__), ".embed_cache.json")


def load_text(doc: str) -> str:
    """URL / .pdf / .txt → чистый текст (форматы из Дня 8, в сжатом виде)."""
    if doc.startswith(("http://", "https://")):
        from selectolax.parser import HTMLParser
        html = httpx.get(doc, timeout=30, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"}).text
        tree = HTMLParser(html)
        for t in tree.css("script, style, nav, header, footer"):
            t.decompose()
        raw = (tree.css_first("article") or tree.body).text(separator="\n", strip=True)
    elif doc.lower().endswith(".pdf"):
        from pypdf import PdfReader
        raw = "\n".join(p.extract_text() or "" for p in PdfReader(doc).pages)
    else:
        with open(doc, encoding="utf-8") as f:
            raw = f.read()
    return " ".join(raw.split())


def chunk(text: str, size: int = 240, overlap: int = 60):
    out, start = [], 0
    while start < len(text):
        out.append(text[start:start + size])
        start += size - overlap
    return out


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


def build(doc):
    text = load_text(doc)
    chunks = chunk(text)
    vecs = [embed(c, "search_document: ") for c in chunks]
    json.dump(_cache, open(CACHE_PATH, "w", encoding="utf-8"))   # сохранили кэш векторов
    return chunks, vecs


def answer(question, chunks, vecs):
    qv = embed(question, "search_query: ")
    score, piece = max(((cosine(qv, v), c) for v, c in zip(vecs, chunks)), key=lambda x: x[0])
    reply = giga([
        {"role": "system", "content": "Ответь на вопрос строго по фрагменту источника. "
                                      "Если ответа во фрагменте нет — скажи «не знаю»."},
        {"role": "user", "content": f"Фрагмент: {piece}\n\nВопрос: {question}"},
    ])
    return f"💬 {reply}\n   📄 фрагмент-источник (похожесть {score:.2f}): «…{piece.strip()}…»"


if __name__ == "__main__":
    print(f"📥 Загружаю документ: {DOC}")
    chunks, vecs = build(DOC)
    print(f"✅ Готов отвечать: {len(chunks)} кусков проиндексировано.\n")
    for q in ["Что такое гарантийный срок?", "Сколько стоит доставка?"]:
        print(f"❓ {q}\n{answer(q, chunks, vecs)}\n")
    print("Это и есть демо недели: подменил DOC на документ клиента — и бот отвечает по нему.")
