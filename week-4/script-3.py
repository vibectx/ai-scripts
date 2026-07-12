"""
День 24 — замер «как есть» (базлайн): сколько времени уходит на ручной поиск ответа.

Прежде чем показывать бота, снимаем цифру «до». Берём реальные частые вопросы и
засекаем, сколько сотрудник ищет ответ вручную (по папкам, регламентам, у коллеги).
Это левая колонка будущего отчёта «до/после» (см. script-6.py). Задним числом её не
восстановить — поэтому меряем ДО внедрения.

Скрипт работает в двух режимах:
  • интерактивно (есть терминал): показывает вопрос, ждёт Enter на старте и по факту
    найденного ответа, засекает секунды;
  • неинтерактивно (запуск в CI/без ввода): проигрывает демо-замер, чтобы показать
    формат результата.

Результат пишется в baseline.jsonl и подсчитывается среднее. КЛЮЧ НЕ НУЖЕН.

Запуск (из корня проекта):
    python3 week-4/scripts/script-3.py
    # свои вопросы (по одному в строке):
    QUESTIONS_FILE=вопросы.txt python3 week-4/scripts/script-3.py
"""

import json
import os
import sys
import time

BASELINE_PATH = os.environ.get(
    "BASELINE_PATH", os.path.join(os.path.dirname(__file__), "baseline.jsonl"))

DEFAULT_QUESTIONS = [
    "Со скольки рублей бесплатная доставка?",
    "За сколько дней можно вернуть товар?",
    "Какая гарантия на технику?",
    "Сколько стоит тариф «Про»?",
    "Как оформить возврат денег на карту?",
]


def load_questions() -> list[str]:
    path = os.environ.get("QUESTIONS_FILE")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            qs = [ln.strip() for ln in f if ln.strip()]
        if qs:
            return qs
    return DEFAULT_QUESTIONS


def measure_interactive(questions: list[str]) -> list[dict]:
    rows = []
    print("⏱  Замер «как есть». На каждый вопрос: Enter — старт поиска, "
          "Enter — когда нашёл ответ. Не нашёл — введи 'x'.\n")
    for i, q in enumerate(questions, 1):
        input(f"[{i}/{len(questions)}] {q}\n   Enter — начинаю искать…")
        t0 = time.perf_counter()
        marker = input("   …ищу. Enter — нашёл ответ (или 'x' — не нашёл): ")
        dt = round(time.perf_counter() - t0, 1)
        found = marker.strip().lower() != "x"
        rows.append({"question": q, "seconds": dt, "found": found})
        print(f"   → {dt} сек, {'нашёл' if found else 'НЕ нашёл'}\n")
    return rows


def measure_demo(questions: list[str]) -> list[dict]:
    """Неинтерактивный режим: правдоподобный демо-замер (без реального секундомера)."""
    demo_seconds = [180, 95, 140, 60, 240]
    demo_found = [True, True, True, True, False]
    rows = []
    print("🎬 Нет терминала для ввода — показываю демо-замер (пример результата):\n")
    for i, q in enumerate(questions):
        sec = demo_seconds[i % len(demo_seconds)]
        found = demo_found[i % len(demo_found)]
        rows.append({"question": q, "seconds": sec, "found": found})
        print(f"  [{i+1}] {q}\n      → {sec} сек, {'нашёл' if found else 'НЕ нашёл'}")
    return rows


def summarize(rows: list[dict]) -> None:
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n = len(rows)
    found = [r for r in rows if r["found"]]
    avg = sum(r["seconds"] for r in found) / len(found) if found else 0
    not_found = n - len(found)
    print("\n" + "─" * 52)
    print(f"📊 Базлайн «как было» ({n} вопросов):")
    print(f"   Среднее время ручного поиска: {avg/60:.1f} мин ({avg:.0f} сек)")
    print(f"   Не нашли ответ вообще:        {not_found}/{n}")
    print(f"   Сохранено: {BASELINE_PATH}")
    print("   Это левая колонка отчёта до/после. Правую даст бот (см. script-6.py).")


if __name__ == "__main__":
    questions = load_questions()
    interactive = sys.stdin.isatty()
    rows = measure_interactive(questions) if interactive else measure_demo(questions)
    summarize(rows)
