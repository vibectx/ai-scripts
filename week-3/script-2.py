"""
День 16 — бот работает сам, по расписанию. Никто не нажимает кнопку каждый день.

Показываем ежедневный автозапуск в самом простом виде: задаёшь время (например,
09:00) — и функция сама срабатывает раз в сутки. В пет-проекте так висит ежедневный
дайджест; тот же приём — под любую регулярную задачу бизнеса (утренняя сводка, отчёт).

Скрипт без зависимостей и без ключа: считает, сколько ждать до следующего запуска,
и в демо-режиме прокручивает несколько «дней» ускоренно, чтобы результат было видно
сразу. В проде тот же цикл живёт в фоне (или берётся APScheduler / системный cron).

Запуск (из корня проекта):
    python3 week-3/scripts/script-2.py            # демо: 3 запуска ускоренно
    RUN_AT=09:00 REAL=1 python3 week-3/scripts/script-2.py   # реальный режим, ждёт 09:00
"""

import datetime as dt
import os
import time

RUN_AT = os.environ.get("RUN_AT", "09:00")          # HH:MM ежедневного запуска
REAL = os.environ.get("REAL") == "1"                # 1 — ждать реального времени


def seconds_until(hh_mm: str, now: dt.datetime) -> float:
    """Сколько секунд до ближайшего наступления времени hh_mm (сегодня или завтра)."""
    hour, minute = (int(x) for x in hh_mm.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += dt.timedelta(days=1)              # время уже прошло — значит завтра
    return (target - now).total_seconds()


def daily_job() -> None:
    """Здесь в проде — make_digest() из пет-проекта. В демо просто отмечаемся."""
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"  🗞️  [{stamp}] запуск ежедневной задачи (тут собирается и шлётся дайджест)")


def run_real() -> None:
    """Боевой режим: бесконечный цикл, раз в сутки в RUN_AT вызывает задачу."""
    print(f"✅ Планировщик запущен. Задача — каждый день в {RUN_AT}. Ctrl+C — остановить.")
    while True:
        wait = seconds_until(RUN_AT, dt.datetime.now())
        print(f"   ⏳ до следующего запуска ~{wait / 3600:.1f} ч")
        time.sleep(wait)
        daily_job()


def run_demo(days: int = 3) -> None:
    """Демо: показываем расчёт ожидания и прокручиваем несколько запусков ускоренно."""
    now = dt.datetime.now()
    wait = seconds_until(RUN_AT, now)
    print(f"✅ Сейчас {now.strftime('%H:%M')}, следующий запуск в {RUN_AT} — "
          f"через {wait / 3600:.1f} ч (в проде бот столько и ждёт в фоне).\n")
    print(f"Демо: прокручиваю {days} ежедневных запуска ускоренно (по 1 сек вместо суток):")
    for _ in range(days):
        time.sleep(1)
        daily_job()
    print("\nПоинт: задача происходит САМА, день за днём. Автоматизация, которую надо "
          "запускать руками, — не автоматизация.")


if __name__ == "__main__":
    (run_real if REAL else run_demo)()
