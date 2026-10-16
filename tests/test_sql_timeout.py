"""Offline tests for SQL execution timeouts."""

import pytest

import src.sql_safety as sql_safety


def test_expired_query_deadline_aborts_execution(monkeypatch):
    """A query that exceeds its deadline must not complete successfully."""
    monkeypatch.setattr(sql_safety, "QUERY_TIMEOUT_SECONDS", -1)

    sql = (
        "SELECT a.TrackId "
        "FROM Track AS a "
        "CROSS JOIN Track AS b "
        "CROSS JOIN Track AS c "
        "CROSS JOIN Track AS d "
        "LIMIT 100"
    )

    with pytest.raises(TimeoutError, match="timeout"):
        sql_safety.execute_sql(sql)