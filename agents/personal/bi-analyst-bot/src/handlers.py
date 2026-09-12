import io
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from . import db as dbmod
from . import formatting, sql_guard
from .nl2sql import NoQueryError, generate_sql

logger = logging.getLogger(__name__)

TELEGRAM_TEXT_LIMIT = 4096


def _chunk_text(text: str, limit: int):
    for i in range(0, len(text), limit):
        yield text[i : i + limit]


def _is_allowed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    allowed = context.bot_data["allowed_user_ids"]
    return not allowed or user_id in allowed


async def _reply_unauthorized(update: Update) -> None:
    logger.warning("Unauthorized access attempt from user_id=%s", update.effective_user.id)
    await update.message.reply_text("У тебя нет доступа к этому боту.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(context, update.effective_user.id):
        await _reply_unauthorized(update)
        return
    await update.message.reply_text(
        "Привет! Я BI-аналитик — отвечаю на вопросы по данным в базе на "
        "естественном языке.\n\n"
        "Просто напиши вопрос, например:\n"
        "«Сколько заказов было в прошлом месяце?»\n"
        "«Топ-10 клиентов по сумме продаж»\n\n"
        "Команды:\n"
        "/schema — показать таблицы и колонки, которые я вижу\n"
        "/refresh_schema — перечитать схему базы данных заново"
    )


async def show_schema(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(context, update.effective_user.id):
        await _reply_unauthorized(update)
        return
    schema_text = context.bot_data["schema_text"]
    if not schema_text:
        await update.message.reply_text("Не нашёл ни одной таблицы в базе данных.")
        return
    for chunk in _chunk_text(f"```\n{schema_text}\n```", TELEGRAM_TEXT_LIMIT):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


async def refresh_schema(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(context, update.effective_user.id):
        await _reply_unauthorized(update)
        return
    database: dbmod.Database = context.bot_data["database"]
    allowed_schemas = context.bot_data["allowed_schemas"]
    try:
        tables = database.load_schema(allowed_schemas)
    except Exception:
        logger.exception("Не удалось обновить схему базы данных")
        await update.message.reply_text("Не удалось подключиться к базе данных, чтобы обновить схему.")
        return
    context.bot_data["schema_text"] = dbmod.format_schema(tables)
    await update.message.reply_text(f"Схема обновлена: таблиц — {len(tables)}.")


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(context, update.effective_user.id):
        await _reply_unauthorized(update)
        return

    question = update.message.text.strip()
    if not question:
        return

    schema_text = context.bot_data["schema_text"]
    if not schema_text:
        await update.message.reply_text("Не вижу ни одной таблицы в базе данных — нечего анализировать.")
        return

    client = context.bot_data["anthropic_client"]
    model = context.bot_data["anthropic_model"]
    max_rows = context.bot_data["max_rows"]

    await update.message.chat.send_action("typing")

    try:
        sql = generate_sql(client, model, schema_text, max_rows, question)
    except NoQueryError as e:
        await update.message.reply_text(str(e))
        return
    except Exception:
        logger.exception("Ошибка при обращении к Claude API")
        await update.message.reply_text("Не получилось сгенерировать SQL-запрос, попробуй ещё раз.")
        return

    try:
        safe_sql = sql_guard.sanitize_select(sql)
    except sql_guard.UnsafeQueryError as e:
        logger.warning("Сгенерированный запрос отклонён проверкой безопасности: %s | SQL: %s", e, sql)
        await update.message.reply_text(
            f"Не могу выполнить этот запрос — он не прошёл проверку безопасности ({e})."
        )
        return

    database: dbmod.Database = context.bot_data["database"]
    try:
        columns, rows, truncated = database.run_query(safe_sql, max_rows)
    except Exception:
        logger.exception("Ошибка выполнения SQL-запроса: %s", safe_sql)
        await update.message.reply_text(
            "Запрос к базе данных завершился ошибкой. Попробуй переформулировать вопрос."
        )
        return

    if context.bot_data["show_sql"]:
        for chunk in _chunk_text(f"SQL:\n```sql\n{safe_sql}\n```", TELEGRAM_TEXT_LIMIT):
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)

    if not rows:
        await update.message.reply_text("Запрос выполнен, но результат пустой.")
        return

    table_text = formatting.format_as_table(columns, rows)
    wrapped = f"```\n{table_text}\n```"

    if len(wrapped) <= TELEGRAM_TEXT_LIMIT:
        await update.message.reply_text(wrapped, parse_mode=ParseMode.MARKDOWN)
    else:
        csv_bytes = formatting.rows_to_csv(columns, rows)
        await update.message.reply_document(
            document=io.BytesIO(csv_bytes),
            filename="result.csv",
            caption=f"Результат: {len(rows)} строк(и) — слишком большой для сообщения.",
        )

    if truncated:
        await update.message.reply_text(
            f"Показаны первые {max_rows} строк(и) — результат мог быть обрезан."
        )
