import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    telegram_token: str
    anthropic_api_key: Optional[str]
    claude_model: str
    db_path: str


def load_config() -> Config:
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set (see .env.example)")

    return Config(
        telegram_token=telegram_token,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        claude_model=os.environ.get("CLAUDE_MODEL", "claude-opus-5"),
        db_path=os.environ.get("BOT_DB_PATH", "fitness_bot.db"),
    )
