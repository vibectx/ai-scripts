"""
День 22 — онбординг за 10 минут: self-check окружения одной командой.

Первый шаг любого внедрения — убедиться, что бот вообще заведётся на машине клиента.
Скрипт по очереди проверяет всё, что нужно для запуска, и по каждому пункту рисует
зелёную галочку или понятное «чего не хватает и как поставить»:

  1. Python подходящей версии;
  2. установлен пакет httpx (для GigaChat и Telegram);
  3. задан ключ GIGACHAT_AUTH_KEY и на него отвечает OAuth GigaChat;
  4. поднят Ollama и есть модель эмбеддингов nomic-embed-text;
  5. читается папка документов клиента.

Скрипт НИЧЕГО не ломает и не меняет — только смотрит. Ключ и Ollama не обязательны:
чего нет — покажет красным, что есть — зелёным. Ноль красных = машина готова к боту.

Запуск (из корня проекта):
    python3 week-4/scripts/script-1.py
    # с реальным окружением клиента:
    GIGACHAT_AUTH_KEY=... DOCS_DIR=путь/к/документам python3 week-4/scripts/script-1.py
"""

import os
import sys
import uuid

OK, BAD, WARN = "✅", "❌", "⚠️ "
DOCS_DIR = os.environ.get("DOCS_DIR", os.path.join(os.path.dirname(__file__), "sample_docs"))

results: list[tuple[bool, str, str]] = []   # (ок?, заголовок, подсказка при провале)


def check(title: str, ok: bool, hint: str = "") -> None:
    results.append((ok, title, hint))
    print(f"  {OK if ok else BAD} {title}" + ("" if ok else f"\n       └─ {hint}"))


def check_python() -> None:
    v = sys.version_info
    check(f"Python {v.major}.{v.minor} (нужен 3.9+)", v >= (3, 9),
          "Поставь Python 3.11+: https://www.python.org/downloads/")


def check_httpx() -> None:
    try:
        import httpx  # noqa: F401
        check("Пакет httpx установлен", True)
    except ImportError:
        check("Пакет httpx установлен", False, "pip install httpx")


def check_gigachat() -> None:
    auth = os.environ.get("GIGACHAT_AUTH_KEY")
    if not auth:
        check("Ключ GIGACHAT_AUTH_KEY задан", False,
              "Возьми «Ключ авторизации» в кабинете GigaChat и задай "
              "переменную окружения GIGACHAT_AUTH_KEY=...")
        return
    check("Ключ GIGACHAT_AUTH_KEY задан", True)
    try:
        import httpx
        verify = os.environ.get("GIGACHAT_VERIFY_SSL", "1") != "0"
        r = httpx.post(
            "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            headers={"Authorization": f"Basic {auth}", "RqUID": str(uuid.uuid4()),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"scope": os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")},
            verify=verify, timeout=20,
        )
        ok = r.status_code == 200 and "access_token" in r.json()
        check("GigaChat отвечает на авторизацию", ok,
              f"Ответ {r.status_code}. Проверь ключ/скоуп. Нет сертификата Минцифры? "
              f"для локалки GIGACHAT_VERIFY_SSL=0")
    except Exception as e:
        check("GigaChat отвечает на авторизацию", False,
              f"{type(e).__name__}: {e}. Проверь интернет и сертификат Минцифры "
              f"(или GIGACHAT_VERIFY_SSL=0 для локалки)")


def check_ollama() -> None:
    try:
        import ollama
    except ImportError:
        check("Ollama-клиент установлен", False, "pip install ollama")
        return
    check("Ollama-клиент установлен", True)
    try:
        names = [m.get("model", m.get("name", "")) for m in ollama.list().get("models", [])]
        has = any("nomic-embed-text" in n for n in names)
        check("Модель nomic-embed-text доступна", has,
              "Скачай модель: ollama pull nomic-embed-text (и запусти приложение Ollama)")
    except Exception as e:
        check("Ollama запущен и отвечает", False,
              f"{type(e).__name__}: {e}. Запусти Ollama и: ollama pull nomic-embed-text")


def check_docs() -> None:
    exts = (".pdf", ".docx", ".txt", ".md")
    if not os.path.isdir(DOCS_DIR):
        check(f"Папка документов читается ({DOCS_DIR})", False,
              "Создай папку с документами клиента и укажи DOCS_DIR=путь")
        return
    files = [f for f in os.listdir(DOCS_DIR) if f.lower().endswith(exts)]
    check(f"Папка документов читается: {len(files)} файлов ({os.path.basename(DOCS_DIR)})",
          bool(files), "Положи в папку .pdf/.docx/.txt/.md документы клиента")


if __name__ == "__main__":
    print("🩺 Self-check окружения бота (онбординг за 10 минут)\n")
    check_python()
    check_httpx()
    check_gigachat()
    check_ollama()
    check_docs()

    bad = [t for ok, t, _ in results if not ok]
    print("\n" + "─" * 52)
    if not bad:
        print(f"{OK} Всё готово ({len(results)}/{len(results)}). Можно ставить бота — переходи к script-2.")
    else:
        print(f"{WARN}Готово {len(results) - len(bad)}/{len(results)}. Осталось закрыть: {len(bad)} пункт(ов).")
        print("   Почини красные пункты по подсказкам выше и запусти проверку снова.")
    # код возврата удобен для CI/скриптов онбординга: 0 — всё зелёное
    sys.exit(1 if bad else 0)
