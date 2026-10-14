"""Tests for database inspection and query tools."""

import pytest

from src.database_tools import get_table_schema, list_tables, run_sql


def test_lists_database_tables():
    tables = list_tables()

    assert len(tables) == 11
    assert "Customer" in tables
    assert "Invoice" in tables
    assert "Track" in tables


def test_inspects_table_columns():
    schema = get_table_schema("Customer")
    column_names = [column["name"] for column in schema["columns"]]

    assert schema["table"] == "Customer"
    assert "CustomerId" in column_names
    assert "FirstName" in column_names
    assert "LastName" in column_names


def test_inspects_foreign_keys():
    schema = get_table_schema("Invoice")
    foreign_key_tables = [
        key["references_table"] for key in schema["foreign_keys"]
    ]

    assert "Customer" in foreign_key_tables


def test_rejects_unknown_table():
    with pytest.raises(ValueError, match="Unknown table"):
        get_table_schema("NotARealTable")


def test_runs_validated_sql():
    result = run_sql("SELECT COUNT(*) AS total FROM Customer")

    assert result["columns"] == ["total"]
    assert result["rows"] == [[59]]


def test_rejects_unsafe_sql():
    with pytest.raises(ValueError):
        run_sql("DELETE FROM Customer")