"""Verify that database execution blocks writes and preserves the database."""

import sqlite3

import pytest

from src.database_tools import run_sql
from src.sql_safety import DATABASE_PATH


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM Customer",
        "UPDATE Customer SET CustomerId = CustomerId",
        "INSERT INTO Customer (CustomerId) VALUES (9999)",
        "DROP TABLE Customer",
        "CREATE TABLE safety_test (id INTEGER)",
        "ALTER TABLE Customer ADD COLUMN safety_test INTEGER",
    ],
)
def test_write_statements_are_rejected(sql):
    with pytest.raises(ValueError):
        run_sql(sql)


def test_database_is_unchanged_after_rejected_writes():
    uri = DATABASE_PATH.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(uri, uri=True) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM Customer"
        ).fetchone()[0]
        customer_table = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name = 'Customer'"
        ).fetchone()[0]
        integrity = connection.execute("PRAGMA quick_check").fetchone()[0]

    assert count == 59
    assert customer_table == 1
    assert integrity == "ok"


def test_read_query_still_works():
    result = run_sql("SELECT COUNT(*) AS customer_count FROM Customer")

    assert result["columns"] == ["customer_count"]
    assert result["rows"] == [[59]]