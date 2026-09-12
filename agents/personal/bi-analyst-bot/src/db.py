from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pymssql


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool


@dataclass(frozen=True)
class TableInfo:
    schema: str
    name: str
    columns: List[ColumnInfo]
    primary_keys: List[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}"


def _schema_table_filter(
    allowed_schemas: Optional[List[str]],
    allowed_tables: Optional[List[Tuple[str, str]]],
    alias: str = "",
) -> Tuple[str, Tuple]:
    prefix = f"{alias}." if alias else ""
    clauses: List[str] = []
    params: list = []

    if allowed_schemas:
        placeholders = ", ".join(["%s"] * len(allowed_schemas))
        clauses.append(f"{prefix}TABLE_SCHEMA IN ({placeholders})")
        params.extend(allowed_schemas)

    if allowed_tables:
        pair_clause = " OR ".join(
            [f"({prefix}TABLE_SCHEMA = %s AND {prefix}TABLE_NAME = %s)"] * len(allowed_tables)
        )
        clauses.append(f"({pair_clause})")
        for schema, table in allowed_tables:
            params.extend([schema, table])

    where_sql = ("AND " + " AND ".join(clauses)) if clauses else ""
    return where_sql, tuple(params)


class Database:
    def __init__(self, server: str, port: int, database: str, user: str, password: str, timeout: int):
        self._server = server
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._timeout = timeout

    def _connect(self):
        return pymssql.connect(
            server=self._server,
            port=str(self._port),
            database=self._database,
            user=self._user,
            password=self._password,
            timeout=self._timeout,
            login_timeout=self._timeout,
        )

    def load_schema(
        self,
        allowed_schemas: Optional[List[str]] = None,
        allowed_tables: Optional[List[Tuple[str, str]]] = None,
    ) -> List[TableInfo]:
        columns_filter, columns_params = _schema_table_filter(allowed_schemas, allowed_tables)
        # The PRIMARY KEY query joins two INFORMATION_SCHEMA views that both have a
        # TABLE_SCHEMA/TABLE_NAME column, so the filter must be qualified with the
        # kcu. alias to avoid an "ambiguous column name" error from SQL Server.
        pk_filter, pk_params = _schema_table_filter(allowed_schemas, allowed_tables, alias="kcu")

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE 1 = 1 {columns_filter}
                ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
                """,
                columns_params,
            )
            columns_by_table: dict = {}
            for table_schema, table_name, column_name, data_type, is_nullable in cur.fetchall():
                key = (table_schema, table_name)
                columns_by_table.setdefault(key, []).append(
                    ColumnInfo(column_name, data_type, is_nullable == "YES")
                )

            cur.execute(
                f"""
                SELECT kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                    AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' {pk_filter}
                """,
                pk_params,
            )
            pks_by_table: dict = {}
            for table_schema, table_name, column_name in cur.fetchall():
                pks_by_table.setdefault((table_schema, table_name), []).append(column_name)

        tables = [
            TableInfo(schema=s, name=n, columns=cols, primary_keys=pks_by_table.get((s, n), []))
            for (s, n), cols in columns_by_table.items()
        ]
        tables.sort(key=lambda t: (t.schema, t.name))
        return tables

    def run_query(self, sql: str, max_rows: int) -> Tuple[List[str], List[tuple], bool]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(max_rows + 1)
            truncated = len(rows) > max_rows
            if truncated:
                rows = rows[:max_rows]
            return columns, rows, truncated


def format_schema(tables: List[TableInfo]) -> str:
    lines = []
    for t in tables:
        parts = []
        for c in t.columns:
            marker = " PK" if c.name in t.primary_keys else ""
            null_marker = "" if c.is_nullable else " NOT NULL"
            parts.append(f"{c.name} {c.data_type}{marker}{null_marker}")
        lines.append(f"{t.full_name}({', '.join(parts)})")
    return "\n".join(lines)
