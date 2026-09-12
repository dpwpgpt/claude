import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def load_glossary(path: str) -> Dict[str, Dict[str, str]]:
    """Load {"schema.table": {"COLUMN": "человеко-понятное описание, синонимы"}}
    from a JSON file. Returns an empty dict if the file doesn't exist."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError):
        logger.exception("Не удалось прочитать глоссарий колонок: %s", path)
        return {}
