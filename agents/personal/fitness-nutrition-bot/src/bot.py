import logging

import anthropic
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from . import handlers as h
from .claude_service import ClaudeService
from .config import load_config
from .storage import Storage

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    config = load_config()

    anthropic_client = (
        anthropic.Anthropic(api_key=config.anthropic_api_key)
        if config.anthropic_api_key
        else anthropic.Anthropic()
    )

    application = ApplicationBuilder().token(config.telegram_token).build()
    application.bot_data["storage"] = Storage(config.db_path)
    application.bot_data["claude"] = ClaudeService(anthropic_client, config.claude_model)

    profile_conv = ConversationHandler(
        entry_points=[CommandHandler("profile", h.profile_start)],
        states={
            h.SEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, h.profile_sex)],
            h.AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, h.profile_age)],
            h.HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, h.profile_height)],
            h.WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, h.profile_weight)],
            h.ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, h.profile_activity)],
            h.GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, h.profile_goal)],
        },
        fallbacks=[CommandHandler("cancel", h.profile_cancel)],
    )

    application.add_handler(CommandHandler("start", h.start))
    application.add_handler(profile_conv)
    application.add_handler(CommandHandler("plan", h.plan))
    application.add_handler(CommandHandler("today", h.today))
    application.add_handler(CallbackQueryHandler(h.handle_log_callback))
    application.add_handler(MessageHandler(filters.PHOTO, h.handle_menu_photo), group=1)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, h.handle_text_meal), group=1
    )

    return application


def main() -> None:
    application = build_application()
    logger.info("Bot started")
    application.run_polling()
