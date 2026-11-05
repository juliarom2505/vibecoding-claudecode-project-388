#!/usr/bin/env python3
"""Сравнивает свежий прогон с предыдущим по правилам из KNOWLEDGE.md.

Использование (из корня репозитория):
    python3 .claude/skills/tracker/diff.py <previous.json|-> <current.json>

`-` вместо previous — первый прогон, сравнивать не с чем.
stdout — JSON:
    {"previous_date", "current_date", "first_run",
     "significant": [ {url, shop, name, changes: [...], ...}, ... ],   # только значимые
     "ignored":     [ ... ]}                                           # изменения ниже порогов
stderr — короткая сводка.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULTS = {"price_change_pct": 1.0, "price_change_abs": 5.0, "big_drop_pct": 10.0}
OK = "ok"


def thresholds():
    """Пороги из блока thresholds в KNOWLEDGE.md."""
    t = dict(DEFAULTS)
    try:
        text = (ROOT / "KNOWLEDGE.md").read_text(encoding="utf-8")
        block = re.search(r"<!-- thresholds:start -->(.*?)<!-- thresholds:end -->", text, re.S)
        for key, val in re.findall(r"^(\w+):\s*([\d.]+)", block.group(1), re.M):
            t[key] = float(val)
    except (OSError, AttributeError):
        print("[diff] KNOWLEDGE.md не найден — пороги по умолчанию", file=sys.stderr)
    return t


def pay(item):
    """Цена к оплате: sale_price, если есть, иначе regular_price."""
    return item.get("sale_price") if item.get("sale_price") is not None else item.get("regular_price")


def compare(old, new, t):
    """Изменения по одному товару: (значимые, отброшенные)."""
    sig, ign = [], []
    old_ok, new_ok = old.get("status") == OK, new.get("status") == OK

    if old_ok and not new_ok:
        return [{"type": "price_lost", "old": pay(old), "status": new.get("status")}], []
    if not old_ok and new_ok:
        return [{"type": "price_back", "new": pay(new)}], []
    if not old_ok and not new_ok:
        return [], [{"type": "still_unavailable"}]

    # цена к оплате
    p_old, p_new = pay(old), pay(new)
    if p_old is not None and p_new is not None and p_old != p_new:
        delta = round(p_new - p_old, 2)
        pct = round(delta / p_old * 100, 2)
        ch = {"type": "price_down" if delta < 0 else "price_up",
              "old": p_old, "new": p_new, "delta": delta, "delta_pct": pct}
        if abs(pct) >= t["price_change_pct"] and abs(delta) >= t["price_change_abs"]:
            if delta < 0 and -pct >= t["big_drop_pct"]:
                ch["big"] = True
            sig.append(ch)
        else:
            ch["type"] = "price_noise"
            ign.append(ch)

    # скидка
    s_old, s_new = old.get("sale_price"), new.get("sale_price")
    if s_old is None and s_new is not None:
        sig.append({"type": "sale_started", "regular": new.get("regular_price"), "sale": s_new})
    elif s_old is not None and s_new is None:
        sig.append({"type": "sale_ended", "old_sale": s_old, "regular": new.get("regular_price")})
    elif s_old is not None and old.get("regular_price") != new.get("regular_price"):
        ign.append({"type": "regular_only", "old": old.get("regular_price"),
                    "new": new.get("regular_price")})

    # рассрочка
    if bool(old.get("has_credit")) != bool(new.get("has_credit")):
        sig.append({"type": "credit_started" if new.get("has_credit") else "credit_ended"})

    return sig, ign


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(64)
    prev_path, cur_path = sys.argv[1], sys.argv[2]
    cur = json.loads(pathlib.Path(cur_path).read_text(encoding="utf-8"))
    t = thresholds()
    out = {"previous_date": None, "current_date": cur.get("date"),
           "first_run": prev_path == "-", "thresholds": t, "significant": [], "ignored": []}

    if prev_path == "-":
        print("[diff] первый прогон — сравнивать не с чем", file=sys.stderr)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    prev = json.loads(pathlib.Path(prev_path).read_text(encoding="utf-8"))
    out["previous_date"] = prev.get("date")
    old_by_url = {i["url"]: i for i in prev.get("items", [])}
    new_by_url = {i["url"]: i for i in cur.get("items", [])}

    def head(item):
        return {"url": item["url"], "shop": item.get("shop"), "name": item.get("name"),
                "price_now": pay(item)}

    for url, new in new_by_url.items():
        old = old_by_url.get(url)
        if old is None:
            out["significant"].append({**head(new), "changes": [{"type": "new_item", "new": pay(new)}]})
            continue
        sig, ign = compare(old, new, t)
        if sig:
            out["significant"].append({**head(new), "changes": sig})
        if ign:
            out["ignored"].append({**head(new), "changes": ign})

    for url, old in old_by_url.items():
        if url not in new_by_url:
            out["significant"].append({**head(old), "price_now": None,
                                       "changes": [{"type": "removed_item", "old": pay(old)}]})

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[diff] {out['previous_date']} → {out['current_date']}: значимых товаров "
          f"{len(out['significant'])}, отброшено {len(out['ignored'])}, "
          f"без изменений {len(new_by_url) - len({c['url'] for c in out['significant'] + out['ignored']} & set(new_by_url))}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
