"""
День 33 — квалификация лида: чек-лист «подходит / не подходит» → скоринг.

После первого кейса тянет писать всем подряд — это выжигает контакты. RAG-бот по базе
знаний нужен не любому бизнесу: там, где есть гора документов, поток однотипных
вопросов, живой человек, теряющий на этом время, и бюджет. Скрипт скорит лида по
чек-листу и раскладывает в три корзины: «писать сейчас», «на потом», «не тратить время».

Критерии (0 — нет, выше — сильнее):
  • docs        — много документов/регламентов        (0–3)
  • repeats     — вопросы часто повторяются            (0–3)
  • time_lost   — есть, кто реально теряет время        (0–2)
  • budget      — есть кому и чем платить               (0–2)
  • warm        — тёплый/полу-тёплый контакт            (0–1)

Итог ≥ 8 → «писать сейчас», 5–7 → «на потом (прогрев)», < 5 → «не тратить время».
Свои лиды — в leads.json рядом (список объектов с этими полями). Чистый Python.

Запуск (из корня проекта):
    python3 week-5/scripts/script-5.py
    LEADS_PATH=week-5/scripts/leads.json python3 week-5/scripts/script-5.py
"""

import json
import os

HERE = os.path.dirname(__file__)
LEADS_PATH = os.environ.get("LEADS_PATH", os.path.join(HERE, "leads.json"))
WEIGHTS = {"docs": 3, "repeats": 3, "time_lost": 2, "budget": 2, "warm": 1}   # максимумы

DEMO_LEADS = [
    {"name": "Оптовая база стройматериалов", "docs": 3, "repeats": 3, "time_lost": 2, "budget": 2, "warm": 1,
     "pain": "менеджеры вручную ищут наличие и условия по прайсам"},
    {"name": "Сеть автосервисов (знакомый)", "docs": 2, "repeats": 3, "time_lost": 2, "budget": 1, "warm": 1,
     "pain": "первая линия повторяет одни и те же ответы клиентам"},
    {"name": "Юрфирма", "docs": 3, "repeats": 2, "time_lost": 2, "budget": 2, "warm": 0,
     "pain": "юристы ищут формулировки по внутренним регламентам"},
    {"name": "Кофейня у дома", "docs": 0, "repeats": 1, "time_lost": 0, "budget": 0, "warm": 1,
     "pain": "почти нет документов и потока вопросов"},
    {"name": "Стартап на 3 человека", "docs": 1, "repeats": 1, "time_lost": 1, "budget": 0, "warm": 1,
     "pain": "документов мало, бюджета пока нет"},
    {"name": "Логистическая компания", "docs": 3, "repeats": 2, "time_lost": 2, "budget": 2, "warm": 0,
     "pain": "диспетчеры ищут условия перевозок в инструкциях"},
]


def load_leads():
    if os.path.exists(LEADS_PATH):
        with open(LEADS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return DEMO_LEADS


def score(lead):
    return sum(min(int(lead.get(k, 0)), cap) for k, cap in WEIGHTS.items())


def bucket(s):
    if s >= 8:
        return "🟢 писать сейчас"
    if s >= 5:
        return "🟡 на потом (прогрев)"
    return "🔴 не тратить время"


if __name__ == "__main__":
    leads = load_leads()
    ranked = sorted(leads, key=score, reverse=True)
    max_score = sum(WEIGHTS.values())

    print(f"🎯 Квалификация лидов (макс {max_score} баллов). Сначала — кому оффер реально нужен:\n")
    now = 0
    for lead in ranked:
        s = score(lead)
        b = bucket(s)
        now += b.startswith("🟢")
        print(f"  {b:<22} {s:>2}/{max_score}  {lead['name']}")
        print(f"      └ {lead.get('pain', '')}")

    print("\n" + "─" * 56)
    print(f"✅ Отобрано «писать сейчас»: {now} из {len(leads)}. Остальные — в прогрев или мимо.")
    print("   Десять точных касаний подходящим лидам > ста холодных в молоко.")
    print("   Следующий шаг (script-6) — первое касание по отобранным.")
