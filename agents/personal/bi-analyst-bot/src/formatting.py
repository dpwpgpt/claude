import csv
import io
from typing import Sequence

MAX_COLUMN_WIDTH = 24


def _format_cell(value) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    if len(text) > MAX_COLUMN_WIDTH:
        text = text[: MAX_COLUMN_WIDTH - 1] + "…"
    return text


def format_as_table(columns: Sequence[str], rows: Sequence[Sequence]) -> str:
    widths = [len(c) for c in columns]
    formatted_rows = []
    for row in rows:
        formatted = [_format_cell(v) for v in row]
        formatted_rows.append(formatted)
        for i, cell in enumerate(formatted):
            widths[i] = max(widths[i], len(cell))

    def _line(cells):
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines = [_line(list(columns)), "-+-".join("-" * w for w in widths)]
    lines.extend(_line(r) for r in formatted_rows)
    return "\n".join(lines)


def rows_to_csv(columns: Sequence[str], rows: Sequence[Sequence]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")
