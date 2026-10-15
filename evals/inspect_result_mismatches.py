"""Inspect row mismatches in selected evaluation results."""

import json
from pathlib import Path

path = Path(__file__).resolve().parent / "evaluation_results_latest.json"
report = json.loads(path.read_text(encoding="utf-8"))

for result in report["results"]:
    if result["id"] not in {"Q019", "Q030"}:
        continue

    expected = result["expected_rows"] or []
    actual = result["actual_rows"] or []

    print(f"\n{result['id']}: {result['question']}")
    print(f"Expected rows: {len(expected)}")
    print(f"Actual rows:   {len(actual)}")

    mismatch = next(
        (
            (index, expected_row, actual_row)
            for index, (expected_row, actual_row)
            in enumerate(zip(expected, actual))
            if expected_row != actual_row
        ),
        None,
    )

    if mismatch:
        index, expected_row, actual_row = mismatch
        print(f"First differing row (zero-based index {index}):")
        print("  Expected:", expected_row)
        print("  Actual:  ", actual_row)
    elif len(expected) != len(actual):
        print("Rows match in the shared range; row counts differ.")
    else:
        print("Rows match exactly.")

    print("Expected final rows:", expected[-2:])
    print("Actual final rows:  ", actual[-2:])