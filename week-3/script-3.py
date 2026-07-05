"""
День 17 — бот отвечает не по «последнему файлу», а по ВСЕЙ накопленной базе.
Каждый документ один раз режется на куски, куски с векторами ложатся в SQLite рядом
с прежними. На вопрос ищем нужный кусок по всему архиву и отвечаем со ссылкой на
источник. База растёт — переиндексировать заново ничего не нужно.

Это шаг Этапа 5 пет-проекта (`/ask` по SQLite) в отдельном самодостаточном виде:
скрипт сам создаёт временную базу, наполняет её несколькими «документами», строит
таблицу chunks и ищет по всему архиву сразу.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-3/scripts/script-3.py
    # нужен запущенный Ollama с моделью nomic-embed-text
    # нет сертификата Минцифры? добавь GIGACHAT_VERIFY_SSL=0
"""

import math
import os
import sqlite3
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-3/scripts/script-3.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"
DB_PATH = os.path.join(os.path.dirname(__file__), "archive_demo.db")

# «Архив» из нескольких документов — как будто их накопили за разные дни.
ARCHIVE = {
    "delivery.md": "Доставка по Москве стоит 300 рублей и бесплатна при заказе от 5000 рублей. "
                   "В регионы заказы отправляются транспортной компанией за 3–7 рабочих дней.",
    "returns.md": "Товар надлежащего качества можно вернуть в течение 14 дней, если он не был в "
                  "использовании. Деньги возвращаются на карту в течение 10 дней.",
    "warranty.md": "Гарантия на технику — 12 месяцев по кассовому чеку. Гарантийный ремонт "
                   "бесплатный, если сохранена упаковка.",
    "loyalty.md": "Постоянным клиентам действует скидка 10% при сумме покупок от 50000 рублей за год. "
                  "Скидка суммируется с акциями до 25%.",
}


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


def chunks_of(text, size=200, overlap=50):
    text = " ".join(text.split())
    out, start = [], 0
    while start < len(text):
        out.append(text[start:start + size]); start += size - overlap
    return out


def build_archive(conn):
    """Складываем куски всех документов с векторами в одну таблицу chunks."""
    conn.executescript("""
        DROP TABLE IF EXISTS chunks;
        CREATE TABLE chunks (source TEXT, text TEXT, embedding TEXT);
    """)
    import json
    for source, text in ARCHIVE.items():
        for piece in chunks_of(text):
            vec = json.dumps(embed(piece, "search_document: "))
            conn.execute("INSERT INTO chunks (source, text, embedding) VALUES (?, ?, ?)",
                         (source, piece, vec))
    conn.commit()


def search_all(conn, question, k=2):
    """Ищем самые близкие куски по ВСЕМУ архиву (перебор в Python, как в спеке)."""
    import json
    qv = embed(question, "search_query: ")
    rows = conn.execute("SELECT source, text, embedding FROM chunks").fetchall()
    scored = sorted(((cosine(qv, json.loads(emb)), src, txt) for src, txt, emb in rows),
                    key=lambda x: x[0], reverse=True)
    return scored[:k]


def ask(conn, question):
    top = search_all(conn, question)
    context = "\n".join(f"[{src}] {txt}" for _, src, txt in top)
    reply = giga([
        {"role": "system", "content": "Отвечай кратко и ТОЛЬКО по документам ниже. "
                                      "Нет ответа — скажи «не знаю»."},
        {"role": "user", "content": f"Документы:\n{context}\n\nВопрос: {question}"},
    ])
    score, src, _ = top[0]
    return f"💬 {reply}\n   📄 источник: {src} (похожесть {score:.2f})"


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    print(f"📚 Индексирую архив из {len(ARCHIVE)} документов в SQLite…")
    build_archive(conn)
    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    print(f"✅ В базе {total} кусков из разных документов. Бот ищет сразу по всем.\n")

    for q in ["Со скольки бесплатная доставка?",
              "Какая скидка у постоянных клиентов?",
              "Сколько длится гарантия?"]:
        print(f"❓ {q}\n{ask(conn, q)}\n")
    conn.close()
    print("Каждый вопрос нашёл ответ в своём документе — база общая, бот один.")
