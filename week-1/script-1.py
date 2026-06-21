"""
День 1 — мини-дайджест: тянем ПОЛНЫЕ статьи Хабра и просим GigaChat сделать выжимку.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=готовый_base64_ключ python3 week-1/scripts/script-1.py
    # нет готового ключа, есть только id+secret? скрипт закодирует сам:
    GIGACHAT_CLIENT_ID=... GIGACHAT_CLIENT_SECRET=... python3 week-1/scripts/script-1.py
    # нет сертификата Минцифры? добавь GIGACHAT_VERIFY_SSL=0
"""

import base64
import os
import uuid
import xml.etree.ElementTree as ET

import httpx
from selectolax.parser import HTMLParser

# Ключ авторизации: либо готовый base64, либо собираем из client_id:client_secret.
AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    cid = os.environ.get("GIGACHAT_CLIENT_ID")
    secret = os.environ.get("GIGACHAT_CLIENT_SECRET")
    if cid and secret:
        AUTH = base64.b64encode(f"{cid}:{secret}".encode()).decode()
if not AUTH:
    raise SystemExit(
        "Задай GIGACHAT_AUTH_KEY=... (готовый base64) "
        "или GIGACHAT_CLIENT_ID=... GIGACHAT_CLIENT_SECRET=..."
    )
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"

# Сколько символов статьи отдаём модели (защита от переполнения контекста).
ARTICLE_LIMIT = 6000


def get_token():
    """Один раз получаем OAuth-токen GigaChat и переиспользуем его."""
    return httpx.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers={
            "Authorization": f"Basic {AUTH}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"scope": "GIGACHAT_API_PERS"},
        verify=VERIFY,
        timeout=20,
    ).json()["access_token"]


def giga(token, messages, temperature=0.3):
    """Вызов чата GigaChat с уже полученным токеном."""
    r = httpx.post(
        "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "GigaChat", "messages": messages, "temperature": temperature},
        verify=VERIFY,
        timeout=120,
    )
    return r.json()["choices"][0]["message"]["content"].strip()


def fetch_article_text(url):
    """Качаем страницу статьи и достаём её тело через CSS-селектор selectolax."""
    r = httpx.get(
        url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, follow_redirects=True
    )
    tree = HTMLParser(r.text)
    # Тело статьи Хабра лежит в <div class="article-formatted-body ...">.
    node = tree.css_first("div.article-formatted-body") or tree.body
    text = node.text(separator=" ", strip=True) if node else ""
    return text[:ARTICLE_LIMIT].rstrip()


def fetch_top_news(n=5):
    """Свежие статьи хаба «Искусственный интеллект»: (заголовок, ссылка, полный текст)."""
    url = "https://habr.com/ru/rss/hubs/artificial_intelligence/articles/?fl=ru"
    r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    root = ET.fromstring(r.text)
    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title")
        link = item.findtext("link")
        if not title or not link:
            continue
        items.append((title.strip(), link.strip()))
        if len(items) >= n:
            break
    return [(t, link, fetch_article_text(link)) for t, link in items]


if __name__ == "__main__":
    token = get_token()
    news = fetch_top_news()

    print("Сырые статьи дня (полный текст):")
    summaries = []
    for title, link, text in news:
        print(f"  - {title} ({len(text)} символов)")
        # Каждую статью сжимаем отдельно — так контекст не переполняется.
        one = giga(
            token,
            [
                {
                    "role": "system",
                    "content": "Ты редактор. Сожми статью в 1-2 предложения "
                    "по сути, на русском, без воды.",
                },
                {"role": "user", "content": f"Заголовок: {title}\n\nТекст:\n{text}"},
            ],
        )
        summaries.append((title, one))

    body = "\n\n".join(f"Заголовок: {t}\nСуть: {s}" for t, s in summaries)
    digest = giga(
        token,
        [
            {
                "role": "system",
                "content": "Ты редактор AI-дайджеста. Собери из готовых выжимок "
                "единый дайджест: 3-5 пунктов, по одному предложению, по делу.",
            },
            {"role": "user", "content": "Статьи дня:\n\n" + body},
        ],
    )
    print("\n=== ДАЙДЖЕСТ ОТ GigaChat ===")
    print(digest)
