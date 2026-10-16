"""Validate and safely execute read-only SQLite queries."""

import re
import sqlite3
import time
from pathlib import Path

import sqlglot
from sqlglot import exp


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "chinook.db"
MAX_ROWS = 100
QUERY_TIMEOUT_SECONDS = 5


def validate_sql(sql: str) -> str:
    """Allow one read-only query and enforce a maximum result size."""
    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty.")

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
    """Execute validated SQL read-only with a row cap and time limit."""
    safe_sql = validate_sql(sql)
    timeout = QUERY_TIMEOUT_SECONDS
    deadline = time.monotonic() + timeout
    timed_out = False

    def check_deadline() -> int:
        nonlocal timed_out

        if time.monotonic() >= deadline:
            timed_out = True
            return 1

        return 0

    database_uri = DATABASE_PATH.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(database_uri, uri=True) as connection:
        connection.set_progress_handler(check_deadline, 1000)

        try:
            # Check immediately so even a short query cannot bypass
            # an already-expired deadline.
            if check_deadline():
                raise TimeoutError(
                    f"SQL query exceeded the {timeout}-second timeout."
                )

            cursor = connection.execute(safe_sql)
            columns = [column[0] for column in cursor.description]
            rows = [list(row) for row in cursor.fetchall()]

        except sqlite3.OperationalError as exc:
            if timed_out:
                raise TimeoutError(
                    f"SQL query exceeded the {timeout}-second timeout."
                ) from exc
            raise

        finally:
            connection.set_progress_handler(None, 0)

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "sql": safe_sql,
    }