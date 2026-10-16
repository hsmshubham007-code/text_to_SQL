# Text-to-SQL Evaluation Results

## Evaluation setup

The project uses the Chinook SQLite database and a 35-question evaluation dataset:

- 30 answerable business questions
- 5 unanswerable questions

Reference SQL and the golden set are audited locally before interpreting model results. These offline audits do not require Groq API calls.

## Recorded model measurements

The following completed evaluation artifacts are preserved in `evals/`:

| Measurement | `evaluation_results_before_agent.json` | Earlier `evaluation_results_latest.json` | Latest recorded `evaluation_results_latest.json` |
|---|---:|---:|---:|
| Recorded time (UTC) | 2026-10-14 11:20 | 2026-10-14 12:04 | 2026-10-15 11:41 |
| Answerable questions | 30 | 30 | 30 |
| Passed answerable questions | 25 | 3 | 21 |
| Incorrect results | 5 | 27 | 2 |
| Runtime/API errors | 0 | 0 | 7 |
| Answerable accuracy | 83.33% | 10.00% | 70.00% |
| Correct unanswerable refusals | 5/5 | 5/5 | 5/5 |
| Elapsed time | 449.67 s | 865.71 s | 391.27 s |

The earlier artifacts recorded these failure categories:

- First run: `incorrect_result: 4`, `incorrect_columns: 1`
- Second run: `incorrect_columns: 26`, `incorrect_result: 1`
- Latest recorded run: `incorrect_columns: 2`, `error: 7`

A separate attempted run recorded 8 passed answerable questions, 1 incorrect result, and 21 API errors caused by Groq token-per-day rate limits. That attempt was incomplete; its 26.67% pass rate is not a valid full-run accuracy measurement.

An earlier report also recorded an 11/30 result (36.67%). Its corresponding raw artifact has not been identified in the JSON files inspected, so it should not be confused with the preserved measurements above.

A fresh full evaluation was completed on October 16, 2026, after the latest prompt and SQL-safety changes. All 30 answerable questions passed (100% accuracy), and all 5 unanswerable questions were correctly refused. The saved artifact contains 35 result records, no failed records, and zero runtime/API errors. The run took 598.50 seconds. This is the latest recorded evaluation; future model or environment changes may produce different results.

## Current local verification

Latest automated test result:

- **77 tests passed.**
- The golden-set consistency audit previously passed 30/30 checks.
- The reference SQL audit previously executed all 30 queries successfully.
- The reference SQL audit made zero Groq API calls and modified no files.
- SQL validation, destructive-statement rejection, and read-only execution are covered by automated tests.
- An agent regression test confirms that the unsupported question "What is the weather on Mars?" is refused without a Groq model call.
- The Streamlit UI was launched, and its unsupported-question refusal path was verified.
- A live supported question, "Show the first five customers alphabetically by last name," was successfully executed through the Streamlit UI.
- The UI displayed generated SQL and the expected five customer rows for that test.
- A direct read-only database check independently confirmed the expected columns, values, and ordering.

The local test result reflects the latest reported test run. The dataset audits and UI checks above are previously completed checks; rerun them if fresh verification is required. These checks verify implementation behavior and reference data, but they do not prove that generated SQL is always correct or establish overall live-query accuracy.

## Failed attempts and limitations

A subsequent full model-evaluation attempt encountered Groq HTTP 429 token-per-day rate-limit errors. It recorded 8 passed answerable questions, 1 incorrect result, and 21 API errors. Because the run was incomplete, its 26.67% pass rate is not a valid full-run accuracy measurement.

Historical completed runs produced inconsistent results: 25/30, 3/30, and 21/30 answerable questions passed in earlier evaluations. The latest full evaluation, completed October 16, 2026, passed 30/30 answerable questions and correctly refused all 5 unanswerable questions. The earlier results remain documented for transparency and comparison.

Local tests and offline audits verify implementation behavior and reference data, but they cannot guarantee correct SQL for arbitrary business questions. A passing safety test also does not guarantee that a generated query answers the user's question correctly.

The Streamlit checks verified an unsupported-question refusal and one successful supported query. A single successful example does not establish overall live-query accuracy.

## Next evaluation

When Groq quota is available:

1. Run the complete 30-question answerable evaluation and the 5-question refusal evaluation.
2. Verify generated SQL, returned columns, and result values against the database.
3. Check representative joins, aggregations, rankings, and filters.
4. Preserve the raw output from each run without losing historical artifacts.
5. Record completed questions, correct results, incorrect results, refusals, API errors, runtime, and pass rate.
6. Compare the completed run with the preserved historical runs and categorize remaining failures.

Do not count API errors as correct answers. Do not present an incomplete run as a completed benchmark, and do not describe a historical result as a measurement of the latest code.

## Conclusion

The latest reported local test suite passed 77 tests. Previously completed offline dataset audits passed their 30-check validations, and the Streamlit interface, unsupported-question refusal path, and one live supported query were verified.

The latest recorded model evaluation, timestamped October 16, 2026, passed 30/30 answerable questions (100%), correctly refused 5/5 unanswerable questions, and reported zero failures. The evaluation took 598.50 seconds. Results are recorded in evals/evaluation_results_latest.json. This is a successful full benchmark, although future model/API runs may produce different results.

The system should not be described as production-ready based on the available evidence.