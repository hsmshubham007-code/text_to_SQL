"""Check whether golden answers match their reference SQL."""

import json
from pathlib import Path

from src.database_tools import run_sql


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "evals" / "golden_set.json"


def main():
    items = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    checked = 0
    passed = 0

    for item in items:
        if not item.get("answerable"):
            continue

        checked += 1
        expected = item.get("expected_answer")
        sql = item.get("expected_sql")

        try:
            actual = run_sql(sql)
            matches = (
                actual["columns"] == expected["columns"]
                and actual["rows"] == expected["rows"]
            )

            if matches:
                passed += 1
                status = "PASS"
            else:
                status = "FAIL"

            print(f"\n{item['id']} [{status}] {item['question']}")

            if not matches:
                print("Reference SQL:", sql)
                print("Expected:", expected)
                print("Actual:", {
                    "columns": actual["columns"],
                    "rows": actual["rows"],
                })

        except Exception as exc:
            print(f"\n{item['id']} [ERROR] {type(exc).__name__}: {exc}")

    print(f"\nGolden-set consistency: {passed}/{checked} passed")


if __name__ == "__main__":
    main()