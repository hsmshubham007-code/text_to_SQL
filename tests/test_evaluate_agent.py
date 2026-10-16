"""Offline regression tests for Text-to-SQL evaluation."""

from evals.evaluate_agent import rows_equal, values_equal, evaluate_question
from unittest.mock import patch


def test_numeric_values_allow_small_floating_point_differences():
    assert values_equal(5.65, 5.6500001)


def test_numeric_values_reject_meaningful_differences():
    assert not values_equal(5.65, 5.66)


def test_non_numeric_values_must_match_exactly():
    assert values_equal("Metallica", "Metallica")
    assert not values_equal("Metallica", "metallica")


def test_rows_must_match_in_the_same_order():
    expected = [["Album A", "Artist A"], ["Album B", "Artist B"]]
    actual = [["Album B", "Artist B"], ["Album A", "Artist A"]]

    assert not rows_equal(expected, actual)


def test_rows_must_have_the_same_number_of_rows():
    assert not rows_equal([[1], [2]], [[1]])


def test_rows_must_have_the_same_number_of_columns():
    assert not rows_equal([[1, "Name"]], [[1, "Name", "Email"]])


def test_matching_rows_with_rounded_numeric_values_pass():
    expected = [[5.65]]
    actual = [[5.6500001]]

    assert rows_equal(expected, actual)


def test_malformed_generated_sql_cannot_pass_evaluation():
    item = {
        "id": "Q014",
        "question": "What is the average track length in minutes for each of the five longest-average genres?",
        "answerable": True,
        "expected_sql": "SELECT 1",
    }
    response = {
        "sql": (
            "SELECT Genre.Name AS genre FROM Genre "
            "ORDER BYaverage_minutes DESC LIMIT 5"
        ),
        "columns": ["genre", "average_minutes"],
        "rows": [
            ["Sci Fi & Fantasy", 48.53],
            ["Science Fiction", 43.76],
            ["Drama", 42.92],
            ["TV Shows", 35.75],
            ["Comedy", 26.42],
        ],
        "supported": True,
        "refusal": None,
    }

    with patch("evals.evaluate_agent.ask_agent", return_value=response):
        result = evaluate_question(item)

    assert result["status"] == "FAIL"
    assert result["failure_category"] == "invalid_sql"