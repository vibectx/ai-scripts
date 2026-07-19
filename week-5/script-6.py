"""
День 34 — outreach: персональное первое касание через боль + цифру.

«Здравствуйте, я делаю ботов, могу быть полезен?» — в корзину не дочитав: это про
меня, а не про адресата. Работающее первое касание = замеченная боль лида + короткий
факт из кейса с цифрой + лёгкий вопрос, на который не жалко ответить.

Формула: {боль лида} → {результат кейса с цифрой} → {маленький открытый вопрос}.
Скрипт собирает такое сообщение под каждого отобранного лида (из script-5). Цель
касания — не продать, а получить ответ и начать разговор. Если задан GIGACHAT_AUTH_KEY —
можно причесать формулировку через LLM (по желанию), иначе — чистый шаблон. Без ключа работает.

Запуск (из корня проекта):
    python3 week-5/scripts/script-6.py
    LEADS_PATH=week-5/scripts/leads.json python3 week-5/scripts/script-6.py
"""

import json
import os

HERE = os.path.dirname(__file__)
LEADS_PATH = os.environ.get("LEADS_PATH", os.path.join(HERE, "leads.json"))
BEFORE_MIN = float(os.environ.get("BEFORE_MIN", "3"))     # «было» из кейса, мин
HIT = float(os.environ.get("HIT", "0.7"))                 # доля закрытых вопросов

# Берём только тех, кому «писать сейчас» (порог как в script-5).
WEIGHTS = {"docs": 3, "repeats": 3, "time_lost": 2, "budget": 2, "warm": 1}
DEMO_LEADS = [
    {"name": "Оптовая база стройматериалов", "docs": 3, "repeats": 3, "time_lost": 2, "budget": 2, "warm": 1,
     "pain": "менеджеры вручную ищут наличие и условия по прайсам"},
    {"name": "Сеть автосервисов", "docs": 2, "repeats": 3, "time_lost": 2, "budget": 1, "warm": 1,
     "pain": "первая линия повторяет одни и те же ответы клиентам"},
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


def touch(lead):
    pain = lead.get("pain", "сотрудники вручную ищут ответы в документах")
    return (f"Здравствуйте! Заметил, что у вас {pain}. "
            f"У похожего бизнеса мы такой поиск свели с {BEFORE_MIN:.0f} минут к секундам — "
            f"{HIT*100:.0f}% типовых вопросов бот закрывает сам по их же регламентам. "
            f"У вас сейчас это как — руками? Если интересно, скину короткий кейс с цифрами.")


def polish_with_llm(text):
    auth = os.environ.get("GIGACHAT_AUTH_KEY")
    if not auth:
        return None
    try:
        import uuid
        import httpx
        verify = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"
        token = httpx.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={"Authorization": f"Basic {auth}", "RqUID": str(uuid.uuid4()),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"scope": os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")},
            verify=verify, timeout=20,
        ).json()["access_token"]
        r = httpx.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={"model": "GigaChat", "temperature": 0.4, "messages": [
                {"role": "system", "content": "Перепиши первое касание живо и по-человечески, "
                 "1 короткий абзац, без канцелярита и без слова «уникальный». Сохрани боль, "
                 "цифру и финальный вопрос. Не выдумывай фактов."},
                {"role": "user", "content": text},
            ]}, verify=verify, timeout=60,
        ).json()
        return r["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️  LLM недоступна ({type(e).__name__}) — оставляю шаблон.")
        return None


if __name__ == "__main__":
    leads = [ld for ld in load_leads() if score(ld) >= 8]
    if not leads:
        leads = load_leads()[:3]
    print(f"✉️  Первые касания по отобранным лидам ({len(leads)}). Цель — ответ, не продажа.\n")
    for lead in leads:
        msg = touch(lead)
        msg = polish_with_llm(msg) or msg
        print(f"→ {lead['name']}")
        print(f"  {msg}\n")

    print("─" * 56)
    print("✅ Касания готовы. Отправляй по 5 в день тёплым и подходящим — это outreach из роадмапа.")
    print("   Не спам-рассылка, а точечные сообщения, за каждым — реальный кейс.")
