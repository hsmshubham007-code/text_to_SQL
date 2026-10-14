"""Tests for SQL validation and read-only execution."""

import pytest

from src.sql_safety import execute_sql, validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM Customer",
        "SELECT COUNT(*) FROM Track",
        "WITH totals AS (SELECT Total FROM Invoice) SELECT * FROM totals",
        "SELECT Name FROM Genre UNION SELECT Name FROM Playlist",
    ],
)
def test_allows_read_only_queries(sql):
    safe_sql = validate_sql(sql)

    assert safe_sql
    assert "SELECT" in safe_sql.upper()


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM Customer",
        "UPDATE Customer SET City = 'London'",
        "INSERT INTO Genre (Name) VALUES ('Test')",
        "DROP TABLE Customer",
        "CREATE TABLE test_table (id INT)",
        "SELECT * FROM Customer; DROP TABLE Customer",
        "PRAGMA table_info(Customer)",
    ],
)
def test_rejects_unsafe_queries(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)


def test_adds_limit_to_query():
    safe_sql = validate_sql("SELECT * FROM Track")

    assert "LIMIT 100" in safe_sql.upper()


def test_caps_large_limit():
    safe_sql = validate_sql("SELECT * FROM Track LIMIT 5000")

    assert "LIMIT 100" in safe_sql.upper()


def test_preserves_smaller_limit():
    safe_sql = validate_sql("SELECT * FROM Track LIMIT 10")

    assert "LIMIT 10" in safe_sql.upper()


def test_rejects_multiple_statements():
    with pytest.raises(ValueError):
        validate_sql("SELECT * FROM Track; SELECT * FROM Album")


def test_executes_read_only_query():
    result = execute_sql("SELECT COUNT(*) AS total FROM Track")

    assert result["columns"] == ["total"]
    assert result["rows"] == [[3503]]
    assert result["row_count"] == 1
    assert "LIMIT 100" in result["sql"].upper()