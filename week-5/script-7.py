"""
День 35 — капстоун недели 5: вся воронка продаж в одном прогоне.

Собирает воедино неделю — от сухих метрик пилота до готовых сообщений подходящим людям:
  1. метрики пилота → цифры кейса «было/стало» (День 29);
  2. ROI в рублях и срок окупаемости (День 30);
  3. отзыв клиента как соцдоказательство (День 31);
  4. sales-kit: оффер + кейс + ROI + отзыв + FAQ (День 32);
  5. квалификация лидов по чек-листу (День 33);
  6. персональные первые касания по отобранным (День 34).

На выходе — сводка воронки: кейс с цифрами, ROI, сколько лидов отобрано и готовые
касания. Подменяешь демо-цифры на данные своего пилота и лидов — получаешь запущенную
воронку на платные пилоты. Чистый Python, без ключей и интернета.

Запуск (из корня проекта):
    python3 week-5/scripts/script-7.py
    CLIENT_NAME="Свет в Дом" HOURS_PER_WEEK=12 RATE_PER_HOUR=700 python3 week-5/scripts/script-7.py
"""

import os

CLIENT = os.environ.get("CLIENT_NAME", "Свет в Дом")
HOURS = float(os.environ.get("HOURS_PER_WEEK", "12"))
RATE = float(os.environ.get("RATE_PER_HOUR", "700"))
AUTOMATION = float(os.environ.get("AUTOMATION", "0.7"))
COST = float(os.environ.get("COST", "70000"))
WEEKS_PER_YEAR = 47

# Цифры кейса (в реальном прогоне — из baseline/metrics/feedback.jsonl пилота).
CASE = {"before_min": 3.0, "after_sec": 7.0, "hit": 0.7, "helpful": 0.8, "votes": 5}
REVIEW = ("Раньше искали ответ по регламентам по 3–4 минуты, теперь бот отвечает за "
          "секунды и 70% вопросов закрывает сам.")

WEIGHTS = {"docs": 3, "repeats": 3, "time_lost": 2, "budget": 2, "warm": 1}
LEADS = [
    {"name": "Оптовая база стройматериалов", "docs": 3, "repeats": 3, "time_lost": 2, "budget": 2, "warm": 1,
     "pain": "менеджеры вручную ищут наличие и условия по прайсам"},
    {"name": "Сеть автосервисов", "docs": 2, "repeats": 3, "time_lost": 2, "budget": 1, "warm": 1,
     "pain": "первая линия повторяет одни и те же ответы клиентам"},
    {"name": "Кофейня у дома", "docs": 0, "repeats": 1, "time_lost": 0, "budget": 0, "warm": 1,
     "pain": "почти нет документов и потока вопросов"},
    {"name": "Логистическая компания", "docs": 3, "repeats": 2, "time_lost": 2, "budget": 2, "warm": 0,
     "pain": "диспетчеры ищут условия перевозок в инструкциях"},
]


def money(x):
    return f"{x:,.0f}".replace(",", " ")


def score(lead):
    return sum(min(int(lead.get(k, 0)), cap) for k, cap in WEIGHTS.items())


def touch(lead, before_min, hit):
    return (f"Здравствуйте! Заметил, что у вас {lead['pain']}. У похожего бизнеса такой "
            f"поиск свели с {before_min:.0f} минут к секундам, {hit*100:.0f}% вопросов бот "
            f"закрывает сам. У вас это сейчас как — руками?")


if __name__ == "__main__":
    speedup = round(CASE["before_min"] * 60 / CASE["after_sec"])
    saved_hours_week = HOURS * AUTOMATION
    saved_year = saved_hours_week * RATE * WEEKS_PER_YEAR
    payback_m = COST / (saved_hours_week * RATE * 52 / 12)

    print("1) Кейс пилота (было → стало):")
    print(f"   Было:  {CASE['before_min']:.1f} мин на ответ вручную")
    print(f"   Стало: {CASE['after_sec']:.1f} сек (×{speedup} быстрее), "
          f"{CASE['hit']*100:.0f}% вопросов закрыто, 👍 {CASE['helpful']*100:.0f}%")

    print("\n2) ROI:")
    print(f"   Экономия ≈ {money(saved_year)} ₽/год · внедрение {money(COST)} ₽ "
          f"окупается за ~{payback_m:.1f} мес")

    print("\n3) Отзыв (соцдоказательство):")
    print(f"   «{REVIEW}»")

    print("\n4) Sales-kit: оффер + кейс + ROI + отзыв + FAQ по возражениям — собран (script-4).")

    print("\n5) Квалификация лидов (сначала — кому нужно):")
    ranked = sorted(LEADS, key=score, reverse=True)
    hot = [ld for ld in ranked if score(ld) >= 8]
    for ld in ranked:
        mark = "🟢" if score(ld) >= 8 else ("🟡" if score(ld) >= 5 else "🔴")
        print(f"   {mark} {score(ld):>2}/{sum(WEIGHTS.values())}  {ld['name']}")

    print(f"\n6) Первые касания по отобранным ({len(hot)}):")
    for ld in hot:
        print(f"   → {ld['name']}: {touch(ld, CASE['before_min'], CASE['hit'])}")

    print("\n" + "─" * 56)
    print("✅ Воронка собрана end-to-end: метрики → кейс → ROI → sales-kit → лиды → касания.")
    print("   Подменил цифры на свой пилот и лидов — воронка на платные пилоты запущена.")
    print("   Дальше — Неделя 6: пакеты, цены и обязательная подписка на поддержку. 🙌")
