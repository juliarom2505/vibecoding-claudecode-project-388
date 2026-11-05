---
name: tracker
description: Трекер цен на кофемашины — за один запуск обходит зашитый список URL товаров, для каждого вызывает скилл extract-price и собирает единую таблицу прогона (товар → цены). Применяй по фразам «запусти трекер», «прогон цен», «проверь цены по списку». Позже сюда добавятся хранение прогонов, сравнение с прошлым прогоном и уведомления в Telegram.
---

# tracker

Один запуск = один **прогон**: все товары из списка ниже → одна таблица цен.

## Отслеживаемые товары

Список зашит здесь, чтобы трекер запускался одной фразой. Формат строки:
`магазин | модель | URL`. Чтобы добавить или убрать товар — правь строки между маркерами.

<!-- urls:start -->
```text
ep.nl       | Philips EP5549/70 LatteGo 5500          | https://www.ep.nl/product/philips-ep5549-70-1452003
ep.nl       | Philips EP3326/90 Series 3300           | https://www.ep.nl/product/philips-ep3326-90-1423459
ep.nl       | De'Longhi ECAM290.22.B Magnifica Evo    | https://www.ep.nl/product/de-longhi-ecam-290-22-b-1345349
ep.nl       | De'Longhi ECAM450.65.S Eletta Explore   | https://www.ep.nl/product/de-longhi-ecam450-65-s-eletta-explore-1407448
ep.nl       | JURA E8 (ED)                            | https://www.ep.nl/product/jura-e8-ed-1494841
ep.nl       | Siemens EQ.6 plus s300 TE653M11RW       | https://www.ep.nl/product/siemens-te653m11rw-1460759
coolblue.nl | Philips LatteGo 5500 EP5547/90          | https://www.coolblue.nl/product/945962/philips-lattego-5500-ep5547-90.html
coolblue.nl | De'Longhi Eletta Explore ECAM450.65.G   | https://www.coolblue.nl/product/938240/de-longhi-eletta-explore-ecam450-65-g.html
coolblue.nl | JURA E8 Piano Black (ED)                | https://www.coolblue.nl/product/979188/jura-e8-piano-black-ed.html
coolblue.nl | Siemens EQ.6 Plus S300 TE653M11RW       | https://www.coolblue.nl/product/833086/siemens-eq-6-plus-s300-te653m11rw.html
```
<!-- urls:end -->

## Главный сценарий

1. **Прочитай список** товаров выше (все строки между маркерами `urls:start` / `urls:end`).
2. **Для каждого URL примени скилл `extract-price`** и получи объект
   `{ regular_price, sale_price, has_credit }`.
   - `tracker` **не извлекает цены сам** и не дублирует логику `extract-price`
     (где искать цену, как нормализовать числа, что делать с рассрочкой) —
     все это живет только в `.claude/skills/extract-price/`. Если извлечение надо
     поправить, правится `extract-price`, а трекер подхватит изменения автоматически.
   - Обрабатывай **все** товары, даже если какой-то упал: ошибка одного URL
     не останавливает прогон, а попадает в таблицу со статусом.
3. **Собери таблицу прогона** (формат ниже) — одна строка на товар, в порядке списка.
4. **Покажи результат** человеку: markdown-таблицу и итоговую строку
   «N товаров: ok — X, без цены — Y, недоступно — Z».

Вызвать `extract-price` для всего списка за один шаг можно так — это тот же скрипт
скилла `extract-price`, просто по очереди для каждой строки:

```bash
sed -n '/<!-- urls:start -->/,/<!-- urls:end -->/p' .claude/skills/tracker/SKILL.md \
  | grep -E '\| *https?://' \
  | while IFS='|' read -r shop name url; do
      shop=$(echo $shop); name=$(echo $name); url=$(echo $url)
      price=$(python3 .claude/skills/extract-price/extract.py "$url" 2>/dev/null); code=$?
      printf '%s\t%s\t%s\t%s\t%s\n' "$shop" "$name" "$url" "$code" "$price"
    done
```

Каждая строка вывода: `магазин`, `модель`, `URL`, код выхода `extract-price`, объект цены.

## Таблица прогона

Это будущая запись прогона (на следующих шагах она сохраняется в репозиторий
`tracker-data` как `YYYY-MM-DD.json`). Формат JSON:

```json
{
  "date": "2026-11-05",
  "items": [
    {
      "shop": "ep.nl",
      "name": "Philips EP5549/70 LatteGo 5500",
      "url": "https://www.ep.nl/product/philips-ep5549-70-1452003",
      "regular_price": 719.99,
      "sale_price": 687.92,
      "has_credit": true,
      "status": "ok"
    }
  ]
}
```

- `date` — дата прогона, `YYYY-MM-DD`.
- `items` — по одному объекту на **каждый** URL из списка, в том же порядке.
- `regular_price`, `sale_price`, `has_credit` — ровно то, что вернул `extract-price`, без изменений.
- `status` — по коду выхода `extract-price`: `0` → `"ok"`, `1` → `"no_price"`, `2` → `"unavailable"`.

Для человека та же таблица в markdown:

| Магазин | Модель | Обычная, € | Со скидкой, € | Рассрочка | Статус |
|---|---|---|---|---|---|
| ep.nl | Philips EP5549/70 LatteGo 5500 | 719.99 | 687.92 | да | ok |

`null` показывай как «—».
