"""
День 15 — «установщик» бота под клиента. На входе — папка с документами клиента
(PDF, Word, txt, md), на выходе — готовый индекс на диске, с которым бот отвечает.

Смысл всей стройки: под нового клиента бот собирается за день из одной папки, без
кода под конкретный бизнес. Этот скрипт делает ровно этот шаг: читает любой формат
(День 8), режет с нахлёстом (День 9), считает векторы (кэш, День 12) и сохраняет
индекс в JSON. Дальше бот просто загружает индекс и отвечает (см. День 17, 21).

КЛЮЧ НЕ НУЖЕН. Нужен только запущенный Ollama с моделью nomic-embed-text.
Запуск (из корня проекта):
    python3 week-3/scripts/script-1.py
    # своя папка с документами:
    DOCS_DIR=путь/к/документам_клиента python3 week-3/scripts/script-1.py

Зависимости по необходимости: pip install pypdf python-docx
"""

import glob
import json
import os

import ollama

DOCS_DIR = os.environ.get("DOCS_DIR", os.path.join(os.path.dirname(__file__), "sample_docs"))
INDEX_PATH = os.environ.get("INDEX_PATH", os.path.join(os.path.dirname(__file__), "client_index.json"))
EMBED_MODEL = "nomic-embed-text"


def read_file(path: str) -> str:
    """Любой поддержанный формат → чистый текст (сжатая версия Дня 8)."""
    low = path.lower()
    if low.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    if low.endswith(".docx"):
        import docx
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    with open(path, encoding="utf-8", errors="ignore") as f:      # .txt / .md
        return f.read()


def chunk(text: str, size: int = 240, overlap: int = 60) -> list[str]:
    """Нарезка с нахлёстом — факт не рвётся на границе кусков (День 9)."""
    text = " ".join(text.split())
    out, start = [], 0
    while start < len(text):
        piece = text[start:start + size].strip()
        if len(piece) > 30:
            out.append(piece)
        start += size - overlap
    return out


def embed(text: str) -> list[float]:
    return ollama.embeddings(model=EMBED_MODEL, prompt="search_document: " + text)["embedding"]


def build_index(docs_dir: str) -> list[dict]:
    """Папка документов → список записей {source, text, embedding} — готовый индекс."""
    paths = [p for p in sorted(glob.glob(os.path.join(docs_dir, "**", "*"), recursive=True))
             if os.path.isfile(p) and p.lower().endswith((".pdf", ".docx", ".txt", ".md"))]
    if not paths:
        raise SystemExit(f"В папке {docs_dir} нет документов (.pdf/.docx/.txt/.md). "
                         f"Задай свою папку: DOCS_DIR=... python3 week-3/scripts/script-1.py")

    index = []
    for path in paths:
        source = os.path.relpath(path, docs_dir)
        chunks = chunk(read_file(path))
        for i, piece in enumerate(chunks):
            index.append({"source": source, "chunk": i, "text": piece, "embedding": embed(piece)})
        print(f"  📄 {source}: {len(chunks)} кусков")
    return index


def _make_sample_docs(docs_dir: str) -> None:
    """Если своей папки нет — кладём демо-документы, чтобы скрипт запускался «из коробки»."""
    os.makedirs(docs_dir, exist_ok=True)
    samples = {
        "delivery.txt": "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей. "
                        "Курьер привозит в день заказа, если оформить до 14:00. В регионы — "
                        "транспортной компанией, срок 3–7 рабочих дней.",
        "returns.txt": "Вернуть товар надлежащего качества можно в течение 14 дней, если он не "
                       "был в использовании и сохранён товарный вид. Деньги возвращаются на карту "
                       "в течение 10 дней.",
        "warranty.txt": "Гарантия на технику — 12 месяцев, оформляется по кассовому чеку. "
                        "Гарантийный ремонт бесплатный при сохранённой упаковке.",
    }
    for name, text in samples.items():
        with open(os.path.join(docs_dir, name), "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    if not os.path.isdir(DOCS_DIR) or not os.listdir(DOCS_DIR):
        print(f"📁 Своей папки нет — кладу демо-документы в {DOCS_DIR}\n")
        _make_sample_docs(DOCS_DIR)

    print(f"📥 Собираю индекс из папки: {DOCS_DIR}")
    index = build_index(DOCS_DIR)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)

    sources = sorted({row["source"] for row in index})
    print(f"\n✅ Готово. {len(index)} кусков из {len(sources)} документов → {INDEX_PATH}")
    print("   Это и есть «бот под клиента за день»: подменил папку — получил его индекс.")
    print("   Дальше бот загружает этот файл и отвечает по нему (см. День 17 и 21).")
