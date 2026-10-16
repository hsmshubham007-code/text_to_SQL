"""Test recovery in the ChatGroq tool-calling agent without API calls."""

from langchain_core.messages import AIMessage

import src.agent as agent


def test_agent_recovers_after_sql_tool_error(monkeypatch):
    broken_sql = "SELECT Name FROM MissingTable LIMIT 5"
    repaired_sql = "SELECT Name FROM Artist LIMIT 5"

    responses = iter([
        AIMessage(
            content="",
            tool_calls=[{
                "name": "run_query",
                "args": {"sql": broken_sql},
                "id": "call-broken",
                "type": "tool_call",
            }],
        ),
        AIMessage(
            content="",
            tool_calls=[{
                "name": "run_query",
                "args": {"sql": repaired_sql},
                "id": "call-repaired",
                "type": "tool_call",
            }],
        ),
        AIMessage(content="Retrieved the artist records."),
    ])

    class FakeModel:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return next(responses)

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(
        agent,
        "ChatGroq",
        lambda **kwargs: FakeModel(),
    )

    result = agent.ask_agent("List artists.")

    assert result["supported"] is True
    assert result["attempts"] == 2
    assert result["sql"] == repaired_sql
    assert result["row_count"] > 0