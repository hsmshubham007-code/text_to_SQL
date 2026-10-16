# Text-to-SQL Evaluation Results

## 1. Evaluation Setup

The project uses the Chinook SQLite database and a 35-question evaluation dataset:

- **30 answerable business questions**
- **5 unanswerable questions**

The dataset covers lookups, filters, joins, aggregations, rankings, and questions the database cannot answer. Reference SQL and the golden set are audited locally before model results are interpreted.

Offline audits and regression tests do not require Groq API calls. Full model evaluations do use the agent and may be affected by provider availability and rate limits.

## 2. Latest Recorded Evaluation

The latest preserved full evaluation is recorded in `evals/evaluation_results_latest.json`, dated October 16, 2026.

| Measurement | Latest recorded result |
|---|---:|
| Total questions | 35 |
| Answerable questions passed | 30/30 |
| Answerable accuracy | 100% |
| Correct unanswerable refusals | 5/5 |
| Failed records | 0 |
| Runtime/API errors | 0 |
| Elapsed time | 598.50 seconds |

All 35 questions were marked `PASS` in this recorded run. This is the latest recorded measurement, not a guarantee of future performance. The evaluation has not been rerun as part of the offline taxonomy and test checks described below.

## 3. Historical Evaluation Measurements

Earlier completed runs produced different results. They are preserved here for transparency and must not be treated as equivalent to the latest run.

| Artifact | Recorded time (UTC) | Answerable passed | Answerable accuracy | Correct refusals | Failed answerable cases |
|---|---|---:|---:|---:|---:|
| `evaluation_results.json` | 2026-10-14 08:05 | 11/30 | 36.67% | 5/5 | 19 |
| `evaluation_results_before_agent.json` | 2026-10-14 11:20 | 25/30 | 83.33% | 5/5 | 5 |
| `evaluation_results_latest.json` — latest recorded run | 2026-10-16 | 30/30 | 100% | 5/5 | 0 |

The historical timestamps above are taken from the saved report records. The October 16 result is the latest recorded evaluation; its detailed timestamp and measurements are available in the JSON artifact.

An earlier documentation table attributed results of 3/30 and 21/30 to intermediate runs. Those entries are not included in the table above because their artifact identities and measurements need to be reconciled against the raw JSON files before they can be reliably compared with the identified reports.

### Historical Groq rate-limit attempt

A separate incomplete evaluation recorded:

- 8 passed answerable questions
- 1 incorrect answer
- 21 API errors caused by Groq token-per-day rate limits

This was an incomplete run. Its apparent pass rate must not be reported as a completed benchmark accuracy measurement. API errors are not correct answers and should be reported separately.

## 4. Automated Failure Taxonomy

The offline script `evals/failure_taxonomy.py` classifies failures in two historical artifacts using reviewed root-cause labels. It writes the machine-readable output to `evals/failure_taxonomy.json`.

### Measured follow-up and remaining uncertainty

The saved evaluation artifacts show the following recorded results:

| Evaluation artifact | Answerable questions passed | Answerable accuracy | Unanswerable refusals passed | Recorded failures |
|---|---:|---:|---:|---:|
| `evaluation_results.json` | 11/30 | 36.67% | Not established by this row | 19 |
| `evaluation_results_before_agent.json` | 25/30 | 83.33% | Not established by this row | 5 |
| `evaluation_results_latest.json` | 30/30 | 100% | 5/5 | 0 |

The initial historical report identified output-contract mismatch as the largest reviewed failure category, accounting for 14 of its 19 failures. The latest saved full evaluation records 30/30 answerable questions passed, all 5 unanswerable questions correctly refused, and zero recorded failures.

These artifacts demonstrate improved recorded evaluation outcomes. They do not, by themselves, establish which individual code change caused the improvement. The historical reports are separate evaluation runs and should not be combined into one benchmark. The latest result is a saved result, not a new run performed during this documentation update.

### Historical run: `evaluation_results.json`

| Reviewed root cause | Count |
|---|---:|
| Output-contract mismatch | 14 |
| Ambiguous question or unspecified subset/tie-break | 4 |
| Wrong aggregation | 1 |
| **Total classified failures** | **19** |

### Historical run: `evaluation_results_before_agent.json`

| Reviewed root cause | Count |
|---|---:|
| Result-ordering mismatch | 3 |
| Output-contract mismatch | 1 |
| Ambiguous question or unspecified subset | 1 |
| **Total classified failures** | **5** |

These runs are reported separately because they represent different evaluation attempts. Their counts should not be added together as if they were one benchmark.

### What the categories mean

