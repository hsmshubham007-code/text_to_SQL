"""Tests for the model-driven Text-to-SQL agent."""

import json
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage

from src.agent import ask_agent
from src.agent_tools import execute_readonly_sql


class FakeTool:
    """Small deterministic tool for testing the agent loop."""

    def __init__(self, name, output=None, error=None):
        self.name = name
        self.output = output
        self.error = error
        self.inputs = []

    def invoke(self, arguments):
        self.inputs.append(arguments)

        if self.error:
            raise self.error

        return self.output


class FakeGroq:
    """Return predetermined model responses without network access."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.bound_tools = None

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        if not self.responses:
            raise AssertionError("The agent made an unexpected model call.")
        return self.responses.pop(0)


def tool_response(name, arguments, call_id="test-call"):
    """Build a model response requesting one tool call."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": arguments,
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def test_rejects_empty_question():
    with pytest.raises(ValueError, match="cannot be empty"):
        ask_agent("   ")


def test_returns_structured_answer_from_tool_result():
    sql = "SELECT COUNT(*) AS artist_count FROM Artist LIMIT 100"
    query_result = {
        "sql": sql,
        "columns": ["artist_count"],
        "rows": [[8]],
        "row_count": 1,
    }
    query_tool = FakeTool("run_query", output=json.dumps(query_result))
    responses = [
        tool_response("run_query", {"sql": sql}),
        AIMessage(content="There are 8 artists in the database."),
    ]
    fake_model = FakeGroq(responses)

    with (
        patch("src.agent.unsupported_reason", return_value=None),
        patch("src.agent.AGENT_TOOLS", [query_tool]),
        patch("src.agent.ChatGroq", return_value=fake_model),
        patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
    ):
        result = ask_agent("How many artists are there?")

    assert result["supported"] is True
    assert result["columns"] == ["artist_count"]
    assert result["rows"] == [[8]]
    assert result["row_count"] == 1
    assert result["attempts"] == 1
    assert result["sql"] == sql
    assert result["answer"] == "There are 8 artists in the database."
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["success"] is True
    assert query_tool.inputs == [{"sql": sql}]


def test_returns_refusal_when_no_query_succeeds():
    refusal = "The database cannot answer this question."
    fake_model = FakeGroq([AIMessage(content=refusal)])

    with (
        patch("src.agent.unsupported_reason", return_value=None),
        patch("src.agent.AGENT_TOOLS", []),
        patch("src.agent.ChatGroq", return_value=fake_model),
        patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
    ):
        result = ask_agent("Give me information unavailable in the database.")

    assert result["supported"] is False
    assert result["refusal"] == refusal
    assert result["answer"] == refusal
    assert result["sql"] is None
    assert result["rows"] == []


def test_unsupported_weather_question_does_not_call_model():
    with patch("src.agent.ChatGroq") as mock_groq:
        result = ask_agent("What is the weather on Mars?")

    assert result["supported"] is False
    assert result["refusal"]
    assert result["sql"] is None
    mock_groq.assert_not_called()


def test_tool_errors_are_returned_to_the_model_for_recovery():
    sql = "SELECT Name FROM Artist LIMIT 5"
    query_result = {
        "sql": sql,
        "columns": ["Name"],
        "rows": [["AC/DC"]],
        "row_count": 1,
    }
    query_tool = FakeTool(
        "run_query",
        error=ValueError("no such column: MissingColumn"),
    )

    # First response requests a query that fails. The second requests a
    # corrected query. The final response is returned after success.
    responses = [
        tool_response(
            "run_query",
            {"sql": "SELECT MissingColumn FROM Artist LIMIT 5"},
            "failed-query",
        ),
        tool_response(
            "run_query",
            {"sql": sql},
            "corrected-query",
        ),
        AIMessage(content="The query succeeded."),
    ]

    # The fake tool fails only on its first call.
    original_invoke = query_tool.invoke

    def invoke_with_one_failure(arguments):
        if len(query_tool.inputs) == 0:
            query_tool.inputs.append(arguments)
            raise ValueError("no such column: MissingColumn")

        query_tool.error = None
        return original_invoke(arguments)

    query_tool.invoke = invoke_with_one_failure
    query_tool.output = json.dumps(query_result)
    fake_model = FakeGroq(responses)

    with (
        patch("src.agent.unsupported_reason", return_value=None),
        patch("src.agent.AGENT_TOOLS", [query_tool]),
        patch("src.agent.ChatGroq", return_value=fake_model),
        patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
    ):
        result = ask_agent("List five artists.")

    assert result["supported"] is True
    assert result["sql"] == sql
    assert result["attempts"] == 2
    assert result["tool_calls"][0]["success"] is False
    assert "MissingColumn" in result["tool_calls"][0]["error"]
    assert result["tool_calls"][1]["success"] is True


def test_sql_tool_rejects_destructive_query():
    with pytest.raises(ValueError, match="Only read-only SELECT"):
        execute_readonly_sql.invoke({"sql": "DROP TABLE Artist"})