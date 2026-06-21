"""
День 6 — переиспользуемый шаблон: меняешь ПАПКУ с документами → бот под новый бизнес.

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ python3 week-1/scripts/script-6.py
    # под другого клиента — просто укажи другую папку:
    GIGACHAT_AUTH_KEY=... DOCS_DIR=путь/к/докам python3 week-1/scripts/script-6.py
"""

import glob
import math
import os
import uuid

import httpx
import ollama

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... python3 week-1/scripts/script-6.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"
DOCS_DIR = os.environ.get("DOCS_DIR", "week-1/ai-digest/knowledge")   # ← единственное, что меняется


def giga(messages, temperature=0.1):
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


def embed(text, prefix):
    return ollama.embeddings(model="nomic-embed-text", prompt=prefix + text)["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def load_folder(folder):
    """Любая папка с .md → список кусков текста. Это и есть «база знаний клиента»."""
    chunks = []
    for path in sorted(glob.glob(os.path.join(folder, "*.md"))):
        with open(path, encoding="utf-8") as f:
            for para in f.read().split("\n\n"):
                para = para.strip()
                if len(para) > 20 and not para.startswith("#"):
                    chunks.append(para)
    return chunks


DOCS = load_folder(DOCS_DIR)
print(f"Загружено {len(DOCS)} кусков из папки: {DOCS_DIR}")
DOC_VECS = [embed(d, "search_document: ") for d in DOCS]


def answer(question):
    qv = embed(question, "search_query: ")
    context = "\n".join(sorted(DOCS, key=lambda d: cosine(qv, DOC_VECS[DOCS.index(d)]),
                               reverse=True)[:3])
    return giga([
        {"role": "system", "content": "Отвечай строго по документам ниже, не выдумывай. "
                                      "Нет ответа — скажи «не знаю»."},
        {"role": "user", "content": f"Документы:\n{context}\n\nВопрос: {question}"},
    ])


if __name__ == "__main__":
    print("\n💬", answer("Сколько стоит доставка по Москве?"))
