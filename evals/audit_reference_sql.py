
"""Audit benchmark reference SQL without calling the LLM or changing files."""

import json
import sqlite3
from pathlib import Path

import sqlglot
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "evals" / "questions.json"
DATABASE_PATH = ROOT / "data" / "chinook.db"


def main():
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    database_uri = DATABASE_PATH.resolve().as_uri() + "?mode=ro"

    checked = 0
    passed = 0
    failures = []

    with sqlite3.connect(database_uri, uri=True) as connection:
        for item in questions:
            if not item.get("answerable"):
                continue

            checked += 1
            sql = item.get("expected_sql", "")

            try:
                statements = sqlglot.parse(sql, read="sqlite")

                if (
                    len(statements) != 1
                    or not isinstance(statements[0], exp.Select)
                ):
                    raise ValueError(
                        "Reference must contain exactly one SELECT query."
                    )

                cursor = connection.execute(sql)
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()

                passed += 1
                print(
                    f"[PASS] {item['id']}: "
                    f"{len(rows)} rows, columns={columns}"
                )

            except Exception as error:
                failures.append(item["id"])
                print(f"[FAIL] {item['id']}: {type(error).__name__}: {error}")
                print(f"       SQL: {sql}")

    print("\n" + "=" * 60)
    print("REFERENCE SQL AUDIT SUMMARY")
    print("=" * 60)
    print(f"Answerable references checked: {checked}")
    print(f"Executed successfully: {passed}")
    print(f"Failed: {len(failures)}")
    print(f"Failed question IDs: {', '.join(failures) or 'None'}")
    print("Groq API calls: 0")
    print("Files modified: none")


if __name__ == "__main__":
    main()
