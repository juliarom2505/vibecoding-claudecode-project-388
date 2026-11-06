#!/usr/bin/env python3
"""Извлекает цену товара с одной страницы.

Использование:
    python3 extract.py <URL>

Печатает в stdout ровно один JSON-объект контракта:
    {"regular_price": float|null, "sale_price": float|null, "has_credit": bool}

Диагностика (откуда взята цена, ошибки) — в stderr.
Коды выхода: 0 — цена найдена; 1 — страница загружена, цены нет; 2 — страницу не загрузить.
Только стандартная библиотека Python.
"""
import json
import re
import sys
import urllib.error
import urllib.request

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


def log(msg):
    print(f"[extract-price] {msg}", file=sys.stderr)


def fetch(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def to_number(value):
    """'1.299,00' / '1299.00' / '€ 687,92' / 627 -> float; иначе None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    s = re.sub(r"[^\d.,]", "", str(value))
    if not s:
        return None
    if "," in s and "." in s:
        # разделитель копеек — тот, что правее
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = f"{head.replace(',', '')}.{tail}" if len(tail) <= 2 else s.replace(",", "")
    elif s.count(".") > 1 or re.search(r"\.\d{3}$", s):
        s = s.replace(".", "")  # точки — разделители тысяч
    try:
        n = round(float(s), 2)
    except ValueError:
        return None
    return n if n > 0 else None


def jsonld_price(html):
    """Цена из JSON-LD блока Product -> offers."""
    for raw in re.findall(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I
    ):
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            if "@graph" in node:
                stack.extend(node["@graph"])
            if node.get("@type") in ("Product", ["Product"]) and node.get("offers"):
                offers = node["offers"]
                offers = offers[0] if isinstance(offers, list) else offers
                price = to_number(offers.get("price") or offers.get("lowPrice"))
                if price:
                    return price
    return None


def meta_price(html):
    """Запасной вариант: microdata / OpenGraph."""
    for pat in (
        r'itemprop="price"[^>]*content="([^"]+)"',
        r'property="(?:product|og):price:amount"[^>]*content="([^"]+)"',
    ):
        m = re.search(pat, html)
        if m and to_number(m.group(1)):
            return to_number(m.group(1))
    return None


def ep_nl(html, price):
    """ep.nl: рекомендованная цена и рассрочка именно этого товара."""
    regular_candidates = []
    flat = html.replace('\\"', '"')
    # aria-label основного блока цены; на странице есть и цены аксессуаров —
    # берем только тот, где Price совпадает с ценой товара
    for cur, advised in re.findall(
        r'aria-label="Price ([\d.,]+)(?:, advised price ([\d.,]+))?"', flat
    ):
        if to_number(cur) == price and advised:
            regular_candidates.append(to_number(advised))
    # блок данных товара: "storePrice":X,...,"payInTerms":true,...,"originalPrice":Y
    has_credit = False
    for block in re.findall(r'"storePrice":[\d.]+,"hasStock".{0,400}?"originalPrice":[\d.]+', flat):
        if to_number(re.search(r'"storePrice":([\d.]+)', block).group(1)) != price:
            continue
        has_credit = has_credit or '"payInTerms":true' in block
        regular_candidates.append(to_number(re.search(r'"originalPrice":([\d.]+)', block).group(1)))
    return [r for r in regular_candidates if r], has_credit


def coolblue_nl(html, price):
    """coolblue.nl: зачеркнутая цена (listPrice) основного товара.

    Рассрочка у Coolblue подгружается скриптом и в HTML для конкретного товара
    не видна (тексты про «termijnen» есть на любой странице) -> has_credit = False.
    """
    flat = html.replace('\\"', '"')
    regular_candidates = []
    for lp in re.findall(
        r'"listPrice":(\{[^{}]*\}|null),"salesPrice":\{"includingVat":([\d.]+)', flat
    ):
        list_obj, sales = lp
        if to_number(sales) != price or list_obj == "null":
            continue
        m = re.search(r'"includingVat":([\d.]+)', list_obj)
        if m:
            regular_candidates.append(to_number(m.group(1)))
    return regular_candidates, False


SHOPS = {"ep.nl": ep_nl, "coolblue.nl": coolblue_nl}


def extract(url):
    empty = {"regular_price": None, "sale_price": None, "has_credit": False}
    try:
        html = fetch(url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log(f"не удалось загрузить страницу: {e}")
        return empty, 2

    price = jsonld_price(html)
    source = "json-ld"
    if price is None:
        price, source = meta_price(html), "meta"
    if price is None:
        log("цена не найдена на странице")
        return empty, 1

    regular_candidates, has_credit = [], False
    for domain, handler in SHOPS.items():
        if re.search(rf"(^|\.){re.escape(domain)}$", urllib.request.urlparse(url).hostname or ""):
            regular_candidates, has_credit = handler(html, price)
            source += f" + {domain}"
            break

    regular = max([price] + regular_candidates)
    result = {
        "regular_price": regular,
        "sale_price": price if regular > price else None,
        "has_credit": has_credit,
    }
    log(f"источник: {source}; текущая цена {price}")
    return result, 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: extract.py <URL>", file=sys.stderr)
        sys.exit(64)
    res, code = extract(sys.argv[1])
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(code)
