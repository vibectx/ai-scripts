"""
День 2 — РОЛИ в общении с LLM: system / user / assistant.

Показывает две вещи:
  1) как system-роль меняет поведение на один и тот же вопрос;
  2) как assistant-роль в истории = «память» диалога.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-1/scripts/script-2.py
"""

import os
import uuid

import httpx

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-1/scripts/script-2.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"


def giga(messages, temperature=0.3):
    token = httpx.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers={"Authorization": f"Basic {AUTH}", "RqUID": str(uuid.uuid4()),
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"scope": "GIGACHAT_API_PERS"}, verify=VERIFY, timeout=20,
    ).json()["access_token"]
    r = httpx.post(
        "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "GigaChat", "messages": messages, "temperature": temperature},
        verify=VERIFY, timeout=60,
    )
    return r.json()["choices"][0]["message"]["content"].strip()


if __name__ == "__main__":
    question = "Что такое кэш простыми словами?"

    print("=== Один вопрос, разный system → разное поведение ===")
    for persona in ["Ты строгий профессор информатики. Отвечай формально, с терминами.",
                    "Ты объясняешь другу за кофе. Простыми словами, с примером из жизни."]:
        print(f"\n[system]: {persona}")
        print(giga([
            {"role": "system", "content": persona},   # КТО модель и как себя ведёт
            {"role": "user", "content": question},     # что спрашивает человек
        ]))

    print("\n\n=== assistant в истории = ПАМЯТЬ диалога ===")
    dialog = [
        {"role": "system", "content": "Ты дружелюбный ассистент."},
        {"role": "user", "content": "Меня зовут Виктор."},
        {"role": "assistant", "content": "Приятно познакомиться, Виктор!"},  # прошлый ответ модели
        {"role": "user", "content": "Как меня зовут?"},
    ]
    # Модель вспомнит имя ТОЛЬКО потому, что оно лежит в истории сообщений.
    print(giga(dialog))
