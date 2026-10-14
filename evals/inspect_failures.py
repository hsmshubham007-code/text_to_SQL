"""Inspect failed evaluation cases without generating new SQL."""

import json
from pathlib import Path

from src.database_tools import run_sql


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "evals" / "evaluation_results.json"
GOLDEN = ROOT / "evals" / "golden_set.json"


def main():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    golden = {
        item["id"]: item
        for item in json.loads(GOLDEN.read_text(encoding="utf-8"))
    }

    failures = [
        item for item in report["results"]
        if item["status"] in {"FAIL", "ERROR"}
    ]

    print(f"Failed cases to inspect: {len(failures)}")

    for item in failures:
        question_id = item["id"]
        expected = golden[question_id]["expected_answer"]

        print(f"\n{'=' * 65}")
        print(f"{question_id}: {item['question']}")
        print(f"Status: {item['status']}")
        print(f"Category: {item.get('category')}")
        print(f"Expected SQL: {golden[question_id].get('expected_sql')}")
        print(f"Generated SQL: {item.get('generated_sql')}")

        if item.get("error"):
            print(f"Recorded error: {item['error']}")

        try:
            actual = run_sql(item["generated_sql"])
            columns_match = actual["columns"] == expected["columns"]
            rows_match = actual["rows"] == expected["rows"]

            print(f"Columns match: {columns_match}")
            print(f"Rows match: {rows_match}")
            print(f"Expected columns: {expected['columns']}")
            print(f"Actual columns:   {actual['columns']}")
            print(f"Expected rows: {expected['rows']}")
            print(f"Actual rows:   {actual['rows'][:5]}")

        except Exception as exc:
            print(f"SQL execution failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()