"""Evaluate the Text-to-SQL agent against the golden question set."""

import json
import math
import sys
import time
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database_tools import run_sql
from src.sql_generator import ask_database


QUESTIONS_PATH = PROJECT_ROOT / "evals" / "questions.json"
OUTPUT_PATH = PROJECT_ROOT / "evals" / "evaluation_results_latest.json"


def values_equal(expected, actual):
    """Compare numeric values with tolerance; compare other values exactly."""
    if (
        isinstance(expected, Real)
        and not isinstance(expected, bool)
        and isinstance(actual, Real)
        and not isinstance(actual, bool)
    ):
        return math.isclose(
            expected,
            actual,
            rel_tol=1e-9,
            abs_tol=1e-6,
        )

    return expected == actual


def rows_equal(expected_rows, actual_rows):
    """Compare rows in order without hiding missing or extra rows."""
    if len(expected_rows) != len(actual_rows):
        return False

    for expected, actual in zip(expected_rows, actual_rows):
        if len(expected) != len(actual):
            return False

        if not all(
            values_equal(expected_value, actual_value)
            for expected_value, actual_value in zip(expected, actual)
        ):
            return False

    return True


def evaluate_question(item):
    """Compare an agent response with the expected query result."""
    result = {
        "id": item["id"],
        "question": item["question"],
        "answerable": item["answerable"],
        "status": "ERROR",
        "failure_category": None,
        "generated_sql": None,
        "expected_columns": None,
        "actual_columns": [],
        "expected_rows": None,
        "actual_rows": [],
        "error": None,
        "refusal": None,
    }

    try:
        response = ask_database(item["question"])
        result["generated_sql"] = response.get("sql")
        result["actual_columns"] = response.get("columns", [])
        result["actual_rows"] = response.get("rows", [])
        result["refusal"] = response.get("refusal")

        if not item["answerable"]:
            if not response.get("supported", True) and result["refusal"]:
                result["status"] = "PASS"
            else:
                result["status"] = "FAIL"
                result["failure_category"] = "refusal_failed"
            return result

        if not response.get("supported", True):
            result["status"] = "FAIL"
            result["failure_category"] = "unexpected_refusal"
            return result

        expected = run_sql(item["expected_sql"])
        result["expected_columns"] = expected["columns"]
        result["expected_rows"] = expected["rows"]

        if result["actual_columns"] != result["expected_columns"]:
            result["status"] = "FAIL"
            result["failure_category"] = "incorrect_columns"
        elif not rows_equal(
            result["expected_rows"],
            result["actual_rows"],
        ):
            result["status"] = "FAIL"
            result["failure_category"] = "incorrect_result"
        else:
            result["status"] = "PASS"

    except Exception as error:
        result["status"] = "ERROR"
        result["failure_category"] = "error"
        result["error"] = f"{type(error).__name__}: {error}"

    return result


def main():
    """Run all benchmark questions and save a new report."""
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    if len(questions) != 35:
        raise ValueError(
            f"Expected 35 benchmark questions, found {len(questions)}."
        )

    started = time.perf_counter()
    results = []

    print("=" * 65)
    print("TEXT-TO-SQL EVALUATION")
    print("=" * 65)
    print(f"Questions: {len(questions)}")
    print("Historical evaluation_results.json will not be overwritten.\n")

    for index, item in enumerate(questions, start=1):
        result = evaluate_question(item)
        results.append(result)

        print(
            f"[{index:02}/{len(questions)}] "
            f"{result['id']} {result['status']}: {result['question']}"
        )

        if result["failure_category"]:
            print(f"     Failure: {result['failure_category']}")
        if result["error"]:
            print(f"     Error: {result['error']}")

    elapsed = round(time.perf_counter() - started, 2)
    answerable = [r for r in results if r["answerable"]]
    unanswerable = [r for r in results if not r["answerable"]]

    passed_answerable = sum(r["status"] == "PASS" for r in answerable)
    passed_refusals = sum(r["status"] == "PASS" for r in unanswerable)

    failure_counts = {}
    for result in results:
        category = result["failure_category"]
        if category:
            failure_counts[category] = failure_counts.get(category, 0) + 1

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "questions_evaluated": len(results),
        "answerable": {
            "total": len(answerable),
            "passed": passed_answerable,
            "incorrect_results": sum(
                r["failure_category"] in {
                    "incorrect_columns",
                    "incorrect_result",
                    "unexpected_refusal",
                }
                for r in answerable
            ),
            "errors": sum(r["status"] == "ERROR" for r in answerable),
            "accuracy": round(
                passed_answerable / len(answerable), 4
            ) if answerable else 0,
        },
        "unanswerable": {
            "total": len(unanswerable),
            "refusal_passed": passed_refusals,
            "refusal_failed": len(unanswerable) - passed_refusals,
            "refusal_support_implemented": True,
        },
        "failure_counts": failure_counts,
        "elapsed_seconds": elapsed,
        "results": results,
    }

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n" + "=" * 65)
    print("EVALUATION SUMMARY")
    print("=" * 65)
    print(
        f"Answerable accuracy: {passed_answerable}/{len(answerable)} "
        f"({report['answerable']['accuracy']:.1%})"
    )
    print(f"Correct refusals: {passed_refusals}/{len(unanswerable)}")
    print(f"Failure categories: {failure_counts}")
    print(f"Elapsed: {elapsed:.2f} seconds")
    print(f"Results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()