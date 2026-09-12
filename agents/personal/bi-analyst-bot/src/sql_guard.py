import re

# Keywords that would let a generated query write, delete, execute code or
# escape the read-only contract. Checked as whole words so they don't false-
# positive on column names like "CreatedDate" or "UpdatedAt".
_FORBIDDEN_WORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "MERGE", "EXEC", "EXECUTE", "GRANT", "REVOKE", "DENY", "BACKUP",
    "RESTORE", "SHUTDOWN", "OPENROWSET", "OPENQUERY", "OPENDATASOURCE",
    "BULK", "INTO",
]

_COMMENT_RE = re.compile(r"--.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)
_WORD_RE = re.compile(r"\b(" + "|".join(_FORBIDDEN_WORDS) + r")\b", re.IGNORECASE)
# sp_/xp_ system and extended stored procedures (e.g. xp_cmdshell) - matched
# separately since the trailing "_" defeats a plain \b...\b word match.
_PROC_PREFIX_RE = re.compile(r"\b(?:sp|xp)_\w*", re.IGNORECASE)


class UnsafeQueryError(ValueError):
    pass


def _strip_comments(sql: str) -> str:
    return _COMMENT_RE.sub(" ", sql)


def _statements(sql: str) -> list:
    return [s.strip() for s in sql.split(";") if s.strip()]


def sanitize_select(sql: str) -> str:
    """Validate that sql is exactly one read-only SELECT (or WITH ... SELECT)
    statement and return it. Raises UnsafeQueryError otherwise."""
    cleaned = _strip_comments(sql).strip()
    stmts = _statements(cleaned)
    if len(stmts) != 1:
        raise UnsafeQueryError("ожидается ровно один SQL-запрос")

    statement = stmts[0]
    if not re.match(r"^(SELECT|WITH)\b", statement, re.IGNORECASE):
        raise UnsafeQueryError("разрешены только запросы SELECT")

    match = _WORD_RE.search(statement) or _PROC_PREFIX_RE.search(statement)
    if match:
        raise UnsafeQueryError(f"запрещённая конструкция: {match.group(0)}")

    return statement
