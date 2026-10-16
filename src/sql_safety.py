"""Validate and safely execute read-only SQLite queries."""

import re
import sqlite3
from pathlib import Path

import sqlglot
from sqlglot import exp


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "chinook.db"
MAX_ROWS = 100


def validate_sql(sql: str) -> str:
    """Allow one read-only query and enforce a maximum result size."""
    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty.")

    # Reject missing whitespace without rejecting the valid ASC keyword.
    if re.search(r"\bFROM(?=[A-Za-z_])", sql, re.IGNORECASE):
        raise ValueError("Invalid SQL syntax: missing space after FROM.")

    if re.search(r"\bAS(?!C\b)(?=[A-Za-z_])", sql, re.IGNORECASE):
        raise ValueError("Invalid SQL syntax: missing space after AS.")

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except sqlglot.errors.ParseError as exc:
        raise ValueError("Invalid SQL syntax.") from exc

    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Only one SQL statement is allowed.")

    query = statements[0]

    if not isinstance(query, (exp.Select, exp.Union)):
        raise ValueError("Only read-only SELECT queries are allowed.")

    if query.find(exp.Into):
        raise ValueError("SELECT INTO is not allowed.")

    forbidden = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Command,
    )
    if any(query.find(kind) for kind in forbidden):
        raise ValueError("SQL contains a forbidden operation.")

    limit = query.args.get("limit")

    if limit is None:
        query = query.limit(MAX_ROWS)
    else:
        limit_value = limit.expression

        if not isinstance(limit_value, exp.Literal) or not limit_value.is_int:
            raise ValueError("LIMIT must be a numeric integer.")

        if int(limit_value.this) > MAX_ROWS:
            query = query.limit(MAX_ROWS)

    return query.sql(dialect="sqlite")


def execute_sql(sql: str) -> dict:
    """Execute a validated query using a read-only SQLite connection."""
    safe_sql = validate_sql(sql)
    database_uri = DATABASE_PATH.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(database_uri, uri=True) as connection:
        cursor = connection.execute(safe_sql)
        columns = [column[0] for column in cursor.description]
        rows = [list(row) for row in cursor.fetchall()]

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "sql": safe_sql,
    }