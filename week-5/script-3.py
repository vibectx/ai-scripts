"""
День 31 — отзыв в продающий формат: 3 вопроса → сильная цитата.

«Ну, норм работает» — бесполезный отзыв: он ничего не доказывает следующему клиенту.
Сильный отзыв — про изменение с цифрой. Чтобы его получить, задаём три точных вопроса,
а не «как вам?»:

  1. Как было ДО бота? (что раздражало, сколько времени уходило)
  2. Что изменилось ПОСЛЕ?
  3. Одна конкретная цифра (за сколько отвечает / сколько вопросов закрывает / сколько сэкономили)

Из ответов скрипт собирает готовую цитату с именем и должностью — только слова клиента,
приведённые в продающий вид. Если задан GIGACHAT_AUTH_KEY — причешет формулировку через
LLM (по желанию), иначе соберёт по шаблону. Работает без интернета и без ключа.

Запуск (из корня проекта):
    python3 week-5/scripts/script-3.py            # спросит ответы (или демо, если не tty)
    NAME="Анна" ROLE="рук. поддержки" python3 week-5/scripts/script-3.py

⚠️ Всегда бери у клиента письменное разрешение показывать отзыв и кейс.
"""

import os
import sys

NAME = os.environ.get("NAME", "Анна Петрова")
ROLE = os.environ.get("ROLE", "руководитель поддержки")
COMPANY = os.environ.get("CLIENT_NAME", "Свет в Дом")

DEMO = {
    "before": "менеджеры искали условия по регламентам по 3–4 минуты и всё равно путали редакции",
    "after": "бот отвечает мгновенно и ссылается на нужный пункт, новичок отвечает как опытный",
    "number": "70% типовых вопросов бот закрывает сам, а на ответ уходит секунды вместо минут",
}
QUESTIONS = [
    ("before", "1) Как было ДО бота? (что раздражало, сколько времени уходило)\n> "),
    ("after", "2) Что изменилось ПОСЛЕ внедрения?\n> "),
    ("number", "3) Одна конкретная цифра (за сколько отвечает / % закрытых / сколько сэкономили)?\n> "),
]


def collect():
    if not sys.stdin.isatty():
        print("ℹ️  Неинтерактивный запуск — беру демо-ответы (пример готовой цитаты).\n")
        return dict(DEMO)
    answers = {}
    for key, prompt in QUESTIONS:
        answers[key] = input(prompt).strip() or DEMO[key]
    return answers


def build_quote(a):
    quote = (f"Раньше {a['before']}. После внедрения {a['after']}. "
             f"По цифрам — {a['number']}.")
    return quote


def polish_with_llm(quote):
    """Необязательно: причесать формулировку через GigaChat, сохранив факты и цифры."""
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
            json={"model": "GigaChat", "temperature": 0.3, "messages": [
                {"role": "system", "content": "Причеши отзыв клиента в 2–3 предложения. "
                 "Сохрани ВСЕ факты и цифры, ничего не выдумывай, тон живой и деловой."},
                {"role": "user", "content": quote},
            ]}, verify=verify, timeout=60,
        ).json()
        return r["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️  LLM недоступна ({type(e).__name__}) — оставляю шаблонную цитату.")
        return None


if __name__ == "__main__":
    print("🗣  Собираю продающий отзыв. Ответы — словами клиента.\n")
    answers = collect()
    quote = build_quote(answers)
    polished = polish_with_llm(quote)
    final = polished or quote

    print("\n" + "─" * 56)
    print("Готовая цитата (согласовать с клиентом перед публикацией):\n")
    print(f"  «{final}»")
    print(f"   — {NAME}, {ROLE}, {COMPANY}")
    print("\n" + "─" * 56)
    print("✅ Отзыв переведён в соцдоказательство с цифрой. Кладём его в кейс и в sales-kit.")
    print("   Не забудь письменное разрешение показывать отзыв.")
