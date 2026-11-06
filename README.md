# Трекер цен с Claude


[![hexlet-check](https://github.com/juliarom2505/vibecoding-claudecode-project-388/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/juliarom2505/vibecoding-claudecode-project-388/actions)

Трекер цен на кофемашины, собранный на Claude-скиллах: по одной фразе «запусти трекер»
он обходит страницы товаров, сохраняет прогон в отдельный приватный репозиторий,
сравнивает с прошлым прогоном и присылает в Telegram **только значимые изменения**.

Учебный проект Хекслета: https://ru.hexlet.io/programs/vibecoding-claudecode

## Что умеет

- Следит за 10 автоматическими кофемашинами в двух голландских магазинах — **ep.nl** и **coolblue.nl**
  (Philips, De'Longhi, JURA, Siemens; три модели — в обоих магазинах, удобно сравнивать).
- По каждому товару извлекает три величины: обычная цена, цена со скидкой, есть ли рассрочка.
- Хранит историю: каждый прогон — файл `YYYY-MM-DD.json` в приватном репозитории `tracker-data`,
  запись через GitHub MCP (каждая запись — отдельный коммит).
- Сравнивает с прошлым прогоном и отбрасывает шум по правилам из [`KNOWLEDGE.md`](KNOWLEDGE.md):
  изменение цены значимо от **1% и €5**, снижение от **10%** помечается 🔥; отдельно — начало и конец
  скидки, появление и пропажа рассрочки, новые и убранные товары, пропавшая цена.
- Присылает короткую сводку в Telegram. Текст сводки пишет дешевый sub-agent на **Haiku**,
  основная модель занимается логикой.

## Как устроено

```
«запусти трекер»
      │
      ▼
tracker ──► extract-price × 10 URL ──► таблица прогона
      │
      ├─► tracker-data: читает последний YYYY-MM-DD.json (GitHub MCP)
      ├─► diff.py + правила KNOWLEDGE.md ──► только значимые изменения
      ├─► tracker-data: сохраняет новый YYYY-MM-DD.json (GitHub MCP)
      └─► tg-summary (Haiku) ──► send.py ──► Telegram
```

| Файл | Что это |
|---|---|
| [`.claude/skills/extract-price/`](.claude/skills/extract-price/SKILL.md) | Скилл: один URL → `{ regular_price, sale_price, has_credit }`. Помощник `extract.py` достает цену из JSON-LD страницы и данных магазина |
| [`.claude/skills/tracker/`](.claude/skills/tracker/SKILL.md) | Скилл: список товаров, сценарий прогона, хранение, сравнение, отправка. Помощники `run.py`, `diff.py`, `summary.py` |
| [`.claude/agents/tg-summary.md`](.claude/agents/tg-summary.md) | Sub-agent на Haiku: diff → текст сводки для Telegram |
| [`KNOWLEDGE.md`](KNOWLEDGE.md) | Правила значимости, пороги, настройки уведомлений, сравнение стоимости Haiku и основной модели |
| [`NICHE.md`](NICHE.md) | Ниша, определение «цены», проверка магазинов и ссылок |
| [`send.py`](send.py) | Отправка текста в Telegram (только стандартная библиотека Python) |

## Стек

- Claude Code: скиллы (`SKILL.md`), sub-agent на Haiku
- GitHub MCP — чтение и запись прогонов в приватный репозиторий `tracker-data`
- Python 3 (только стандартная библиотека: `urllib`, `json`, `re`)
- Telegram Bot API

## Установка

```bash
git clone https://github.com/juliarom2505/vibecoding-claudecode-project-388.git
cd vibecoding-claudecode-project-388
```

Ничего устанавливать не нужно — нужен Python 3 и Claude Code. Дальше:

1. **Репозиторий для данных.** Создайте приватный репозиторий `tracker-data` (с README).
2. **GitHub MCP.** Подключите GitHub MCP к Claude Code (`/mcp` должен показывать `github` как `connected`).
   При подключении по личному токену — fine-grained токен только на `tracker-data`
   с правами `Contents: Read and write` и `Metadata: Read-only`.
3. **Telegram-бот.** Создайте бота в [@BotFather](https://t.me/botfather), узнайте свой chat id
   в [@userinfobot](https://t.me/userinfobot) и **напишите боту первым** любое сообщение.
4. **Секреты.** Задайте `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` — в переменных окружения
   (в облачной среде Claude Code — в настройках окружения) или в файле `.env` в корне:

   ```
   TELEGRAM_BOT_TOKEN=1234567890:AA...
   TELEGRAM_CHAT_ID=123456789
   ```

   `.env` уже в `.gitignore` — токены в репозиторий не попадают.
5. **Сеть (только для облачной среды claude.ai/code).** Разрешите домены
   `www.ep.nl`, `www.coolblue.nl` и `api.telegram.org` в Network access окружения.

## Использование

Основной сценарий — одна фраза в Claude Code:

```
запусти трекер
```

Проверить отдельные части:

```bash
python3 .claude/skills/extract-price/extract.py "https://www.ep.nl/product/jura-e8-ed-1494841"
```

```bash
python3 .claude/skills/tracker/run.py > /tmp/run.json
```

```bash
python3 send.py "тест"
```

Ответ `extract-price`:

```json
{"regular_price": 719.99, "sale_price": 687.92, "has_credit": true}
```

Пример сообщения в Telegram:

```
☕ Цены на кофемашины: 2026-11-06 (сравнение с 2026-11-05)

📉 Philips EP3326/90 Series 3300 (ep.nl): 450 € → 434 € (−16 €, −3,6%)
🔥📉 Siemens EQ.6 Plus S300 TE653M11RW (coolblue.nl): 690 € → 602 € (−88 €, −12,8%)
🏷 Philips EP5549/70 LatteGo 5500 (ep.nl): скидка 719,99 € → 687,92 €
🆕 De'Longhi Eletta Explore ECAM450.65.G (coolblue.nl): добавлен в отслеживание, 754 €

Отброшено как шум: 2
```

Добавить или убрать товар — поправить строку `магазин | модель | URL` в
[`.claude/skills/tracker/SKILL.md`](.claude/skills/tracker/SKILL.md); изменить пороги — цифры в
[`KNOWLEDGE.md`](KNOWLEDGE.md).

## Ограничения

- bol.com и mediamarkt.nl блокируют автоматические запросы (403) — в список не вошли.
- На coolblue.nl рассрочка подгружается скриптом и в HTML не видна — для Coolblue `has_credit` всегда `false`.
- На ep.nl рассрочка (in3) доступна почти на все товары — `has_credit` почти всегда `true`.

---

<details>
<summary>Автоматические тесты Хекслета</summary>

Тесты запускаются на каждый коммит. За запуск отвечает файл `.github/workflows/hexlet-check.yml` — не удаляйте и не переименовывайте ни его, ни репозиторий.

</details>

## О Хекслете

[Хекслет](https://ru.hexlet.io/) — школа программирования: авторские программы обучения с практикой, поддержкой наставников и реальными проектами, которые остаются в резюме. Этот репозиторий — один из таких проектов.
