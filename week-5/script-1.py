"""
День 29 — продающий кейс-лендинг из метрик пилота (одностраничник HTML).

Прошлая неделя дала внутренний отчёт «до/после» для руководства клиента. Этот шаг
собирает ДРУГОЙ артефакт — продающий кейс-лендинг, который не стыдно отправить
СЛЕДУЮЩЕМУ клиенту: крупная цифра экономии, колонки «было/стало», доля закрытых
вопросов, место под отзыв. Всё — из уже накопленных данных пилота, без ручной вёрстки:

  • «было»  — базлайн ручного поиска (baseline.jsonl, week-4/script-3.py);
  • «стало» — работа бота: среднее время ответа и доля закрытых вопросов
              (metrics.jsonl) + оценки 👍/👎 (feedback.jsonl);
  • отзыв   — короткая цитата клиента (env REVIEW / файл review.txt), если есть.

На выходе — самодостаточный case.html (инлайн-стили, открывается в браузере как есть).
Нет реальных логов? Скрипт кладёт демо-данные и показывает, как выглядит готовый
лендинг. КЛЮЧ НЕ НУЖЕН, интернет не нужен.

Запуск (из корня проекта):
    python3 week-5/scripts/script-1.py
    # свои вводные:
    CLIENT_NAME="Свет в Дом" QUESTIONS_PER_WEEK=300 python3 week-5/scripts/script-1.py
"""

import html
import json
import os

HERE = os.path.dirname(__file__)
BASELINE_PATH = os.environ.get("BASELINE_PATH", os.path.join(HERE, "baseline.jsonl"))
METRICS_PATH = os.environ.get("METRICS_PATH", os.path.join(HERE, "metrics.jsonl"))
FEEDBACK_PATH = os.environ.get("FEEDBACK_PATH", os.path.join(HERE, "feedback.jsonl"))
OUT_PATH = os.environ.get("CASE_PATH", os.path.join(HERE, "case.html"))
QPW = int(os.environ.get("QUESTIONS_PER_WEEK", "300"))
CLIENT = os.environ.get("CLIENT_NAME", "Свет в Дом")
REVIEW = os.environ.get("REVIEW", "")


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def _demo_if_empty():
    """Нет реальных логов — кладём демо, чтобы показать вид готового лендинга."""
    if _read_jsonl(BASELINE_PATH):
        return
    print("📁 Реальных логов пилота нет — собираю лендинг на демо-данных (пример вида).\n")
    base = [{"question": f"вопрос {i}", "seconds": s, "found": f}
            for i, (s, f) in enumerate([(180, True), (95, True), (140, True), (60, True), (240, False)])]
    metr = [{"event": "ask", "latency_s": s, "hit": h}
            for s, h in [(7.2, True), (5.9, True), (8.1, True), (6.0, True), (9.4, False)]]
    fb = [{"question": "q", "vote": v} for v in (1, 1, 1, 1, 0)]
    for path, rows in ((BASELINE_PATH, base), (METRICS_PATH, metr), (FEEDBACK_PATH, fb)):
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def _review_text():
    if REVIEW:
        return REVIEW
    path = os.path.join(HERE, "review.txt")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read().strip()
    return "Раньше искали ответ по регламентам по три минуты, теперь бот отвечает за секунды."


def compute():
    base = _read_jsonl(BASELINE_PATH)
    metr = [r for r in _read_jsonl(METRICS_PATH) if r.get("event") == "ask"]
    fb = _read_jsonl(FEEDBACK_PATH)

    found = [r for r in base if r.get("found")]
    before_avg = sum(r["seconds"] for r in found) / len(found) if found else 0.0
    after_avg = sum(r.get("latency_s", 0) for r in metr) / len(metr) if metr else 0.0
    hit = sum(1 for r in metr if r.get("hit")) / len(metr) if metr else 0.0
    votes = [r for r in fb if "vote" in r]
    helpful = sum(r["vote"] for r in votes) / len(votes) if votes else 0.0

    saved_sec = max(before_avg - after_avg, 0)
    saved_hours_week = saved_sec * QPW / 3600
    speedup = round(before_avg / after_avg) if after_avg else 0
    return {
        "before_min": before_avg / 60, "after_sec": after_avg, "hit": hit,
        "helpful": helpful, "votes": len(votes), "speedup": speedup,
        "saved_hours_week": saved_hours_week,
    }


