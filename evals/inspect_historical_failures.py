import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "evals" / "evaluation_results.json",
    ROOT / "evals" / "evaluation_results_before_agent.json",
]

for path in FILES:
    print(f"\n{'=' * 65}\n{path.name}\n{'=' * 65}")

    if not path.exists():
        print("File not found.")
        continue

    report = json.loads(path.read_text(encoding="utf-8"))

    print("Timestamp:", report.get("timestamp_utc"))
    print("Answerable summary:", report.get("answerable"))
    print("Unanswerable summary:", report.get("unanswerable"))
    print("Recorded failure counts:", report.get("failure_counts"))

    failures = [
        item for item in report.get("results", [])
        if item.get("status") in {"FAIL", "ERROR"}
    ]
    print("Failed cases:", len(failures))

    for item in failures:
        print(f"\n--- {item.get('id')} | {item.get('status')} ---")
        print("Question:", item.get("question"))
        print("Category:", item.get("failure_category", item.get("category")))
        print("Generated SQL:", item.get("generated_sql"))
        print("Error:", item.get("error"))
        print("Expected columns:", item.get("expected_columns"))
        print("Actual columns:", item.get("actual_columns"))
        print("Expected rows:", item.get("expected_rows"))
        print("Actual rows:", item.get("actual_rows"))