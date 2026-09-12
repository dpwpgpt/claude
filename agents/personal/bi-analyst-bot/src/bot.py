import logging

import anthropic
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters

from . import db as dbmod
from . import handlers as h
from .config import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def build_application() -> Application:
    config = load_config()

    database = dbmod.Database(
        server=config.mssql_server,
        port=config.mssql_port,
        database=config.mssql_database,
        user=config.mssql_user,
        password=config.mssql_password,
        timeout=config.query_timeout_seconds,
    )

    tables = database.load_schema(config.allowed_schemas, config.allowed_tables)
    schema_text = dbmod.format_schema(tables)
    logger.info("Загружена схема БД: таблиц — %d", len(tables))

    application = ApplicationBuilder().token(config.telegram_token).build()
    application.bot_data["database"] = database
    application.bot_data["schema_text"] = schema_text
    application.bot_data["allowed_schemas"] = config.allowed_schemas
    application.bot_data["allowed_tables"] = config.allowed_tables
    application.bot_data["anthropic_client"] = anthropic.Anthropic()
    application.bot_data["anthropic_model"] = config.anthropic_model
    application.bot_data["max_rows"] = config.max_rows
    application.bot_data["allowed_user_ids"] = config.allowed_user_ids
    application.bot_data["show_sql"] = config.show_generated_sql

    application.add_handler(CommandHandler("start", h.start))
    application.add_handler(CommandHandler("schema", h.show_schema))
    application.add_handler(CommandHandler("refresh_schema", h.refresh_schema))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, h.handle_question))

    if not config.allowed_user_ids:
        logger.warning(
            "ALLOWED_TELEGRAM_USER_IDS не задан — бот отвечает ЛЮБОМУ пользователю Telegram. "
            "Настоятельно рекомендуется ограничить доступ в .env."
        )

    return application


def main() -> None:
    application = build_application()
    logger.info("Bot started")
    application.run_polling()
