#!/usr/bin/env python3
"""Формирует короткую сводку для Telegram из результата diff.py.

Использование (из корня репозитория):
    python3 .claude/skills/tracker/summary.py /tmp/diff.json /tmp/run.json > /tmp/summary.txt

Пустой stdout — отправлять нечего (нет значимых изменений и в KNOWLEDGE.md
notify_when_no_changes: 0).
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]


def setting(name, default):
    try:
        text = (ROOT / "KNOWLEDGE.md").read_text(encoding="utf-8")
        m = re.search(rf"^{name}:\s*([\d.]+)", text, re.M)
        return float(m.group(1)) if m else default
    except OSError:
        return default


def eur(x):
    """1299.0 -> '1 299 €', 687.92 -> '687,92 €'."""
    if x is None:
        return "—"
    whole = f"{int(x):,}".replace(",", " ")
    cents = round((x - int(x)) * 100)
    return f"{whole},{cents:02d} €" if cents else f"{whole} €"


def signed(x, suffix):
    sign = "−" if x < 0 else "+"
    return f"{sign}{eur(abs(x)).replace(' €', '') if suffix == ' €' else f'{abs(x):.1f}'.replace('.', ',')}{suffix}"


def line(item, ch):
    who = f"{item['name']} ({item['shop']})"
    t = ch["type"]
    if t in ("price_down", "price_up"):
        icon = ("🔥📉" if ch.get("big") else "📉") if t == "price_down" else "📈"
        return (f"{icon} {who}: {eur(ch['old'])} → {eur(ch['new'])} "
                f"({signed(ch['delta'], ' €')}, {signed(ch['delta_pct'], '%')})")
    return {
        "sale_started": f"🏷 {who}: скидка {eur(ch.get('regular'))} → {eur(ch.get('sale'))}",
        "sale_ended": f"⌛ {who}: скидка закончилась, теперь {eur(ch.get('regular'))}",
        "credit_started": f"💳 {who}: появилась рассрочка",
        "credit_ended": f"🚫💳 {who}: рассрочка пропала",
        "new_item": f"🆕 {who}: добавлен в отслеживание, {eur(ch.get('new'))}",
        "removed_item": f"➖ {who}: убран из отслеживания",
        "price_lost": f"⚠️ {who}: цена пропала (снят с продажи или сайт недоступен)",
        "price_back": f"✅ {who}: цена снова есть — {eur(ch.get('new'))}",
    }.get(t, f"• {who}: {t}")


def main():
    diff = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    run = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
    date = diff.get("current_date") or run.get("date")
    out = []

    if diff.get("first_run"):
        out.append(f"📸 Первый прогон — снимок цен на кофемашины, {date}\n")
        for i in run["items"]:
            if i["status"] != "ok":
                out.append(f"⚠️ {i['name']} ({i['shop']}) — цена недоступна")
                continue
            price = eur(i["regular_price"])
            if i["sale_price"] is not None:
                price += f" / {eur(i['sale_price'])}"
            out.append(f"☕ {i['name']} ({i['shop']}) — {price}" + (" 💳" if i["has_credit"] else ""))
    elif diff["significant"]:
        out.append(f"☕ Цены на кофемашины: {date} (сравнение с {diff['previous_date']})\n")
        for item in diff["significant"]:
            out.extend(line(item, ch) for ch in item["changes"])
        if diff["ignored"]:
            out.append(f"\nОтброшено как шум: {sum(len(i['changes']) for i in diff['ignored'])}")
    elif setting("notify_when_no_changes", 1):
        out.append(f"✅ {date}: значимых изменений цен нет "
                   f"(проверено товаров: {len(run['items'])})")

    if out:
        print("\n".join(out))


if __name__ == "__main__":
    main()
