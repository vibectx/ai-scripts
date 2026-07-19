"""
День 30 — ROI-калькулятор: перевести «сэкономили X часов» в деньги.

Собственник думает не в часах, а в рублях. Пока экономия не переведена в ₽ в год и
срок окупаемости, кейс висит в воздухе. Этот скрипт считает ROI по трём вводным,
которые клиент и так знает:

  • HOURS_PER_WEEK  — сколько часов в неделю сотрудники тратят на поиск ответов;
  • RATE_PER_HOUR   — во сколько компании обходится час такого сотрудника (₽);
  • AUTOMATION      — какую долю этих вопросов бот закрывает сам (0..1).

Плюс COST — стоимость внедрения (разовая) и SUBSCRIPTION — подписка на поддержку
(₽/мес, повторяющийся доход из роадмапа). На выходе — экономия ₽/нед, ₽/год,
срок окупаемости и годовой ROI в процентах. Чистый Python, без ключей и интернета.

Запуск (из корня проекта):
    python3 week-5/scripts/script-2.py
    HOURS_PER_WEEK=12 RATE_PER_HOUR=700 AUTOMATION=0.7 COST=70000 \
      SUBSCRIPTION=6000 python3 week-5/scripts/script-2.py
"""

import os

HOURS = float(os.environ.get("HOURS_PER_WEEK", "12"))
RATE = float(os.environ.get("RATE_PER_HOUR", "700"))
AUTOMATION = float(os.environ.get("AUTOMATION", "0.7"))
COST = float(os.environ.get("COST", "70000"))          # разовое внедрение, ₽
SUBSCRIPTION = float(os.environ.get("SUBSCRIPTION", "6000"))   # поддержка, ₽/мес
CLIENT = os.environ.get("CLIENT_NAME", "Клиент")
WEEKS_PER_YEAR = 47          # рабочие недели за вычетом отпусков/праздников


def money(x):
    """Разряды пробелами: 204000 -> '204 000'."""
    return f"{x:,.0f}".replace(",", " ")


def compute():
    saved_hours_week = HOURS * AUTOMATION
    saved_week = saved_hours_week * RATE
    saved_year = saved_week * WEEKS_PER_YEAR
    year_cost = COST + SUBSCRIPTION * 12          # первый год: внедрение + год поддержки
    net_year = saved_year - year_cost
    payback_months = (COST / (saved_week * 52 / 12)) if saved_week else float("inf")
    roi_pct = (net_year / year_cost * 100) if year_cost else 0.0
    return {
        "saved_hours_week": saved_hours_week, "saved_week": saved_week,
        "saved_year": saved_year, "year_cost": year_cost, "net_year": net_year,
        "payback_months": payback_months, "roi_pct": roi_pct,
    }


def report(m):
    payback = ("меньше месяца" if m["payback_months"] < 1
               else f"~{m['payback_months']:.1f} мес" if m["payback_months"] != float("inf")
               else "—")
    return f"""💰 ROI внедрения RAG-бота — {CLIENT}

Вводные:
  • поиск ответов вручную      {HOURS:.0f} ч/нед
  • стоимость часа сотрудника  {money(RATE)} ₽
  • бот закрывает сам          {AUTOMATION*100:.0f}% вопросов
  • внедрение (разово)         {money(COST)} ₽
  • поддержка                  {money(SUBSCRIPTION)} ₽/мес

Экономия:
  • {m['saved_hours_week']:.1f} ч/нед освобождённого времени
  • {money(m['saved_week'])} ₽/нед  →  {money(m['saved_year'])} ₽/год

Окупаемость:
  • затраты за первый год:  {money(m['year_cost'])} ₽ (внедрение + год поддержки)
  • чистая выгода за год:   {money(m['net_year'])} ₽
  • окупается за:           {payback}
  • ROI за первый год:      {m['roi_pct']:.0f}%

Фраза для встречи: «Сейчас вы теряете около {money(m['saved_year'])} ₽ в год на ручном
поиске. Внедрение окупается за {payback}, дальше — чистая экономия»."""


if __name__ == "__main__":
    m = compute()
    print(report(m))
    print("\n" + "─" * 56)
    print("✅ ROI посчитан. Эту цифру кладём в кейс рядом с «было/стало» — она продаёт сильнее всего.")