- **Output-contract mismatch:** returned column names, aliases, extra identifier columns, or column order differed from the reference output. Some historical cases had matching business values despite these differences.
- **Result-ordering mismatch:** the rows contained the expected information but were returned in a different order from the reference result.
- **Ambiguous question or unspecified subset:** a question requested a limited number of qualifying records without specifying a deterministic selection or tie-break rule.
- **Wrong aggregation:** the generated result did not include a required aggregate. Historical case Q025 omitted the requested track count from its output.

The classifications are reviewed explanations of the saved failures, not labels generated by the model. They are intended to distinguish SQL reasoning defects from benchmark comparison and question-definition issues.

### Required assignment categories

The assignment asks us to consider schema misunderstanding, wrong joins, wrong aggregation, hallucinated columns, and ambiguous questions.

The available historical diagnostics confirm one wrong-aggregation case and several ambiguity-related cases. They do **not** establish confirmed counts for schema misunderstanding, wrong joins, or hallucinated columns. Those categories should not be assigned merely to fill out the taxonomy. The current evidence supports the additional categories of output-contract mismatch and result-ordering mismatch.

## 5. Evaluation Method and Limitations

The current evaluator in `evals/evaluate_agent.py`:

1. Calls the agent for each question.
2. Validates generated SQL before accepting it for evaluation.
3. Executes the reference SQL against the local database.
4. Compares returned column names exactly.
5. Compares row values using a numeric tolerance.
6. Compares rows in their original order.
7. Records pass/fail status, error information, and failure categories.

Exact column-name comparison can flag aliases or extra columns even when some business values match. Order-sensitive row comparison can flag different row orders when the question does not specify an order.

These behaviors are limitations to account for when interpreting historical failures. They should not be silently ignored: extra columns, missing values, incorrect aggregates, and genuinely wrong rows can indicate real defects. Any change to comparison rules must be justified by the question's semantics and covered by regression tests.

The evaluation also depends on the correctness of the golden set and reference SQL. An inaccurate expected result can incorrectly mark a valid agent response as a failure.

## 6. Current Local Verification

Previously recorded project verification includes:

- **Final full test suite: 101 passed in 0.81 seconds**, verified after the latest documentation and test changes.
- **82 automated tests passed** using `python -m pytest -q`.
- The golden-set consistency audit passed all 30 checks.
- The reference SQL audit executed all 30 queries successfully.
- The reference SQL audit made no Groq API calls and modified no files.
- SQL validation, destructive-statement rejection, and read-only execution have automated test coverage.
- Agent recovery and unsupported-question refusal have focused regression coverage.
- A Streamlit smoke test verified an unsupported-question refusal.
- A supported Streamlit query displayed generated SQL and the expected five customer rows, independently checked against the database.

In the current evaluation-taxonomy work, the focused evaluator tests also passed:

```powershell
python -m pytest .\tests\test_evaluate_agent.py -q
```

Result: **8 passed in 0.59 seconds.**

The taxonomy script ran successfully against both historical JSON files, classified all 24 recorded failures, and made no model calls.

These verification results concern different checks and should not be conflated. In particular, passing offline tests does not establish that all possible live-generated SQL will be correct.

## 7. Reproducible Offline Checks

From the project root, with the virtual environment activated, run:

```powershell
python .\evals\failure_taxonomy.py
python -m pytest .\tests\test_evaluate_agent.py -q
python -m pytest -q
```

The first command regenerates the historical failure taxonomy from the saved reports. The second runs the focused evaluator tests. The third runs the full test suite.

**Do not run the full model evaluation merely to regenerate the taxonomy.** The evaluation script writes to `evals/evaluation_results_latest.json`; preserve the existing artifact before any future full evaluation.

## 8. Next Evaluation Procedure

When Groq quota is available and a new model evaluation is intentionally scheduled:

1. Preserve the existing evaluation artifact.
2. Run the full 35-question benchmark.
3. Check that all 30 answerable questions and all 5 unanswerable questions were evaluated.
4. Verify generated SQL, output columns, values, joins, filters, aggregations, and ranking behavior.
5. Separate incorrect answers from API errors and other runtime errors.
6. Record the run timestamp, accuracy, refusal performance, runtime, and failure categories.
7. Compare the new completed run with historical results.
8. Investigate and document every remaining failure category.

Do not count API errors as correct answers. Do not present an incomplete run as a completed benchmark.

## 9. Conclusion

The latest recorded full evaluation passed all 30 answerable questions and correctly refused all 5 unanswerable questions, for 35/35 passing cases in 598.50 seconds. The focused evaluator tests passed 8/8, and the historical taxonomy script successfully classified all failures in both reviewed reports without making model calls.

The historical analysis shows that output-contract mismatches and result-ordering differences accounted for many of the reviewed failures. These findings help prioritize future improvements, but they do not establish which code changes caused the latest improvement.

The evidence supports the tested behavior and the latest recorded benchmark result. It does not guarantee that every future natural-language question will produce correct SQL, and it is not sufficient on its own to describe the system as production-ready.