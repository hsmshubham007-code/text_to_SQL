
"""Tests for the Text-to-SQL golden evaluation set."""

import json
import sqlite3
from pathlib import Path

import sqlglot
from sqlglot import exp

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "chinook.db"
GOLDEN_SET_PATH = PROJECT_ROOT / "evals" / "golden_set.json"


def load_golden_set():
    with GOLDEN_SET_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def test_question_counts_and_unique_ids():
    questions = load_golden_set()

    assert len(questions) == 35
    assert sum(q["answerable"] for q in questions) == 30
    assert sum(not q["answerable"] for q in questions) == 5
    assert len({q["id"] for q in questions}) == 35


def test_all_answerable_queries_match_saved_answers():
    questions = load_golden_set()
    connection = sqlite3.connect(
        DATABASE_PATH.resolve().as_uri() + "?mode=ro",
        uri=True,
    )

    try:
        for question in questions:
            if not question["answerable"]:
                continue

            sql = question["expected_sql"]
            statements = sqlglot.parse(sql, read="sqlite")

            assert len(statements) == 1, question["id"]
            assert isinstance(statements[0], exp.Select), question["id"]

            cursor = connection.execute(sql)
            actual = {
                "columns": [column[0] for column in cursor.description],
                "rows": [list(row) for row in cursor.fetchall()],
            }

            assert actual == question["expected_answer"], question["id"]
    finally:
        connection.close()


def test_unanswerable_questions_have_reasons():
    for question in load_golden_set():
        if question["answerable"]:
            continue

        assert question["expected_sql"] is None
        assert question["reason"].strip()
        assert question["expected_behavior"].strip()
        assert question["expected_answer"]["cannot_answer"] is True


def test_question_ids_are_complete():
    questions = load_golden_set()
    expected_ids = {f"Q{i:03d}" for i in range(1, 36)}

    assert {q["id"] for q in questions} == expected_ids
