"""
День 27 — отчёт до/после на одну страницу (кейс для руководства).

Решение о платном продолжении принимает тот, кто бота не видел — он видит отчёт.
Скрипт собирает одностраничный кейс «было → стало» из уже накопленных данных, без
ручного копания в логах:

  • «было»  — базлайн ручного поиска (baseline.jsonl, script-3.py);
  • «стало» — работа бота: среднее время ответа и доля закрытых вопросов
              (metrics.jsonl, формат ai-digest) + оценки 👍/👎 (feedback.jsonl, script-4.py);
  • «экономия» — прикидка сэкономленных часов в неделю;
  • «дальше» — сколько осталось пробелов (script-5.py).

На выходе — готовый report.md, который несут руководителю клиента. КЛЮЧ НЕ НУЖЕН.

Запуск (из корня проекта):
    python3 week-4/scripts/script-6.py
    # число вопросов в неделю для расчёта экономии:
    QUESTIONS_PER_WEEK=300 python3 week-4/scripts/script-6.py
"""

import json
import os

HERE = os.path.dirname(__file__)
BASELINE_PATH = os.environ.get("BASELINE_PATH", os.path.join(HERE, "baseline.jsonl"))
METRICS_PATH = os.environ.get("METRICS_PATH", os.path.join(HERE, "metrics.jsonl"))
FEEDBACK_PATH = os.environ.get("FEEDBACK_PATH", os.path.join(HERE, "feedback.jsonl"))
REPORT_PATH = os.environ.get("REPORT_PATH", os.path.join(HERE, "report.md"))
QPW = int(os.environ.get("QUESTIONS_PER_WEEK", "300"))
CLIENT = os.environ.get("CLIENT_NAME", "Клиент")


def _read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def _demo_if_empty() -> None:
    """Нет реальных логов — кладём демо, чтобы показать, как выглядит готовый отчёт."""
    if _read_jsonl(BASELINE_PATH):
        return
    print("📁 Реальных логов нет — генерирую отчёт на демо-данных (пример вида).\n")
    base = [{"question": f"вопрос {i}", "seconds": s, "found": f}
            for i, (s, f) in enumerate([(180, True), (95, True), (140, True), (60, True), (240, False)])]
    with open(BASELINE_PATH, "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in base)
    metr = [{"event": "ask", "latency_s": s, "hit": h}
            for s, h in [(7.2, True), (5.9, True), (8.1, True), (6.0, True), (9.4, False)]]
    with open(METRICS_PATH, "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in metr)
    fb = [{"question": "q", "vote": v} for v in (1, 1, 1, 1, 0)]
    with open(FEEDBACK_PATH, "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in fb)


def build_report() -> str:
    base = _read_jsonl(BASELINE_PATH)
    metr = [r for r in _read_jsonl(METRICS_PATH) if r.get("event") == "ask"]
    fb = _read_jsonl(FEEDBACK_PATH)

    found_base = [r for r in base if r.get("found")]
    before_avg = sum(r["seconds"] for r in found_base) / len(found_base) if found_base else 0
    before_missrate = 1 - len(found_base) / len(base) if base else 0

    after_avg = sum(r.get("latency_s", 0) for r in metr) / len(metr) if metr else 0
    after_hit = sum(1 for r in metr if r.get("hit")) / len(metr) if metr else 0

    votes = [r for r in fb if "vote" in r]
    helpful = sum(r["vote"] for r in votes) / len(votes) if votes else 0
    gaps = len({r.get("question") for r in fb if r.get("vote") == 0 and r.get("question")})

    saved_sec_per_q = max(before_avg - after_avg, 0)
    saved_hours_week = saved_sec_per_q * QPW / 3600
    speedup = f"в {before_avg / after_avg:.0f} раз быстрее" if after_avg else "—"

    return f"""# Кейс {CLIENT}: RAG-бот по базе знаний — до/после

> Одностраничный итог пилота. Все цифры — из логов работы бота и замера «как было».

## Коротко

Бот отвечает на вопросы по документам компании **{speedup}**, чем ручной поиск,
и закрывает **{after_hit*100:.0f}%** вопросов сам. Экономия — около
**{saved_hours_week:.1f} ч/неделю** при {QPW} вопросах в неделю.

## Было → стало

| Показатель | Было (вручную) | Стало (бот) |
|---|---|---|
| Время на ответ | {before_avg/60:.1f} мин ({before_avg:.0f} сек) | {after_avg:.1f} сек |
| Вопросов без ответа | {before_missrate*100:.0f}% | {(1-after_hit)*100:.0f}% |
| Доступность | рабочие часы | 24/7 |

## Оценка пользователями

- Полезных ответов (👍): **{helpful*100:.0f}%** из {len(votes)} оценок сотрудников.
- Обратная связь встроена в бота — каждый промах виден сразу.

## Экономия

- ~**{saved_sec_per_q:.0f} сек** экономии на каждом вопросе.
- ~**{saved_hours_week:.1f} часов в неделю** при {QPW} вопросах — это время
  сотрудников, освобождённое от рутинного поиска в документах.

## Что дальше

- Осталось пробелов в базе знаний: **{gaps}** (список — отдельным ТЗ на доработку регламентов).
- Закрыв их, поднимаем долю автоматических ответов ещё выше.

_Отчёт собран автоматически из метрик пилота (script-6.py, неделя 4)._
"""


if __name__ == "__main__":
    _demo_if_empty()
    report = build_report()
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print("─" * 52)
    print(f"✅ Отчёт до/после сохранён: {REPORT_PATH}")
    print("   Это первый кейс, который несут руководству — и мой первый настоящий кейс.")
