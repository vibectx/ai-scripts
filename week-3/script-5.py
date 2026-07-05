"""
День 19 — бот считает свою пользу в цифрах. На каждый ответ пишем в лог: за сколько
секунд ответил, во сколько обошёлся и нашёл ли ответ в базе. Из лога собирается
сводка до/после — заготовка кейса вместо «клиенту понравилось».

«Было» (менеджер ищет ответ в регламенте руками) задаётся константой BEFORE_SECONDS.
«Стало» — реально измеряется на прогоне. Стоимость ответа считаем по прайсу GigaChat
(≈ по токенам ответа), поиск по документам бесплатен (векторы локальные, День 12).

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-3/scripts/script-5.py
    # нужен Ollama с nomic-embed-text; нет сертификата Минцифры? GIGACHAT_VERIFY_SSL=0
"""

import json
import math
import os
import time
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-3/scripts/script-5.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"

LOG_PATH = os.path.join(os.path.dirname(__file__), "metrics.jsonl")
BEFORE_SECONDS = 240          # «было»: менеджер ищет ответ в регламенте ~4 минуты
RUB_PER_1K_TOKENS = 0.20      # ориентир прайса GigaChat: ~0.2 ₽ за 1000 токенов ответа

DOCS = [
    "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей.",
    "Вернуть товар можно в течение 14 дней, если он не был в использовании.",
    "Гарантия на технику — 12 месяцев по кассовому чеку.",
]


def embed(text, prefix):
    return ollama.embeddings(model="nomic-embed-text", prompt=prefix + text)["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


VECS = [embed(d, "search_document: ") for d in DOCS]


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
    tokens = r.get("usage", {}).get("total_tokens", len(text) // 3)   # нет usage — прикинем
    return text, tokens


def answer_and_log(question: str) -> dict:
    """Отвечаем и пишем метрику ответа в JSONL. Возвращаем саму метрику."""
    t0 = time.perf_counter()
    qv = embed(question, "search_query: ")
    score, doc = max(((cosine(qv, v), d) for v, d in zip(VECS, DOCS)), key=lambda x: x[0])
    reply, tokens = giga([
        {"role": "system", "content": "Отвечай кратко и только по документу. Нет ответа — «не знаю»."},
        {"role": "user", "content": f"Документ: {doc}\n\nВопрос: {question}"},
    ])
    metric = {
        "question": question,
        "latency_s": round(time.perf_counter() - t0, 2),
        "cost_rub": round(tokens / 1000 * RUB_PER_1K_TOKENS, 4),
        "hit": score >= 0.5 and "не знаю" not in reply.lower(),   # нашёл ли ответ в базе
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(metric, ensure_ascii=False) + "\n")
    return metric


def summary() -> None:
    """Сводка до/после по накопленному логу — то, что несём владельцу."""
    rows = [json.loads(ln) for ln in open(LOG_PATH, encoding="utf-8")]
    n = len(rows)
    hits = sum(r["hit"] for r in rows)
    avg_lat = sum(r["latency_s"] for r in rows) / n
    total_cost = sum(r["cost_rub"] for r in rows)
    saved_h = n * (BEFORE_SECONDS - avg_lat) / 3600

    print("\n📊 Сводка (заготовка кейса):")
    print(f"   Вопросов обработано:      {n}")
    print(f"   Найден ответ в базе:      {hits}/{n} ({hits / n * 100:.0f}%)")
    print(f"   Было (ручной поиск):      {BEFORE_SECONDS} сек/вопрос")
    print(f"   Стало (бот):              {avg_lat:.1f} сек/вопрос")
    print(f"   Сэкономлено времени:      ~{saved_h:.2f} ч на этих вопросах")
    print(f"   Стоимость всех ответов:   {total_cost:.2f} ₽ (поиск по базе — бесплатно)")


if __name__ == "__main__":
    open(LOG_PATH, "w").close()          # чистим лог перед демо-прогоном
    for q in ["Сколько стоит доставка по Москве?",
              "За сколько дней можно вернуть товар?",
              "Какой срок гарантии?",
              "А вы чините автомобили?"]:      # последний — ответа в базе нет
        m = answer_and_log(q)
        mark = "✅" if m["hit"] else "➖"
        print(f"{mark} {q}  —  {m['latency_s']} сек, {m['cost_rub']} ₽")
    summary()
    print("\nЭту сводку и несём владельцу вместо «удобно же». Цифра продаёт пилот.")
