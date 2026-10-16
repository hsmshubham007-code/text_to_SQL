
"""Classify reviewed historical Text-to-SQL failures without API calls."""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evals" / "failure_taxonomy.json"

CLASSIFICATIONS = {
    "evaluation_results.json": {
        "Q004": ("output_contract_mismatch", "Extra ID column and differing output names."),
        "Q007": ("ambiguous_question", "Five matching tracks requested without defining which five."),
        "Q010": ("output_contract_mismatch", "Revenue alias differs; both result sets are empty."),
        "Q011": ("output_contract_mismatch", "Revenue values match, but column names differ."),
        "Q012": ("output_contract_mismatch", "Genre values and counts match; genre alias differs."),
        "Q013": ("output_contract_mismatch", "Correct top artists and counts, but extra ID and different alias."),
        "Q014": ("output_contract_mismatch", "Values match, but output column names differ."),
        "Q015": ("output_contract_mismatch", "Correct top artists and revenue, but an extra ID column."),
        "Q016": ("ambiguous_question", "Five qualifying tracks requested without defining which five."),
        "Q018": ("output_contract_mismatch", "Correct tracks and counts, but extra ID and different aliases."),
        "Q019": ("output_contract_mismatch", "Column names and genre labels differ; a zero-revenue row also differs."),
        "Q020": ("output_contract_mismatch", "First/last name columns are reversed and ordering differs."),
        "Q021": ("output_contract_mismatch", "Year values and counts match; year alias differs."),
        "Q023": ("output_contract_mismatch", "Correct tracks and prices, but an extra ID column."),
        "Q024": ("output_contract_mismatch", "Correct playlist counts, but extra ID and different output names."),
        "Q025": ("wrong_aggregation", "The query omits the required track count from its output."),
        "Q026": ("output_contract_mismatch", "Customer spending values match, but the aggregate alias differs."),
        "Q027": ("ambiguous_question", "Five qualifying tracks requested without defining which five."),
        "Q029": ("ambiguous_question", "Several customers tie at seven invoices; tie-breaking is unspecified."),
    },
    "evaluation_results_before_agent.json": {
        "Q006": ("result_ordering_mismatch", "Correct Canadian customers, but row order differs."),
        "Q015": ("output_contract_mismatch", "Artist and revenue values match; the revenue alias differs."),
        "Q016": ("ambiguous_question", "Five qualifying tracks requested without defining which five."),
        "Q020": ("result_ordering_mismatch", "Employee counts match, but row order differs."),
        "Q026": ("result_ordering_mismatch", "Customer spending values match, but row order differs."),
    },
}

REQUIRED_CATEGORIES = {
    "schema_misunderstanding",
    "wrong_join",
    "wrong_aggregation",
    "hallucinated_column",
    "ambiguous_question",
}

ADDITIONAL_CATEGORIES = {
    "output_contract_mismatch",
    "result_ordering_mismatch",
}


def main():
    reports = []
    errors = []

    for filename, classifications in CLASSIFICATIONS.items():
        path = ROOT / "evals" / filename

        if not path.exists():
            errors.append(f"Missing historical report: {filename}")
            continue

        report = json.loads(path.read_text(encoding="utf-8"))
        failures = [
            item for item in report.get("results", [])
            if item.get("status") in {"FAIL", "ERROR"}
        ]

        actual_ids = {item.get("id") for item in failures}
        classified_ids = set(classifications)

        if actual_ids != classified_ids:
            errors.append(
                f"{filename}: missing classifications "
                f"{sorted(actual_ids - classified_ids)}; "
                f"stale classifications {sorted(classified_ids - actual_ids)}"
            )
            continue

        counts = Counter()
        details = []

        for item in failures:
            category, rationale = classifications[item["id"]]
            counts[category] += 1
            details.append({
                "id": item["id"],
                "question": item.get("question"),
                "status": item.get("status"),
                "recorded_failure": item.get("failure_category"),
                "root_cause": category,
                "rationale": rationale,
                "generated_sql": item.get("generated_sql"),
                "expected_columns": item.get("expected_columns"),
                "actual_columns": item.get("actual_columns"),
                "expected_rows": item.get("expected_rows"),
                "actual_rows": item.get("actual_rows"),
            })

        reports.append({
            "file": filename,
            "timestamp_utc": report.get("timestamp_utc"),
            "answerable_accuracy": report.get("answerable", {}).get("accuracy"),
            "failed_cases": len(failures),
            "recorded_failure_counts": report.get("failure_counts", {}),
            "root_cause_counts": dict(sorted(counts.items())),
            "classifications": details,
        })

    if errors:
        raise SystemExit("\n".join(errors))

    observed = {
        category
        for report in reports
        for category in report["root_cause_counts"]
    }

    result = {
        "method": (
            "Manually reviewed root-cause classifications based on saved "
            "historical diagnostics. Counts are generated from source JSON."
        ),
        "required_assignment_categories": sorted(REQUIRED_CATEGORIES),
        "additional_categories": sorted(ADDITIONAL_CATEGORIES),
        "categories_with_zero_observed_cases": sorted(
            REQUIRED_CATEGORIES - observed
        ),
        "reports": reports,
    }

    OUTPUT.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("Failure taxonomy created:", OUTPUT.relative_to(ROOT))
    for report in reports:
        print(f"\n{report['file']}")
        print("Failed cases classified:", report["failed_cases"])
        print("Root-cause counts:", report["root_cause_counts"])

    print("\nAll historical failures have a classification.")
    print("No model calls were made.")


if __name__ == "__main__":
    main()
