"""
День 25 — оценка ответов прямо в боте: 👍/👎 + причина.

Молчаливый бот, который иногда врёт, хуже никакого. Поэтому под каждым ответом —
две кнопки: помог / не помог. Оценки копятся вместе с вопросом, и из них сразу видно
долю полезных ответов и список всего, что получило 👎 (это будущие «пробелы», День 26).

Скрипт демонстрирует петлю обратной связи целиком: собирает мини-индекс из папки,
отвечает на вопросы (GigaChat + локальные эмбеддинги), сохраняет оценку каждого
ответа в feedback.jsonl и печатает сводку. Оценку берём:
  • интерактивно — спрашиваем у тебя (Enter=👍, 'x'=👎, можно причину);
  • неинтерактивно — авто-оценка: ответ «не знаю» → 👎, иначе → 👍 (демо-режим).

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=... python3 week-4/scripts/script-4.py
    # своя папка: DOCS_DIR=... GIGACHAT_AUTH_KEY=... python3 ...
    # нужен Ollama с nomic-embed-text; нет сертификата Минцифры? GIGACHAT_VERIFY_SSL=0
"""

import glob
import json
import math
import os
import sys
import time
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-4/scripts/script-4.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"
DOCS_DIR = os.environ.get("DOCS_DIR", os.path.join(os.path.dirname(__file__), "sample_docs"))
FEEDBACK_PATH = os.environ.get("FEEDBACK_PATH", os.path.join(os.path.dirname(__file__), "feedback.jsonl"))


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
        json={"model": "GigaChat", "messages": messages, "temperature": 0.1},
        verify=VERIFY, timeout=60,
    ).json()
    return r["choices"][0]["message"]["content"].strip()


def _make_sample_docs(docs_dir: str) -> None:
    os.makedirs(docs_dir, exist_ok=True)
    samples = {
        "delivery.txt": "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей.",
        "returns.txt": "Вернуть товар можно в течение 14 дней, если он не был в использовании.",
        "warranty.txt": "Гарантия на технику — 12 месяцев по кассовому чеку.",
    }
    for name, text in samples.items():
        with open(os.path.join(docs_dir, name), "w", encoding="utf-8") as f:
            f.write(text)


def build(docs_dir: str):
    paths = [p for p in sorted(glob.glob(os.path.join(docs_dir, "**", "*"), recursive=True))
             if os.path.isfile(p) and p.lower().endswith((".pdf", ".docx", ".txt", ".md"))]
    index = []
    for path in paths:
        src = os.path.relpath(path, docs_dir)
        for piece in chunk(read_file(path)):
            index.append((src, piece, embed(piece, "search_document: ")))
    return index


def answer(question, index):
    qv = embed(question, "search_query: ")
    score, src, text = max(((cosine(qv, e), s, t) for s, t, e in index), key=lambda x: x[0])
    reply = giga([
        {"role": "system", "content": "Ответь строго по фрагменту. Нет ответа во фрагменте — "
                                      "скажи «не знаю»."},
        {"role": "user", "content": f"Фрагмент: {text}\n\nВопрос: {question}"},
    ])
    return reply, src, score


def rate(reply: str, interactive: bool) -> tuple[int, str]:
    """Оценка ответа. Возвращает (1=👍 / 0=👎, причина)."""
    if interactive:
        raw = input("   Оцени: Enter = 👍 помог, 'x' = 👎 не помог (можно 'x причина'): ").strip()
        if raw.lower().startswith("x"):
            return 0, raw[1:].strip()
        return 1, ""
    # авто-режим: «не знаю» считаем неудачным ответом
    good = "не знаю" not in reply.lower()
    return (1, "") if good else (0, "нет ответа в базе")


def save(row: dict) -> None:
    with open(FEEDBACK_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if not os.path.isdir(DOCS_DIR) or not os.listdir(DOCS_DIR):
        _make_sample_docs(DOCS_DIR)

    print(f"📥 Собираю мини-бота из папки: {DOCS_DIR}")
    index = build(DOCS_DIR)
    print(f"✅ Готов: {len(index)} кусков. Отвечаю и собираю оценки.\n")

    interactive = sys.stdin.isatty()
    questions = ["Со скольки бесплатная доставка?",
                 "За сколько дней можно вернуть товар?",
                 "А вы чините автомобили?"]

    for q in questions:
        reply, src, score = answer(q, index)
        print(f"❓ {q}\n💬 {reply}\n   📄 {src} (похожесть {score:.2f})")
        vote, reason = rate(reply, interactive)
        save({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "question": q,
              "answer": reply, "source": src, "vote": vote, "reason": reason})
        print(f"   {'👍' if vote else '👎'} записал оценку" + (f" · {reason}" if reason else "") + "\n")

    rows = [json.loads(ln) for ln in open(FEEDBACK_PATH, encoding="utf-8") if ln.strip()]
    up = sum(r["vote"] for r in rows)
    print("─" * 52)
    print(f"📊 Оценок в базе: {len(rows)} · 👍 {up} · 👎 {len(rows)-up} "
          f"· полезных {up/len(rows)*100:.0f}%")
    print(f"   Лог оценок: {FEEDBACK_PATH}. Все 👎 → в «пробелы базы» (script-5.py).")
