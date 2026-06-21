"""
День 4 — интеграция с GigaChat вживую: получаем токен и задаём вопрос.
Российский ИИ, оплата в рублях, данные не уходят за рубеж.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-1/scripts/script-4.py
    # нет сертификата Минцифры? добавь GIGACHAT_VERIFY_SSL=0
"""

import os
import uuid

import httpx

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-1/scripts/script-4.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"

# Шаг 1 — получаем access-токен (живёт ~30 минут).
resp = httpx.post(
    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
    headers={"Authorization": f"Basic {AUTH}",
             "RqUID": str(uuid.uuid4()),           # любой уникальный id запроса
             "Content-Type": "application/x-www-form-urlencoded"},
    data={"scope": "GIGACHAT_API_PERS"},           # PERS = для физлица
    verify=VERIFY, timeout=20,
)
resp.raise_for_status()
token = resp.json()["access_token"]
print("✅ Токен получен.")

# Шаг 2 — задаём вопрос модели.
chat = httpx.post(
    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={"model": "GigaChat", "messages": [
        {"role": "user", "content": "Назови 3 задачи бизнеса, которые решает чат-бот. Коротко."}
    ]},
    verify=VERIFY, timeout=60,
)
chat.raise_for_status()
print("\nОтвет GigaChat:")
print(chat.json()["choices"][0]["message"]["content"].strip())
