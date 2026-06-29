"""
День 8 — данные клиента живут в PDF, Word и на сайте. Превращаем ЛЮБОЙ формат
в чистый текст, с которым уже работает бот.

Что делает скрипт: берёт документ (URL, .pdf, .docx или .txt), определяет тип
и вытаскивает из него читаемый текст без «мусора» вёрстки. Это нулевой шаг любого
бота по документам: пока данные в PDF, бот их «не видит».

Запуск (из корня проекта):
    python3 week-2/scripts/script-1.py
    # свой документ — через переменную DOC (путь к файлу или ссылка):
    DOC=путь/к/договору.pdf  python3 week-2/scripts/script-1.py
    DOC=https://site.ru/oferta  python3 week-2/scripts/script-1.py

Зависимости по необходимости:
    pip install httpx selectolax       # для веб-страниц
    pip install pypdf                  # для .pdf
    pip install python-docx            # для .docx
"""

import os

# По умолчанию — публичная веб-страница, чтобы скрипт запускался без своих файлов.
DOC = os.environ.get("DOC", "https://ru.ruwiki.ru/wiki/Машинное_обучение")


def from_url(url: str) -> str:
    """Веб-страница → текст: вырезаем тело статьи, выкидываем меню/скрипты/стили."""
    import httpx
    from selectolax.parser import HTMLParser

    html = httpx.get(
        url, timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}
    ).text
    tree = HTMLParser(html)
    for tag in tree.css("script, style, nav, header, footer, noscript"):
        tag.decompose()  # удаляем неинформативные узлы
    body = tree.css_first("article") or tree.body
    return body.text(separator="\n", strip=True)


def from_pdf(path: str) -> str:
    """PDF → текст постранично (pypdf)."""
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def from_docx(path: str) -> str:
    """Word → текст по абзацам (python-docx)."""
    import docx

    return "\n".join(p.text for p in docx.Document(path).paragraphs)


def extract(doc: str) -> str:
    """Единая точка входа: по виду источника выбираем нужный парсер."""
    if doc.startswith(("http://", "https://")):
        return from_url(doc)
    if doc.lower().endswith(".pdf"):
        return from_pdf(doc)
    if doc.lower().endswith(".docx"):
        return from_docx(doc)
    with open(doc, encoding="utf-8") as f:  # обычный .txt / .md
        return f.read()


def clean(text: str) -> str:
    """Схлопываем пустые строки и пробелы — модели нужен компактный текст."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"📥 Источник: {DOC}")
    text = clean(extract(DOC))
    paragraphs = [p for p in text.split("\n") if len(p) > 40]

    print(
        f"✅ Извлечено {len(text)} символов, {len(paragraphs)} содержательных абзацев.\n"
    )
    print("Первые 600 символов очищенного текста:\n")
    print(text[:600])
    print("\n— дальше этот текст режется на куски и идёт в бота (см. День 9).")
