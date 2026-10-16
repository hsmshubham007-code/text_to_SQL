"""Offline tests for expensive-query confirmation and SQL guardrails."""

import pytest

from src.query_guardrails import requires_confirmation
from src.sql_safety import validate_sql


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT * FROM Track LIMIT 5", False),
        ("SELECT * FROM Customer WHERE CustomerId = 1 LIMIT 1", False),
        ("SELECT GenreId, COUNT(*) FROM Track GROUP BY GenreId", True),
        (
            "SELECT Artist.Name, COUNT(Album.AlbumId) "
            "FROM Artist "
            "JOIN Album ON Artist.ArtistId = Album.ArtistId "
            "JOIN Track ON Album.AlbumId = Track.AlbumId "
            "JOIN Genre ON Track.GenreId = Genre.GenreId "
            "LIMIT 20",
            True,
        ),
        (
            "SELECT * FROM Track WHERE AlbumId IN "
            "(SELECT AlbumId FROM Album) LIMIT 10",
            True,
        ),
    ],
)
def test_query_confirmation_classification(sql, expected):
    assert requires_confirmation(sql) is expected


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE Track",
        "DELETE FROM Track",
        "UPDATE Track SET Name = 'injected'",
        "INSERT INTO Track (Name) VALUES ('injected')",
        "SELECT * FROM Track; DROP TABLE Track",
    ],
)
def test_injected_destructive_sql_is_rejected(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)


def test_row_limit_is_enforced():
    safe_sql = validate_sql("SELECT * FROM Track LIMIT 999999")
    assert "LIMIT 100" in safe_sql.upper()


def test_confirmation_classifier_fails_closed_on_invalid_sql():
    assert requires_confirmation("not valid sql") is True