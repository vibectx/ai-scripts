"""
День 26 — пробелы базы: на что бот не ответил / получил 👎.

Каждое честное «в документах этого нет» и каждый 👎 — не провал, а сигнал: в базе
знаний пробел. Скрипт проходит по логам работы бота и собирает такие случаи в один
короткий список, отсортированный по частоте: сверху то, что спрашивают чаще всего.

Это готовое ТЗ клиенту: «допишите в регламент вот эти пункты — и бот закроет ещё
часть вопросов». Улучшается не только бот, но и база знаний самого бизнеса.

Источники (что найдёт — то и использует, ключ НЕ нужен):
  • feedback.jsonl — оценки ответов (👎 = пробел), см. script-4.py;
  • metrics.jsonl  — лог ответов бота (event=ask, hit=false = не нашёл), формат ai-digest.

Запуск (из корня проекта):
    python3 week-4/scripts/script-5.py
"""

import json
import os
from collections import Counter

HERE = os.path.dirname(__file__)
FEEDBACK_PATH = os.environ.get("FEEDBACK_PATH", os.path.join(HERE, "feedback.jsonl"))
METRICS_PATH = os.environ.get("METRICS_PATH", os.path.join(HERE, "metrics.jsonl"))


def _read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def collect_gaps() -> Counter:
    """Возвращает Counter{вопрос: сколько раз он оказался пробелом}."""
    gaps: Counter = Counter()
    for r in _read_jsonl(FEEDBACK_PATH):
        if r.get("vote") == 0 and r.get("question"):        # 👎
            gaps[r["question"].strip()] += 1
    for r in _read_jsonl(METRICS_PATH):
        if r.get("event") == "ask" and r.get("hit") is False and r.get("question"):
            gaps[r["question"].strip()] += 1
    return gaps


def _make_sample_feedback() -> None:
    """Если логов нет — кладём демо-фидбек, чтобы показать формат отчёта."""
    demo = [
        {"question": "А вы чините автомобили?", "vote": 0, "reason": "нет ответа в базе"},
        {"question": "Есть ли рассрочка?", "vote": 0, "reason": "не нашёл в документах"},
        {"question": "Есть ли рассрочка?", "vote": 0, "reason": ""},
        {"question": "Работаете ли вы в выходные?", "vote": 0, "reason": ""},
        {"question": "Со скольки бесплатная доставка?", "vote": 1, "reason": ""},
    ]
    with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
        for r in demo:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if not os.path.exists(FEEDBACK_PATH) and not os.path.exists(METRICS_PATH):
        print("📁 Логов работы бота нет — кладу демо-фидбек, чтобы показать формат.\n")
        _make_sample_feedback()

    gaps = collect_gaps()
    print("🕳  Пробелы базы знаний — что дописать, чтобы бот закрывал больше вопросов:\n")
    if not gaps:
        print("  ✅ Пробелов не найдено: бот отвечает по всем вопросам из логов.")
    else:
        for i, (q, n) in enumerate(gaps.most_common(), 1):
            print(f"  {i}. {q}   — спрашивали {n} раз(а)")
        print(f"\n  Итого дыр: {len(gaps)}. Отдай этот список клиенту как ТЗ на доработку")
        print("  регламентов — и часть 👎 превратится в 👍. Отчёт до/после — script-6.py.")
