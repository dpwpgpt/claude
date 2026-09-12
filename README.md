# claude

Репозиторий с агентами.

## Структура

- `agents/personal/` — личные агенты (для одного пользователя, без
  мультиарендности).
  - [`fitness-nutrition-bot`](agents/personal/fitness-nutrition-bot) —
    Telegram-бот помощник по фитнесу и питанию: обработка меню, подсчёт
    КБЖУ по составу блюд, составление рациона.
  - [`bi-analyst-bot`](agents/personal/bi-analyst-bot) — Telegram-бот
    BI-аналитик: отвечает на вопросы по данным в MS SQL Server на
    естественном языке, сам генерирует и выполняет read-only SQL-запросы.
