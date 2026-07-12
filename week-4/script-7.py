"""
День 28 — капстоун недели 4: весь пилот в одном файле, от онбординга до отчёта.

Собирает воедино всю неделю:
  1. лёгкий self-check окружения (День 22);
  2. папка документов клиента → чистка от дублей → индекс (День 23);
  3. ответы по базе с метриками времени/стоимости (недели 3–4) и авто-оценкой (День 25);
  4. список пробелов базы (День 26);
  5. одностраничный отчёт до/после (День 27), где «было» — базлайн ручного поиска (День 24).

Подменяешь DOCS_DIR на документы конкретного бизнеса — и на выходе получаешь бота +
готовый кейс с цифрами. Это и есть то, что закрывает чек-поинт Фазы 1: рабочее
внедрение + отзыв + демо.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-4/scripts/script-7.py
    # своя папка: DOCS_DIR=... GIGACHAT_AUTH_KEY=... python3 ...
    # нужен Ollama с nomic-embed-text; нет сертификата Минцифры? GIGACHAT_VERIFY_SSL=0
"""

import glob
import hashlib
import math
import os
import time
import uuid
from collections import Counter

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-4/scripts/script-7.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"
DOCS_DIR = os.environ.get("DOCS_DIR", os.path.join(os.path.dirname(__file__), "sample_docs"))
RUB_PER_1K_TOKENS = 0.20
QPW = int(os.environ.get("QUESTIONS_PER_WEEK", "300"))
BASELINE_MIN = 2.5          # средний ручной поиск «как было», мин (замер Дня 24)


# ── движок (недели 1–3) ──────────────────────────────────────────────────────
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
    text = r["choices"][0]["message"]["content"].strip()
    tokens = r.get("usage", {}).get("total_tokens", len(text) // 3)
    return text, tokens


# ── шаг 2: чистка + индекс (День 23) ─────────────────────────────────────────
def build_clean(docs_dir: str):
    paths = [p for p in sorted(glob.glob(os.path.join(docs_dir, "**", "*"), recursive=True))
             if os.path.isfile(p) and p.lower().endswith((".pdf", ".docx", ".txt", ".md"))]
    seen, index, total, dupes = set(), [], 0, 0
    for path in paths:
        src = os.path.relpath(path, docs_dir)
        for piece in chunk(read_file(path)):
            total += 1
            fp = hashlib.sha1(" ".join(piece.lower().split()).encode()).hexdigest()
            if fp in seen:
                dupes += 1
                continue
            seen.add(fp)
            index.append((src, piece, embed(piece, "search_document: ")))
    return index, {"files": len(paths), "total": total, "dupes": dupes, "indexed": len(index)}


def answer(question, index):
    t0 = time.perf_counter()
    qv = embed(question, "search_query: ")
    score, src, text = max(((cosine(qv, e), s, t) for s, t, e in index), key=lambda x: x[0])
    reply, tokens = giga([
        {"role": "system", "content": "Ответь строго по фрагменту. Нет ответа — скажи «не знаю»."},
        {"role": "user", "content": f"Фрагмент: {text}\n\nВопрос: {question}"},
    ])
    dt = time.perf_counter() - t0
    hit = "не знаю" not in reply.lower()
    return {"q": question, "reply": reply, "src": src, "score": score, "dt": dt,
            "cost": tokens / 1000 * RUB_PER_1K_TOKENS, "hit": hit}


def _make_messy_docs(docs_dir: str) -> None:
    os.makedirs(docs_dir, exist_ok=True)
    delivery = "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей."
    samples = {
        "доставка_final.txt": delivery,
        "доставка_final_2.txt": delivery,                    # дубль
        "возвраты.txt": "Вернуть товар можно в течение 14 дней, если он не был в использовании.",
        "гарантия.txt": "Гарантия на технику — 12 месяцев по кассовому чеку.",
    }
    for name, text in samples.items():
        with open(os.path.join(docs_dir, name), "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    # Шаг 1 — лёгкий self-check (День 22)
    print("1) Онбординг: проверяю окружение…")
    print(f"   ✅ ключ GigaChat задан · ✅ Ollama-клиент импортирован · "
          f"{'✅' if VERIFY else '⚠️ '} SSL {'вкл' if VERIFY else 'выкл (локалка)'}")

    if not os.path.isdir(DOCS_DIR) or not os.listdir(DOCS_DIR):
        _make_messy_docs(DOCS_DIR)

    # Шаг 2 — чистка + индекс (День 23)
    print(f"\n2) Чищу и индексирую документы клиента: {DOCS_DIR}")
    index, st = build_clean(DOCS_DIR)
    print(f"   ✅ файлов {st['files']} · дублей выкинуто {st['dupes']} · в индексе {st['indexed']} кусков")

    # Шаг 3 — ответы + метрики + авто-оценка (Дни 25)
    print("\n3) Отвечаю по базе, собираю метрики и оценки:")
    questions = ["Со скольки бесплатная доставка?",
                 "За сколько дней вернуть товар?",
                 "Какая гарантия на технику?",
                 "А вы чините автомобили?",
                 "Есть ли рассрочка?"]
    runs = []
    for q in questions:
        r = answer(q, index)
        runs.append(r)
        print(f"   ❓ {q}\n      💬 {r['reply']}  ({'👍' if r['hit'] else '👎'} · "
              f"⏱ {r['dt']:.1f}s · 💰 {r['cost']:.3f}₽)")

    # Шаг 4 — пробелы базы (День 26)
    gaps = Counter(r["q"] for r in runs if not r["hit"])
    print("\n4) Пробелы базы (на что бот не ответил — дописать в регламенты):")
    if gaps:
        for i, (q, n) in enumerate(gaps.most_common(), 1):
            print(f"   {i}. {q}")
    else:
        print("   ✅ пробелов нет")

    # Шаг 5 — отчёт до/после (Дни 24, 27)
    hit_rate = sum(r["hit"] for r in runs) / len(runs)
    after_avg = sum(r["dt"] for r in runs) / len(runs)
    before_sec = BASELINE_MIN * 60
    saved_h = max(before_sec - after_avg, 0) * QPW / 3600
    print("\n5) Отчёт до/после (кейс для руководства):")
    print(f"   Было (вручную):  {BASELINE_MIN:.1f} мин на вопрос")
    print(f"   Стало (бот):     {after_avg:.1f} сек на вопрос, закрыто {hit_rate*100:.0f}% вопросов")
    print(f"   Экономия:        ~{saved_h:.1f} ч/неделю при {QPW} вопросах")
    print(f"   Осталось дыр:    {len(gaps)} (ТЗ на доработку базы)")

    print("\n" + "─" * 56)
    print("✅ Пилот собран end-to-end: онбординг → чистка → бот → оценки → пробелы → отчёт.")
    print("   Подменил DOCS_DIR на документы бизнеса — получил бота и кейс с цифрами.")
    print("   Чек-поинт Фазы 1 закрыт. Дальше — платные пилоты. 🙌")
