"""Tests for the Text-to-SQL agent integration."""

from unittest.mock import patch

import pytest

from src.agent import ask_agent
from src.agent_tools import execute_readonly_sql


def test_rejects_empty_question():
    with pytest.raises(ValueError, match="cannot be empty"):
        ask_agent("   ")


@patch("src.agent.ask_database")
def test_returns_structured_answer(mock_ask_database):
    mock_ask_database.return_value = {
        "question": "How many artists are there?",
        "supported": True,
        "refusal": None,
        "sql": "SELECT COUNT(*) AS artist_count FROM Artist LIMIT 100",
        "columns": ["artist_count"],
        "rows": [[8]],
        "row_count": 1,
        "attempts": 1,
    }

    result = ask_agent("How many artists are there?")

    assert result["supported"] is True
    assert result["columns"] == ["artist_count"]
    assert result["rows"] == [[8]]
    assert result["row_count"] == 1
    assert result["attempts"] == 1
    assert result["sql"] is not None
    assert result["answer"]
    assert result["tool_calls"] == []
    mock_ask_database.assert_called_once_with(
        "How many artists are there?"
    )


@patch("src.agent.unsupported_reason", return_value=None)
@patch("src.agent.ask_database")
def test_preserves_generator_refusal(mock_ask_database, _mock_reason):
    reason = "The database does not contain weather data."
    mock_ask_database.return_value = {
        "question": "What is the weather on Mars?",
        "supported": False,
        "refusal": reason,
        "sql": None,
        "columns": [],
        "rows": [],
        "row_count": 0,
    }

    result = ask_agent("What is the weather on Mars?")

    assert result["supported"] is False
    assert result["refusal"] == reason
    assert result["answer"] == reason
    assert result["sql"] is None
    mock_ask_database.assert_called_once()


def test_unsupported_weather_question_does_not_call_generator():
    with patch("src.agent.ask_database") as mock_generator:
        result = ask_agent("What is the weather on Mars?")

    assert result["supported"] is False
    assert result["refusal"]
    assert result["sql"] is None
    mock_generator.assert_not_called()


def test_sql_tool_rejects_destructive_query():
    with pytest.raises(ValueError, match="Only read-only SELECT"):
        execute_readonly_sql.invoke({"sql": "DROP TABLE Artist"})