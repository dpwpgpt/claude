import re

import anthropic

_SQL_FENCE_RE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)

SYSTEM_PROMPT_TEMPLATE = """\
Ты — генератор T-SQL запросов для Microsoft SQL Server. Тебе дана схема базы \
данных и вопрос пользователя на естественном языке. Твоя задача — сгенерировать \
ОДИН корректный read-only SQL-запрос (SELECT или WITH ... SELECT), который \
отвечает на вопрос.

Схема базы данных:
{schema}

Правила:
- Используй ТОЛЬКО таблицы и колонки, перечисленные выше. Если вопрос требует \
данных, которых нет в схеме, или вопрос не связан с данными, вместо SQL ответь \
одной строкой вида: NO_QUERY: <краткое объяснение по-русски>.
- Разрешены только операторы чтения: SELECT (в том числе с CTE через WITH). \
Никогда не используй INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, \
MERGE, EXEC/EXECUTE, GRANT/REVOKE, BACKUP/RESTORE, SELECT INTO и подобные \
конструкции.
- Если запрос не является агрегатом, возвращающим одну строку (COUNT, SUM, \
AVG и т.п. без группировки), обязательно ограничивай выборку через \
"TOP {max_rows}", чтобы не возвращать слишком много строк.
- Используй диалект T-SQL (Microsoft SQL Server): [квадратные скобки] для \
идентификаторов при необходимости, GETDATE() для текущей даты и т.д.
- В ответе верни ТОЛЬКО сам SQL-запрос, без markdown-разметки, без пояснений, \
без точки с запятой в конце.
"""


class NoQueryError(ValueError):
    """Raised when the model decides the question can't be answered from the schema."""


def generate_sql(
    client: anthropic.Anthropic, model: str, schema_text: str, max_rows: int, question: str
) -> str:
    system = SYSTEM_PROMPT_TEMPLATE.format(schema=schema_text, max_rows=max_rows)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    text = "".join(block.text for block in response.content if block.type == "text").strip()

    if text.upper().startswith("NO_QUERY"):
        explanation = (
            text.split(":", 1)[1].strip()
            if ":" in text
            else "Не могу ответить на этот вопрос по имеющейся схеме."
        )
        raise NoQueryError(explanation)

    return _SQL_FENCE_RE.sub("", text).strip()
