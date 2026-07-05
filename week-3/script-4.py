"""
День 18 — тот же бот, но на САЙТЕ, а не только в Telegram. Движок ответа один,
меняется лишь «витрина». Поднимаем маленький веб-адрес /chat, которому страница шлёт
вопрос и получает ответ по документам, и отдаём одностраничный чат-виджет.

Открой в браузере http://127.0.0.1:8000 — печатаешь вопрос, получаешь ответ по базе
со ссылкой на источник. Дальше этот виджет вставляется на сайт клиента (iframe или
пара строк JS на свой /chat).

Запуск (из корня проекта):
    GIGACHAT_AUTH_KEY=ваш_ключ ./venv/bin/python week-3/scripts/script-4.py
    # нужен Ollama с nomic-embed-text; нет сертификата Минцифры? GIGACHAT_VERIFY_SSL=0
    # зависимости уже в venv проекта: fastapi, uvicorn, httpx, ollama
"""

import math
import os
import uuid

import httpx
import ollama
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

AUTH = os.environ.get("GIGACHAT_AUTH_KEY")
if not AUTH:
    raise SystemExit("Задай ключ: GIGACHAT_AUTH_KEY=... ./venv/bin/python week-3/scripts/script-4.py")
VERIFY = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"

DOCS = [
    ("delivery", "Доставка по Москве — 300 рублей, бесплатно при заказе от 5000 рублей. "
                 "В регионы — транспортной компанией за 3–7 рабочих дней."),
    ("returns", "Вернуть товар можно в течение 14 дней, если он не был в использовании. "
                "Деньги возвращаются на карту в течение 10 дней."),
    ("warranty", "Гарантия на технику — 12 месяцев по кассовому чеку."),
]


def embed(text, prefix):
    return ollama.embeddings(model="nomic-embed-text", prompt=prefix + text)["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


VECS = [embed(text, "search_document: ") for _, text in DOCS]


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


def answer(question: str) -> dict:
    qv = embed(question, "search_query: ")
    score, (src, text) = max(((cosine(qv, v), d) for v, d in zip(VECS, DOCS)), key=lambda x: x[0])
    reply = giga([
        {"role": "system", "content": "Отвечай кратко и только по документу ниже. "
                                      "Нет ответа — скажи «не знаю»."},
        {"role": "user", "content": f"Документ: {text}\n\nВопрос: {question}"},
    ])
    return {"answer": reply, "source": src, "score": round(score, 2)}


# Одностраничный чат-виджет — весь фронтенд в одной строке, без внешних зависимостей.
PAGE = """<!doctype html><html lang="ru"><meta charset="utf-8">
<title>Бот на сайте</title>
<style>
 body{font-family:system-ui;background:#0a101e;color:#dce9ff;display:flex;
   justify-content:center;padding:40px}
 .box{width:520px;max-width:92vw}
 #log{background:#0e1626;border:1px solid #27374f;border-radius:14px;padding:16px;
   height:360px;overflow:auto;margin-bottom:12px}
 .u{color:#7ee8ff;margin:8px 0}.b{color:#7dffc7;margin:8px 0}.s{color:#5a6b8c;font-size:12px}
 input{width:75%;padding:12px;border-radius:10px;border:1px solid #27374f;background:#0e1626;color:#fff}
 button{padding:12px 16px;border:0;border-radius:10px;background:#2ef2a1;color:#04121a;font-weight:700;cursor:pointer}
</style>
<div class="box"><h3>💬 Бот-помощник по документам</h3>
<div id="log"><div class="s">Спросите, например: «Сколько стоит доставка по Москве?»</div></div>
<input id="q" placeholder="Ваш вопрос…" onkeydown="if(event.key==='Enter')ask()">
<button onclick="ask()">Спросить</button></div>
<script>
async function ask(){
 const q=document.getElementById('q'),log=document.getElementById('log');
 if(!q.value.trim())return; const text=q.value; q.value='';
 log.innerHTML+='<div class="u">🙋 '+text+'</div>';
 log.innerHTML+='<div class="s" id="w">…думаю</div>'; log.scrollTop=log.scrollHeight;
 const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({question:text})}); const d=await r.json();
 document.getElementById('w').remove();
 log.innerHTML+='<div class="b">🤖 '+d.answer+'</div>'+
   '<div class="s">📄 источник: '+d.source+' (похожесть '+d.score+')</div>';
 log.scrollTop=log.scrollHeight;
}
</script></html>"""

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.post("/chat")
async def chat(payload: dict):
    question = (payload.get("question") or "").strip()
    if not question:
        return JSONResponse({"answer": "Задайте вопрос.", "source": "-", "score": 0})
    return answer(question)


if __name__ == "__main__":
    print("✅ Открой в браузере http://127.0.0.1:8000  — это бот на сайте. Ctrl+C — стоп.")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
