import os
from dataclasses import dataclass
from typing import FrozenSet, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    telegram_token: str
    mssql_server: str
    mssql_port: int
    mssql_database: str
    mssql_user: str
    mssql_password: str
    anthropic_model: str
    allowed_user_ids: FrozenSet[int]
    allowed_schemas: Optional[List[str]]
    allowed_tables: Optional[List[Tuple[str, str]]]
    max_rows: int
    query_timeout_seconds: int
    show_generated_sql: bool


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set (see .env.example)")
    return value


def _parse_user_ids(raw: Optional[str]) -> FrozenSet[int]:
    if not raw:
        return frozenset()
    return frozenset(int(x.strip()) for x in raw.split(",") if x.strip())


def _parse_schemas(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    return [x.strip() for x in raw.split(",") if x.strip()]


def _parse_tables(raw: Optional[str]) -> Optional[List[Tuple[str, str]]]:
    if not raw:
        return None
    tables = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "." in entry:
            schema, table = entry.split(".", 1)
        else:
            schema, table = "dbo", entry
        tables.append((schema.strip(), table.strip()))
    return tables or None


def _parse_bool(raw: Optional[str], default: bool) -> bool:
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() not in ("false", "0", "no")


def load_config() -> Config:
    return Config(
        telegram_token=_require("TELEGRAM_BOT_TOKEN"),
        mssql_server=_require("MSSQL_SERVER"),
        mssql_port=int(os.environ.get("MSSQL_PORT") or "1433"),
        mssql_database=_require("MSSQL_DATABASE"),
        mssql_user=_require("MSSQL_USER"),
        mssql_password=_require("MSSQL_PASSWORD"),
        anthropic_model=os.environ.get("ANTHROPIC_MODEL") or "claude-opus-5",
        allowed_user_ids=_parse_user_ids(os.environ.get("ALLOWED_TELEGRAM_USER_IDS")),
        allowed_schemas=_parse_schemas(os.environ.get("MSSQL_ALLOWED_SCHEMAS")),
        allowed_tables=_parse_tables(os.environ.get("MSSQL_ALLOWED_TABLES")),
        max_rows=int(os.environ.get("MAX_ROWS") or "200"),
        query_timeout_seconds=int(os.environ.get("QUERY_TIMEOUT_SECONDS") or "30"),
        show_generated_sql=_parse_bool(os.environ.get("SHOW_GENERATED_SQL"), True),
    )
