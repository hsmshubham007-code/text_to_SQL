"""Tools for inspecting and querying the Chinook database."""

import sqlite3

from src.sql_safety import DATABASE_PATH, execute_sql


def list_tables() -> list[str]:
    """Return all user tables in the database."""
    with sqlite3.connect(
        DATABASE_PATH.resolve().as_uri() + "?mode=ro",
        uri=True,
    ) as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

    return [row[0] for row in rows]


def get_table_schema(table_name: str) -> dict:
    """Return a table's column definitions and foreign keys."""
    if table_name not in list_tables():
        raise ValueError(f"Unknown table: {table_name}")

    with sqlite3.connect(
        DATABASE_PATH.resolve().as_uri() + "?mode=ro",
        uri=True,
    ) as connection:
        columns = connection.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()

        foreign_keys = connection.execute(
            f'PRAGMA foreign_key_list("{table_name}")'
        ).fetchall()

    return {
        "table": table_name,
        "columns": [
            {
                "name": column[1],
                "type": column[2],
                "primary_key": bool(column[5]),
                "not_null": bool(column[3]),
            }
            for column in columns
        ],
        "foreign_keys": [
            {
                "column": key[3],
                "references_table": key[2],
                "references_column": key[4],
            }
            for key in foreign_keys
        ],
    }


def run_sql(sql: str) -> dict:
    """Execute SQL only through the validated read-only executor."""
    return execute_sql(sql)