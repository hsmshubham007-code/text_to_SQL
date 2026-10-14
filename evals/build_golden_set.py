
"""Build verified expected answers for the Text-to-SQL evaluation set."""

import json
import sqlite3
from pathlib import Path

import sqlglot
from sqlglot import exp

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "chinook.db"
QUESTIONS_PATH = PROJECT_ROOT / "evals" / "questions.json"
OUTPUT_PATH = PROJECT_ROOT / "evals" / "golden_set.json"


def run_read_only_query(connection, sql):
    """Validate and execute one read-only SELECT query."""
    statements = sqlglot.parse(sql, read="sqlite")

    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError("Only one SELECT query is allowed.")

    cursor = connection.execute(sql)
    columns = [column[0] for column in cursor.description]
    rows = [list(row) for row in cursor.fetchall()]

    return {"columns": columns, "rows": rows}


def build_golden_set():
    with QUESTIONS_PATH.open("r", encoding="utf-8") as file:
        questions = json.load(file)

    if len(questions) != 35:
        raise ValueError(f"Expected 35 questions, found {len(questions)}.")

    answerable_count = sum(item["answerable"] for item in questions)
    unanswerable_count = len(questions) - answerable_count

    if answerable_count != 30 or unanswerable_count != 5:
        raise ValueError("Expected 30 answerable and 5 unanswerable questions.")

    if len({item["id"] for item in questions}) != len(questions):
        raise ValueError("Question IDs must be unique.")

    database_uri = DATABASE_PATH.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)
    results = []

    try:
        for item in questions:
            result = dict(item)

            if item["answerable"]:
                result["expected_answer"] = run_read_only_query(
                    connection, item["expected_sql"]
                )
            else:
                result["expected_answer"] = {
                    "cannot_answer": True,
                    "reason": item["reason"],
                    "expected_behavior": item["expected_behavior"],
                }

            results.append(result)
            print(f"Verified {item['id']}: {item['question']}")

    finally:
        connection.close()

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print("\nGolden set created successfully.")
    print(f"Total questions: {len(results)}")
    print(f"Answerable: {answerable_count}")
    print(f"Unanswerable: {unanswerable_count}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_golden_set()
