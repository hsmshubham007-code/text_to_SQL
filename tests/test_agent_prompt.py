"""Offline regression tests for the active agent prompt."""

from src.agent import SYSTEM_PROMPT


def test_prompt_demonstrates_customer_columns_and_sorting():
    assert "SELECT CustomerId, FirstName, LastName" in SYSTEM_PROMPT
    assert "ORDER BY LastName, FirstName" in SYSTEM_PROMPT


def test_prompt_demonstrates_album_artist_aliases_and_join():
    assert "Album.Title AS album" in SYSTEM_PROMPT
    assert "Artist.Name AS artist" in SYSTEM_PROMPT
    assert "Album.ArtistId = Artist.ArtistId" in SYSTEM_PROMPT
    assert "ORDER BY Album.Title" in SYSTEM_PROMPT


def test_prompt_demonstrates_rounded_average_invoice_total():
    assert "ROUND(AVG(Invoice.Total), 2)" in SYSTEM_PROMPT
    assert "AS average_invoice_total" in SYSTEM_PROMPT


def test_prompt_requires_lowercase_aggregate_aliases():
    assert "lowercase snake_case aliases" in SYSTEM_PROMPT
    assert "Genre.Name AS genre" in SYSTEM_PROMPT
    assert "AS revenue" in SYSTEM_PROMPT
    assert "MediaType.Name AS media_type" in SYSTEM_PROMPT


def test_prompt_requires_deterministic_genre_revenue_ties():
    assert "genre name ascending" in SYSTEM_PROMPT
    assert "ORDER BY" in SYSTEM_PROMPT


def test_prompt_requires_rounded_line_item_revenue():
    assert "ROUND(SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity), 2)" in SYSTEM_PROMPT


def test_prompt_requires_execution_and_error_correction():
    assert "execute_readonly_sql" in SYSTEM_PROMPT
    assert "correct the SQL" in SYSTEM_PROMPT


def test_prompt_prohibits_destructive_sql():
    assert "Never attempt INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or PRAGMA" in SYSTEM_PROMPT