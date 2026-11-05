---
name: tracker
description: Трекер цен на кофемашины — за один запуск обходит зашитый список URL товаров, для каждого вызывает скилл extract-price, собирает единую таблицу прогона (товар → цены) и сохраняет ее через GitHub MCP в приватный репозиторий tracker-data как YYYY-MM-DD.json. Применяй по фразам «запусти трекер», «прогон цен», «проверь цены по списку». Позже сюда добавятся сравнение с прошлым прогоном и уведомления в Telegram.
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
4. **Сохрани прогон в `tracker-data`** через GitHub MCP (раздел «Сохранение прогона»).
5. **Покажи результат** человеку: markdown-таблицу, итоговую строку
   «N товаров: ok — X, без цены — Y, недоступно — Z» и ссылку на коммит.

Шаги 1–3 за один вызов делает помощник — он читает список отсюда и для каждой строки
запускает скрипт скилла `extract-price`:

```bash
python3 .claude/skills/tracker/run.py > /tmp/run.json
```

stdout — готовый JSON прогона (формат ниже), stderr — сводка по статусам.

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

## Сохранение прогона

Прогоны хранятся отдельно от кода — в приватном репозитории **`juliarom2505/tracker-data`**,
ветка `main`. Пишем **через GitHub MCP**, без `git clone` / `git push`: каждая запись
файла — это сразу отдельный коммит.

**Схема хранения:** один прогон — один файл `YYYY-MM-DD.json` в корне репозитория,
имя = `date` прогона, внутри — JSON таблицы прогона (как выдал `run.py`, с отступами
в 2 пробела и переводом строки в конце).

**Как записать:**

1. Проверь, есть ли уже файл за эту дату: `get_file_contents`
   (`owner: juliarom2505`, `repo: tracker-data`, `path: YYYY-MM-DD.json`, `ref: refs/heads/main`).
   - Файла нет → создаем.
   - Файл есть (повторный прогон в тот же день) → запомни его `sha`: новый прогон
     **перезапишет** файл, а прошлая версия останется в истории коммитов.
2. Запиши файл: `create_or_update_file`
   - `owner: juliarom2505`, `repo: tracker-data`, `branch: main`, `path: YYYY-MM-DD.json`;
   - `content` — JSON прогона как есть (обычный текст, **не** base64);
   - `sha` — только если файл уже был;
   - `message` — `Run YYYY-MM-DD: N items, ok X, no_price Y, unavailable Z`.
3. Проверь запись: снова `get_file_contents` по этому пути — содержимое совпадает
   с прогоном; в ответе на шаг 2 есть ссылка на коммит — покажи ее человеку.

**Если GitHub MCP недоступен или отвечает 403** даже с валидным доступом — сохрани тем же
путем обычным `git` (клон `tracker-data` → файл → `git commit` → `git push origin main`)
и скажи человеку, что запись прошла не через MCP.
