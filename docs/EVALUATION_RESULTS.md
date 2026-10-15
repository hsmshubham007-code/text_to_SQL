# Text-to-SQL Evaluation Results

## Evaluation setup

The project uses the Chinook SQLite database and a 35-question evaluation dataset:

- 30 answerable business questions
- 5 unanswerable questions

Reference SQL and the golden set are audited locally before interpreting model results. These offline audits do not require Groq API calls.

## Recorded model measurements

Two completed evaluation artifacts are preserved in `evals/`:

| Measurement | `evaluation_results_before_agent.json` | `evaluation_results_latest.json` |
|---|---:|---:|
| Recorded time (UTC) | 2026-10-14 11:20 | 2026-10-14 12:04 |
| Answerable questions | 30 | 30 |
| Passed answerable questions | 25 | 3 |
| Incorrect results | 5 | 27 |
| Runtime/API errors | 0 | 0 |
| Answerable accuracy | 83.33% | 10.00% |
| Correct unanswerable refusals | 5/5 | 5/5 |
| Elapsed time | 449.67 s | 865.71 s |

The failure categories recorded were `incorrect_result: 4` and `incorrect_columns: 1` in the earlier run, compared with `incorrect_columns: 26` and `incorrect_result: 1` in the later run.

A separate subsequent attempted run recorded 8 passed answerable questions, 1 incorrect result, and 21 API errors caused by Groq token-per-day rate limits. That attempt was incomplete; its 26.67% pass rate is not a valid full-run accuracy measurement.

An earlier report also recorded an 11/30 result (36.67%). Its corresponding raw artifact has not been identified in the two JSON files inspected here, so it should not be confused with either preserved run.

These measurements represent different runs and must not be combined or substituted for one another. The JSON artifacts are retained as historical evidence; recent prompt, agent, UI, and test changes have not been validated by a new complete model evaluation.

## Current local verification

Latest automated test result:

- **74 tests passed.**
- Golden-set consistency audit: 30/30 passed.
- Reference SQL audit: 30/30 queries executed successfully.
- The reference SQL audit made zero Groq API calls and modified no files.
- SQL validation, destructive-statement rejection, and read-only execution are covered by automated tests.
- An agent regression test confirms that the question "What is the weather on Mars?" is refused without a Groq model call.
- The Streamlit UI was launched, and its unsupported-question refusal path was verified.
- A live supported question, "Show the first five customers alphabetically by last name," was successfully executed through the Streamlit UI.
- The generated SQL included `ORDER BY LastName, FirstName LIMIT 5`, and the UI displayed the expected five customer rows.
- A direct read-only database check independently confirmed the column names, row values, and ordering.

These checks verify local behavior and reference data, including one successful live supported query. They do not prove that generated SQL is always correct or establish overall live-query accuracy.

## Failed attempt and limitations

A subsequent full model-evaluation attempt encountered Groq HTTP 429 token-per-day rate-limit errors. It recorded 8 passed answerable questions, 1 incorrect result, and 21 API errors. Because the run was incomplete, its 26.67% pass rate is not a valid full-run accuracy measurement.

The preserved completed runs also show inconsistent results: 25/30 answerable questions passed in the earlier artifact, compared with 3/30 in the later artifact. These results indicate that live SQL-generation accuracy is not yet reliable.

The local tests and offline audits verify implementation behavior and reference data, but they do not guarantee that generated SQL will be correct for arbitrary questions.

The Streamlit checks verified an unsupported-question refusal and one successful supported query. The supported query returned the expected five customers ordered by last name and first name. This single example does not establish overall live-query accuracy.

## Next evaluation

When Groq quota is available:

1. Repeat live supported-query checks for representative joins, aggregations, rankings, and filters.
2. Verify generated SQL, returned columns, and result values against the database.
3. Run the complete 30-question answerable evaluation and the 5-question refusal evaluation.
4. Preserve the raw output from each run.
5. Record completed questions, correct results, incorrect results, refusals, API errors, runtime, and pass rate.
6. Compare the completed run with the preserved historical runs and categorize remaining failures.

Do not count API errors as correct answers. Do not overwrite the historical baseline or present an incomplete run as a completed benchmark.

## Conclusion

The current local test suite passes 74 tests, and both offline dataset audits pass all 30 checks. The Streamlit interface, unsupported-question refusal path, and one live supported query have been verified.

However, recorded evaluation results vary substantially, and the latest attempted full evaluation was interrupted by API limits. Overall live SQL-generation accuracy remains unverified. The system should not be described as production-ready based on the available evidence.