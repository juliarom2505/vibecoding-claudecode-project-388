#!/usr/bin/env python3
"""Собирает таблицу прогона трекера.

Использование (из корня репозитория):
    python3 .claude/skills/tracker/run.py

Читает список товаров из .claude/skills/tracker/SKILL.md (между маркерами
urls:start / urls:end), для каждого URL вызывает скилл extract-price
(.claude/skills/extract-price/extract.py) и печатает в stdout JSON прогона:
    {"date": "YYYY-MM-DD", "items": [ {shop, name, url, regular_price, sale_price, has_credit, status}, ... ]}
Сводка по статусам — в stderr. Логику извлечения цены здесь не дублируем.
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys

SKILLS = pathlib.Path(__file__).resolve().parent.parent
EXTRACT = SKILLS / "extract-price" / "extract.py"
STATUS = {0: "ok", 1: "no_price", 2: "unavailable"}
EMPTY = {"regular_price": None, "sale_price": None, "has_credit": False}


def products():
    text = (SKILLS / "tracker" / "SKILL.md").read_text(encoding="utf-8")
    block = re.search(r"<!-- urls:start -->(.*?)<!-- urls:end -->", text, re.S).group(1)
    for line in block.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and parts[2].startswith("http"):
            yield parts


def main():
    items = []
    for shop, name, url in products():
        r = subprocess.run(
            [sys.executable, str(EXTRACT), url], capture_output=True, text=True, timeout=90
        )
        try:
            price = json.loads(r.stdout)
        except ValueError:
            price = dict(EMPTY)
        status = STATUS.get(r.returncode, "unavailable")
        items.append({"shop": shop, "name": name, "url": url, **price, "status": status})

    run = {"date": datetime.date.today().isoformat(), "items": items}
    print(json.dumps(run, ensure_ascii=False, indent=2))
    counts = {s: sum(i["status"] == s for i in items) for s in STATUS.values()}
    print(f"[tracker] {len(items)} товаров: {counts}", file=sys.stderr)


if __name__ == "__main__":
    main()
