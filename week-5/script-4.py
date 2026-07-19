"""
День 32 — сборка sales-kit.md: оффер + кейс + ROI + отзыв + FAQ по возражениям.

Кейс, ROI и отзыв уже готовы (дни 29–31), но лежат в разных местах — и на каждом
новом контакте я собираю ответ заново. Этот шаг склеивает всё в ОДИН документ, из
которого продаётся оффер: открыл на встрече или отправил в личку — не собирая на ходу.

Секции sales-kit:
  1. Оффер одной фразой         5. Пакеты (эскиз; цены — Неделя 6)
  2. Кейс «было/стало» + цифры  6. FAQ по возражениям (дорого / данные / врёт / сами на ChatGPT)
  3. ROI в ₽/год                7. Первое касание — шаблон
  4. Отзыв клиента

Цифры кейса берутся из логов пилота (baseline/metrics/feedback.jsonl рядом; если их
нет — из демо), ROI — из env (как в script-2). Чистый Python, без ключей.

Запуск (из корня проекта):
    python3 week-5/scripts/script-4.py
    CLIENT_NAME="Свет в Дом" HOURS_PER_WEEK=12 RATE_PER_HOUR=700 python3 week-5/scripts/script-4.py
"""

import json
import os

HERE = os.path.dirname(__file__)
OUT_PATH = os.environ.get("SALESKIT_PATH", os.path.join(HERE, "sales-kit.generated.md"))
CLIENT = os.environ.get("CLIENT_NAME", "Свет в Дом")
QPW = int(os.environ.get("QUESTIONS_PER_WEEK", "300"))
HOURS = float(os.environ.get("HOURS_PER_WEEK", "12"))
RATE = float(os.environ.get("RATE_PER_HOUR", "700"))
AUTOMATION = float(os.environ.get("AUTOMATION", "0.7"))
COST = float(os.environ.get("COST", "70000"))
WEEKS_PER_YEAR = 47

DEMO_METRICS = {"before_min": 3.0, "after_sec": 7.0, "hit": 0.7, "helpful": 0.8, "votes": 5}
REVIEW = os.environ.get(
    "REVIEW",
    "Раньше менеджеры искали условия по регламентам по 3–4 минуты. Теперь бот отвечает "
    "за секунды и 70% вопросов закрывает сам — освободили почти по два часа в день.")
REVIEW_BY = os.environ.get("REVIEW_BY", "Анна Петрова, руководитель поддержки")

OBJECTIONS = [
    ("«Дорого»",
     "Внедрение окупается за месяц-полтора: считаем ROI по вашим цифрам до старта. "
     "Дальше бот просто экономит фонд времени сотрудников."),
    ("«Не отдадим свои данные»",
     "Данные не уходят на сторону: генерация — через российский GigaChat/YandexGPT, "
     "поиск (эмбеддинги) работает локально. Возможен полностью on-premise-контур."),
    ("«А вдруг бот начнёт врать клиентам»",
     "Бот отвечает строго по вашим документам и при отсутствии ответа честно говорит "
     "«не знаю». Под каждым ответом — оценка 👍/👎, все промахи видно сразу."),
    ("«Мы сами попробуем на ChatGPT»",
     "ChatGPT не знает ваших регламентов и выдумывает. Ценность — не в модели, а во "
     "встроенном в неё поиске по вашей базе и в доведении до Telegram/сайта/CRM."),
    ("«Сейчас не до этого»",
     "Начнём с бесплатного/пилотного контура на части документов — за неделю увидите "
     "цифры до/после на своём материале и решите."),
]


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def metrics_from_logs():
    base = _read_jsonl(os.path.join(HERE, "baseline.jsonl"))
    metr = [r for r in _read_jsonl(os.path.join(HERE, "metrics.jsonl")) if r.get("event") == "ask"]
    fb = _read_jsonl(os.path.join(HERE, "feedback.jsonl"))
    if not (base and metr):
        return dict(DEMO_METRICS)
    found = [r for r in base if r.get("found")]
    votes = [r for r in fb if "vote" in r]
    return {
        "before_min": (sum(r["seconds"] for r in found) / len(found) / 60) if found else 0,
        "after_sec": sum(r.get("latency_s", 0) for r in metr) / len(metr),
        "hit": sum(1 for r in metr if r.get("hit")) / len(metr),
        "helpful": (sum(r["vote"] for r in votes) / len(votes)) if votes else 0,
        "votes": len(votes),
    }


def money(x):
    return f"{x:,.0f}".replace(",", " ")


def build():
    m = metrics_from_logs()
    speedup = round(m["before_min"] * 60 / m["after_sec"]) if m["after_sec"] else 0
    saved_hours_week = HOURS * AUTOMATION
    saved_year = saved_hours_week * RATE * WEEKS_PER_YEAR
    payback_m = COST / (saved_hours_week * RATE * 52 / 12) if saved_hours_week else 0

    faq = "\n".join(f"**{q}**\n{a}\n" for q, a in OBJECTIONS)
    return f"""# Sales-kit: RAG-бот по базе знаний компании

_Собран автоматически из данных пилота (week-5/script-4.py). Правь под конкретного лида._

## 1. Оффер одной фразой

Ставлю бота, который отвечает сотрудникам и клиентам по вашим регламентам, FAQ,
прайсам и документам — в Telegram или на сайте. Разворачивается под ваши документы
за считанные дни. Не демо в ChatGPT, а встроенное в вашу работу решение.

## 2. Кейс «{CLIENT}»: было → стало

| Показатель | Было (вручную) | Стало (бот) |
|---|---|---|
| Время на ответ | {m['before_min']:.1f} мин | {m['after_sec']:.1f} сек (×{speedup} быстрее) |
| Доля закрытых вопросов | как повезёт | {m['hit']*100:.0f}% |
| Доступность | рабочие часы | 24/7 |
| Оценка сотрудников (👍) | — | {m['helpful']*100:.0f}% из {m['votes']} |

## 3. ROI

При {HOURS:.0f} ч/нед ручного поиска, ставке {money(RATE)} ₽/час и автоматизации
{AUTOMATION*100:.0f}% — экономия ≈ **{money(saved_year)} ₽/год**. Внедрение за
{money(COST)} ₽ окупается за **~{payback_m:.1f} мес**, дальше — чистая экономия.

## 4. Отзыв клиента

> «{REVIEW}»
> — {REVIEW_BY}

## 5. Пакеты (эскиз — цены фиксируем на Неделе 6)

- **Пилот** — бот на части документов, метрики до/после за неделю.
- **Внедрение** — полная база, Telegram + виджет на сайт, обучение команды.
- **Поддержка** (обязательно) — обновление базы, мониторинг оценок, доработки. Подписка ₽/мес.

## 6. FAQ по возражениям

{faq}
## 7. Первое касание — шаблон

Заметил, что у вас {{боль}}. У похожего бизнеса мы свели поиск ответа с {m['before_min']:.0f} минут
к секундам, {m['hit']*100:.0f}% вопросов бот закрывает сам. У вас сейчас как с этим — руками?
"""


if __name__ == "__main__":
    text = build()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print("─" * 56)
    print(f"✅ Sales-kit собран: {OUT_PATH}")
    print("   Это оружие для каждого контакта: оффер, кейс, ROI, отзыв и ответы на возражения в одном месте.")
    print("   Канонический шаблон-образец — week-5/sales-kit.md.")
