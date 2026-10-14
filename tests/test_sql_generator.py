"""Tests for the Text-to-SQL generation layer."""

from unittest.mock import patch

import pytest

from src.sql_generator import ask_database, build_compact_schema, generate_sql
from src.sql_safety import validate_sql


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
    schema = build_compact_schema()

    assert "CustomerId INTEGER PK" in schema


def test_rejects_malformed_generated_sql():
    malformed_sql = (
        "SELECT Customer.CustomerId, Customer.FirstName, "
        "Customer.LastName, COUNT(Invoice.InvoiceId) AS InvoiceCount "
        "FROMCustomer JOIN Invoice "
        "ON Customer.CustomerId = Invoice.CustomerId "
        "GROUP BY Customer.CustomerId, Customer.FirstName, "
        "Customer.LastName ORDER BY InvoiceCount DESC LIMIT 5"
    )

    with pytest.raises(ValueError, match="missing space after FROM"):
        validate_sql(malformed_sql)


def test_generate_sql_validates_model_output():
    malformed_sql = (
        "SELECT Customer.CustomerId FROMCustomer "
        "JOIN Invoice ON Customer.CustomerId = Invoice.CustomerId"
    )

    class FakeResponse:
        content = malformed_sql

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
    malformed_sql = (
        "SELECT Customer.CustomerId FROMCustomer "
        "JOIN Invoice ON Customer.CustomerId = Invoice.CustomerId"
    )

    with (
        patch("src.sql_generator.generate_sql", return_value=malformed_sql),
        patch("src.sql_generator.run_sql") as mock_run_sql,
    ):
        with pytest.raises(ValueError, match="missing space after FROM"):
            ask_database("Which customers have invoices?")

    mock_run_sql.assert_not_called()

@pytest.mark.parametrize(
    "question",
    [
        "How many copies are in warehouse inventory?",
        "What is the customer's age?",
        "What is the customer satisfaction score?",
        "How many unresolved support tickets are there?",
        "What is the marketing campaign ROI?",
    ],
)
def test_unsupported_questions_are_refused_without_model_call(question):
    with patch("src.sql_generator.ChatGroq") as mock_model:
        with pytest.raises(Exception) as error:
            generate_sql(question)

    from src.sql_generator import UnsupportedQuestionError

    assert isinstance(error.value, UnsupportedQuestionError)
    mock_model.assert_not_called()


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