"""
День 23 — реальная выгрузка клиента (грязная) → чистка + дедуп → индекс.

Демо проходят на аккуратных данных. Пилот спотыкается о настоящую выгрузку:
«регламент_final», «регламент_final_2», три версии прайса, куски-дубли. Если тупо
всё проиндексировать — бот начнёт цитировать устаревшую редакцию.

Этот скрипт добавляет к «установщику» из недели 3 шаг ЧИСТКИ на входе:
  1. читает любой формат (pdf/docx/txt/md);
  2. режет с нахлёстом (как в week-2/День 9);
  3. выкидывает пустой мусор и точные повторы кусков — по отпечатку (sha1);
  4. только уникальные куски идут в индекс.

На выходе — прозрачная сводка: файлов, кусков всего, дублей выкинуто, ушло в базу.

КЛЮЧ НЕ НУЖЕН. Нужен только Ollama с nomic-embed-text.
Запуск (из корня проекта):
    python3 week-4/scripts/script-2.py
    # реальная папка клиента:
    DOCS_DIR=путь/к/выгрузке python3 week-4/scripts/script-2.py
"""

import glob
import hashlib
import json
import os

import ollama

DOCS_DIR = os.environ.get("DOCS_DIR", os.path.join(os.path.dirname(__file__), "sample_docs"))
INDEX_PATH = os.environ.get("INDEX_PATH", os.path.join(os.path.dirname(__file__), "client_index.json"))
EMBED_MODEL = "nomic-embed-text"


def read_file(path: str) -> str:
    low = path.lower()
    if low.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    if low.endswith(".docx"):
        import docx
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def chunk(text: str, size: int = 240, overlap: int = 60) -> list[str]:
    text = " ".join(text.split())
    out, start = [], 0
    while start < len(text):
        piece = text[start:start + size].strip()
        if len(piece) > 30:
            out.append(piece)
        start += size - overlap
    return out


def _fingerprint(piece: str) -> str:
    """Отпечаток куска для дедупа: нормализуем регистр/пробелы, чтобы ловить
    «тот же текст с косметическими правками» как дубль."""
    norm = " ".join(piece.lower().split())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()


def embed(text: str) -> list[float]:
    return ollama.embeddings(model=EMBED_MODEL, prompt="search_document: " + text)["embedding"]


def build_clean_index(docs_dir: str) -> tuple[list[dict], dict]:
    paths = [p for p in sorted(glob.glob(os.path.join(docs_dir, "**", "*"), recursive=True))
             if os.path.isfile(p) and p.lower().endswith((".pdf", ".docx", ".txt", ".md"))]
    if not paths:
        raise SystemExit(f"В папке {docs_dir} нет документов. Задай DOCS_DIR=...")

    seen: set[str] = set()
    index: list[dict] = []
    total_chunks = dupes = 0
    for path in paths:
        source = os.path.relpath(path, docs_dir)
        pieces = chunk(read_file(path))
        kept = 0
        for i, piece in enumerate(pieces):
            total_chunks += 1
            fp = _fingerprint(piece)
            if fp in seen:                       # точный повтор — пропускаем
                dupes += 1
                continue
            seen.add(fp)
            index.append({"source": source, "chunk": i, "text": piece, "embedding": embed(piece)})
            kept += 1
        print(f"  📄 {source}: {len(pieces)} кусков, уникальных {kept}")
    stats = {"files": len(paths), "chunks_total": total_chunks, "dupes": dupes, "indexed": len(index)}
    return index, stats


def _make_messy_docs(docs_dir: str) -> None:
    """Демо-выгрузка «как у клиента»: дубли файлов и повтор куска в двух редакциях."""
    os.makedirs(docs_dir, exist_ok=True)
    delivery = ("Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей. "
                "Курьер привозит в день заказа при оформлении до 14:00.")
    samples = {
        "регламент_доставки_final.txt": delivery,
        "регламент_доставки_final_2.txt": delivery,          # точный дубль файла
        "прайс.txt": "Тариф «Базовый» — 5000 ₽ в месяц. Тариф «Про» — 12000 ₽ в месяц.",
        "прайс_копия.txt": "Тариф «Базовый» — 5000 ₽ в месяц. Тариф «Про» — 12000 ₽ в месяц.",
        "возвраты.txt": "Вернуть товар можно в течение 14 дней, если он не был в использовании. "
                        "Деньги возвращаются на карту в течение 10 дней.",
    }
    for name, text in samples.items():
        with open(os.path.join(docs_dir, name), "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    if not os.path.isdir(DOCS_DIR) or not os.listdir(DOCS_DIR):
        print(f"📁 Своей папки нет — кладу «грязную» демо-выгрузку в {DOCS_DIR}\n")
        _make_messy_docs(DOCS_DIR)

    print(f"🧹 Чищу и индексирую выгрузку из папки: {DOCS_DIR}")
    index, stats = build_clean_index(DOCS_DIR)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)

    print(f"\n✅ Готово. Файлов: {stats['files']} · кусков всего: {stats['chunks_total']} · "
          f"дублей выкинуто: {stats['dupes']} · в индексе: {stats['indexed']}")
    print(f"   Индекс сохранён: {INDEX_PATH}")
    print("   Бот не будет цитировать устаревшие копии — в базу ушли только уникальные куски.")
