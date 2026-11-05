#!/usr/bin/env python3
"""Отправляет текст в Telegram от имени бота.

Использование:
    python3 send.py "текст сообщения"
    python3 send.py - < summary.txt      # текст из stdin

Токен и chat id берутся из переменных окружения TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID,
а если их нет — из файла .env рядом со скриптом (строки KEY=value).
Только стандартная библиотека Python, ничего устанавливать не нужно.
Коды выхода: 0 — отправлено; 1 — ошибка Telegram или сети; 2 — нет настроек/текста.
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

LIMIT = 4096  # максимальная длина одного сообщения в Telegram


def load_env():
    env_file = pathlib.Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")


def chunks(text):
    """Режет длинный текст по строкам на куски не длиннее LIMIT."""
    part = ""
    for line in text.splitlines(keepends=True):
        while len(line) > LIMIT:
            if part:
                yield part
                part = ""
            yield line[:LIMIT]
            line = line[LIMIT:]
        if len(part) + len(line) > LIMIT:
            yield part
            part = ""
        part += line
    if part.strip():
        yield part


def send(token, chat_id, text):
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    if len(sys.argv) != 2:
        print('usage: python3 send.py "текст"  |  python3 send.py - < file', file=sys.stderr)
        return 2
    text = sys.stdin.read() if sys.argv[1] == "-" else sys.argv[1]
    if not text.strip():
        print("Пустой текст — нечего отправлять.", file=sys.stderr)
        return 2

    token, chat_id = load_env()
    if not token or not chat_id:
        print("Не заданы TELEGRAM_BOT_TOKEN и/или TELEGRAM_CHAT_ID "
              "(переменные окружения или .env рядом с send.py).", file=sys.stderr)
        return 2

    try:
        for part in chunks(text):
            send(token, chat_id, part)
    except urllib.error.HTTPError as e:
        try:
            desc = json.load(e).get("description", "")
        except ValueError:
            desc = ""
        hint = {
            401: "неверный токен бота — проверь TELEGRAM_BOT_TOKEN.",
            400: "чаще всего неверный TELEGRAM_CHAT_ID.",
            403: "бот не может писать первым — открой чат с ботом и отправь ему любое сообщение.",
        }.get(e.code, "")
        print(f"Ошибка Telegram {e.code}: {desc}. {hint}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"Нет связи с api.telegram.org: {e}. Проверь сеть окружения "
              "(api.telegram.org должен быть в разрешенных доменах).", file=sys.stderr)
        return 1

    print("Отправлено.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
