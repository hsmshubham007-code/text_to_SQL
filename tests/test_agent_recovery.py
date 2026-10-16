"""Verify SQL-agent recovery from three real SQLite execution errors."""

import json

import pytest

from src.sql_generator import ask_database


CASES = [
    (
        "List artists.",
        "SELECT MissingColumn FROM Artist LIMIT 5",
        "SELECT Name FROM Artist LIMIT 5",
        "MissingColumn",
    ),
    (
        "List artists.",
        "SELECT Name FROM MissingTable LIMIT 5",
        "SELECT Name FROM Artist LIMIT 5",
        "MissingTable",
    ),
    (
        "Count artists.",
        "SELECT COUNT(*) FROM Artist WHERE MissingColumn = 1 LIMIT 5",
        "SELECT COUNT(*) AS artist_count FROM Artist LIMIT 5",
        "MissingColumn",
    ),
]


@pytest.mark.parametrize(
    "question,broken_sql,repaired_sql,error_text",
    CASES,
    ids=["missing-column", "missing-table", "invalid-filter-column"],
)
def test_agent_recovers_from_database_errors(
    monkeypatch,
    question,
    broken_sql,
    repaired_sql,
    error_text,
):
    generated = iter([broken_sql, repaired_sql])
    prompts = []

    def fake_generate_sql(
        question,
        correction_error=None,
        previous_sql=None,
        tool_calls=None,
    ):
        prompts.append({
            "previous_sql": previous_sql,
            "correction_error": correction_error,
        })
        return next(generated)

    monkeypatch.setattr(
        "src.sql_generator.generate_sql",
        fake_generate_sql,
    )

    result = ask_database(question)

    assert result["supported"] is True
    assert result["attempts"] == 2
    assert result["sql"] == repaired_sql
    assert result["row_count"] >= 0

    failed_calls = [
        call for call in result["tool_calls"]
        if call.get("success") is False
    ]
    successful_calls = [
        call for call in result["tool_calls"]
        if call.get("success") is True
        and call.get("tool") == "execute_readonly_sql"
    ]

    assert len(failed_calls) == 1
    assert error_text in failed_calls[0]["error"]
    assert len(successful_calls) == 1
    assert successful_calls[0]["input"]["sql"] == repaired_sql

    assert prompts[1]["previous_sql"] == broken_sql
    assert error_text in prompts[1]["correction_error"]

    print(json.dumps({
        "question": question,
        "failed_sql": broken_sql,
        "database_error": failed_calls[0]["error"],
        "corrected_sql": repaired_sql,
        "attempts": result["attempts"],
        "recovered": True,
    }, indent=2))