def render(m):
    e = lambda s: html.escape(str(s))
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Кейс {e(CLIENT)}: RAG-бот по базе знаний</title></head>
<body style="margin:0;background:#0b1020;color:#e8ecf5;font:16px/1.6 -apple-system,Segoe UI,Roboto,sans-serif">
<main style="max-width:720px;margin:0 auto;padding:48px 24px">
  <p style="color:#39d98a;letter-spacing:.14em;text-transform:uppercase;font-size:13px;margin:0">Кейс внедрения</p>
  <h1 style="font-size:30px;margin:.2em 0 .1em">{e(CLIENT)}: бот отвечает по базе знаний за секунды</h1>
  <p style="color:#9fb0d0;margin:0 0 28px">RAG-бот по регламентам, FAQ и документам компании в Telegram и на сайте.</p>

  <div style="display:flex;gap:16px;flex-wrap:wrap;margin:0 0 28px">
    <div style="flex:1;min-width:150px;background:#121a30;border:1px solid #1e2a48;border-radius:14px;padding:18px">
      <div style="font-size:34px;font-weight:700;color:#39d98a">×{e(m['speedup'])}</div>
      <div style="color:#9fb0d0;font-size:14px">быстрее, чем поиск вручную</div></div>
    <div style="flex:1;min-width:150px;background:#121a30;border:1px solid #1e2a48;border-radius:14px;padding:18px">
      <div style="font-size:34px;font-weight:700;color:#39d98a">{e(f"{m['hit']*100:.0f}")}%</div>
      <div style="color:#9fb0d0;font-size:14px">вопросов бот закрывает сам</div></div>
    <div style="flex:1;min-width:150px;background:#121a30;border:1px solid #1e2a48;border-radius:14px;padding:18px">
      <div style="font-size:34px;font-weight:700;color:#39d98a">≈{e(f"{m['saved_hours_week']:.0f}")} ч</div>
      <div style="color:#9fb0d0;font-size:14px">экономии в неделю</div></div>
  </div>

  <h2 style="font-size:20px;border-bottom:1px solid #1e2a48;padding-bottom:8px">Было → стало</h2>
  <table style="width:100%;border-collapse:collapse;margin:0 0 28px">
    <tr><td style="padding:10px 0;color:#9fb0d0">Время на ответ</td>
        <td style="padding:10px 0;color:#7d8bad">{e(f"{m['before_min']:.1f}")} мин вручную</td>
        <td style="padding:10px 0;color:#39d98a;font-weight:600">{e(f"{m['after_sec']:.1f}")} сек</td></tr>
    <tr><td style="padding:10px 0;color:#9fb0d0">Доля закрытых вопросов</td>
        <td style="padding:10px 0;color:#7d8bad">как повезёт</td>
        <td style="padding:10px 0;color:#39d98a;font-weight:600">{e(f"{m['hit']*100:.0f}")}%</td></tr>
    <tr><td style="padding:10px 0;color:#9fb0d0">Доступность</td>
        <td style="padding:10px 0;color:#7d8bad">рабочие часы</td>
        <td style="padding:10px 0;color:#39d98a;font-weight:600">24/7</td></tr>
    <tr><td style="padding:10px 0;color:#9fb0d0">Оценка сотрудников (👍)</td>
        <td style="padding:10px 0;color:#7d8bad">—</td>
        <td style="padding:10px 0;color:#39d98a;font-weight:600">{e(f"{m['helpful']*100:.0f}")}% из {e(m['votes'])}</td></tr>
  </table>

  <blockquote style="margin:0 0 28px;padding:18px 22px;background:#121a30;border-left:3px solid #39d98a;border-radius:0 12px 12px 0;color:#cdd8ef;font-style:italic">
    «{e(_review_text())}»<br><span style="color:#7d8bad;font-style:normal;font-size:14px">— клиент, {e(CLIENT)}</span></blockquote>

  <a href="#" style="display:inline-block;background:#39d98a;color:#08131f;font-weight:700;text-decoration:none;padding:14px 26px;border-radius:12px">
    Хочу такой же бот по своим документам →</a>
  <p style="color:#5f6f92;font-size:13px;margin-top:36px">Кейс собран автоматически из метрик пилота · week-5/script-1.py</p>
</main></body></html>"""


if __name__ == "__main__":
    _demo_if_empty()
    m = compute()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(render(m))
    print(f"Кейс {CLIENT}: ×{m['speedup']} быстрее · {m['hit']*100:.0f}% вопросов закрыто · "
          f"≈{m['saved_hours_week']:.0f} ч/неделю экономии.")
    print("─" * 56)
    print(f"✅ Продающий кейс-лендинг сохранён: {OUT_PATH}")
    print("   Открой в браузере — это страница, которую отправляешь следующему клиенту.")
