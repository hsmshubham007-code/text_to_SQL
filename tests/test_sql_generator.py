"""Tests for the Text-to-SQL generation layer."""

import json
import sqlite3
from unittest.mock import patch

import pytest

from src.sql_generator import ask_database, build_compact_schema, generate_sql
from src.sql_safety import validate_sql


def tool_result(sql="SELECT Name FROM Artist LIMIT 5"):
    return json.dumps({
        "sql": sql,
        "columns": ["Name"],
        "rows": [["AC/DC"]],
        "row_count": 1,
    })


def test_compact_schema_includes_main_tables():
    schema = build_compact_schema()
    assert "Customer:" in schema
    assert "Invoice:" in schema
    assert "Track:" in schema


def test_compact_schema_includes_relationships():
    schema = build_compact_schema()
    assert "CustomerId -> Customer.CustomerId" in schema
    assert "InvoiceId -> Invoice.InvoiceId" in schema


def test_compact_schema_includes_primary_keys():
    assert "CustomerId INTEGER PK" in build_compact_schema()


def test_rejects_malformed_generated_sql():
    sql = (
        "SELECT Customer.CustomerId FROMCustomer JOIN Invoice "
        "ON Customer.CustomerId = Invoice.CustomerId"
    )
    with pytest.raises(ValueError, match="missing space after FROM"):
        validate_sql(sql)


def test_generate_sql_validates_model_output():
    class FakeResponse:
        content = "SELECT Customer.CustomerId FROMCustomer"

    class FakeModel:
        def invoke(self, prompt):
            return FakeResponse()

    with (
        patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}),
        patch("src.sql_generator.ChatGroq", return_value=FakeModel()),
    ):
        with pytest.raises(ValueError, match="missing space after FROM"):
            generate_sql("Which customers have invoices?")


def test_ask_database_never_executes_invalid_generated_sql():
    sql = "SELECT Customer.CustomerId FROMCustomer"
    with (
        patch("src.sql_generator.generate_sql", return_value=sql),
        patch("src.sql_generator.execute_sql_tool") as execute,
    ):
        with pytest.raises(ValueError, match="missing space after FROM"):
            ask_database("Which customers have invoices?")
    execute.assert_not_called()


@pytest.mark.parametrize(
    "question",
    [
        "How many copies are in warehouse inventory?",
        "What is the customer's age?",
        "What is the customer satisfaction score?",
        "How many unresolved support tickets are there?",
        "What is the marketing campaign ROI?",
        "What is the weather on Mars?",
    ],
)
def test_unsupported_questions_are_refused_without_model_call(question):
    from src.sql_generator import UnsupportedQuestionError

    with patch("src.sql_generator.ChatGroq") as model:
        with pytest.raises(UnsupportedQuestionError):
            generate_sql(question)
    model.assert_not_called()


@pytest.mark.parametrize(
    "question",
    [
        "How many customers are in the database?",
        "Which five customers have the most invoices?",
        "Show five tracks priced at 99 cents.",
    ],
)
def test_supported_question_types_are_not_marked_unsupported(question):
    from src.sql_generator import unsupported_reason
    assert unsupported_reason(question) is None


def test_repairs_sql_after_validation_error():
    valid_sql = "SELECT Name FROM Artist LIMIT 5"

    with (
        patch(
            "src.sql_generator.generate_sql",
            side_effect=[ValueError("Invalid SQL syntax."), valid_sql],
        ) as generate,
        patch(
            "src.sql_generator.execute_sql_tool",
            return_value=tool_result(valid_sql),
        ) as execute,
    ):
        answer = ask_database("List five artists.")

    assert answer["supported"] is True
    assert answer["attempts"] == 2
    assert generate.call_count == 2
    assert "Invalid SQL syntax." in generate.call_args.kwargs["correction_error"]
    execute.assert_called_once()


def test_self_correction_stops_after_maximum_attempts():
    from src.sql_generator import MAX_SQL_ATTEMPTS

    with (
        patch(
            "src.sql_generator.generate_sql",
            side_effect=ValueError("Invalid SQL syntax."),
        ) as generate,
        patch("src.sql_generator.execute_sql_tool") as execute,
    ):
        with pytest.raises(ValueError, match="Invalid SQL syntax"):
            ask_database("List five artists.")

    assert generate.call_count == MAX_SQL_ATTEMPTS
    execute.assert_not_called()


def test_repairs_sql_after_database_execution_error():
    first_sql = "SELECT MissingColumn FROM Artist LIMIT 5"
    repaired_sql = "SELECT Name FROM Artist LIMIT 5"

    with (
        patch(
            "src.sql_generator.generate_sql",
            side_effect=[first_sql, repaired_sql],
        ) as generate,
        patch(
            "src.sql_generator.execute_sql_tool",
            side_effect=[
                sqlite3.OperationalError("no such column: MissingColumn"),
                tool_result(repaired_sql),
            ],
        ) as execute,
    ):
        answer = ask_database("List five artists.")

    assert answer["supported"] is True
    assert answer["attempts"] == 2
    assert generate.call_count == 2
    assert "MissingColumn" in generate.call_args.kwargs["correction_error"]
    assert execute.call_count == 2


def test_unsafe_sql_is_never_executed_during_retries():
    with (
        patch(
            "src.sql_generator.generate_sql",
            return_value="DROP TABLE Artist",
        ) as generate,
        patch("src.sql_generator.execute_sql_tool") as execute,
    ):
        with pytest.raises(ValueError):
            ask_database("List five artists.")

    assert generate.call_count == 2
    execute.assert_not_called()