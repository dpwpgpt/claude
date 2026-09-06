import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    telegram_token: str
    db_path: str
    foods_path: str
    templates_path: str


def load_config() -> Config:
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set (see .env.example)")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return Config(
        telegram_token=telegram_token,
        db_path=os.environ.get("BOT_DB_PATH") or "fitness_bot.db",
        foods_path=os.environ.get("FOODS_DB_PATH") or os.path.join(base_dir, "data", "foods.json"),
        templates_path=os.environ.get("MEAL_TEMPLATES_PATH")
        or os.path.join(base_dir, "data", "meal_templates.json"),
    )
