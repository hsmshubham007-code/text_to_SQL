# Text-to-SQL Evaluation Results

## Evaluation setup

The project uses the Chinook SQLite database and a 35-question evaluation dataset: 30 answerable questions and 5 unanswerable questions. Reference SQL was audited locally before interpreting model results.

## Recorded measurements

| Measurement | Initial recorded run | Latest attempted run |
|---|---:|---:|
| Answerable questions | 30 | 30 |
| Passed answerable questions | 11 | 8 |
| Incorrect results | 19 | 1 |
| Runtime/API errors | 0 | 21 |
| Answerable pass rate | 36.67% | 26.67%* |
| Correct unanswerable refusals | 5/5 | 5/5 |

\* The latest pass rate is not a valid full-run accuracy measurement because 21 questions encountered API errors.

## Validation and safety checks

- Automated tests: 48 passed.
- Golden-set consistency audit: 30/30 passed.
- Reference SQL audit: 30/30 queries executed successfully.
- Reference SQL audit made no Groq API calls and modified no files.
- SQL validation and read-only execution are covered by automated tests, including destructive-statement rejection.

These checks verify the local test suite, dataset consistency, reference queries, and tested safety controls. They do not prove that generated SQL is always correct.

## Failed attempt and limitations

The latest full model evaluation was interrupted by Groq HTTP 429 token-per-day rate-limit errors. It recorded 21 errors, so the run cannot be compared fairly with a completed evaluation. The report is retained as diagnostic evidence and must not be treated as a valid full-run accuracy result.

The initial recorded run also shows substantial answerable-query failures. Incorrect output columns and result mismatches indicate that the agent still needs improvement. Correctly refusing all five unanswerable questions is encouraging but does not establish overall reliability.

## Next evaluation

When API quota is available, rerun the complete 30-answerable-question evaluation. Confirm that all questions finish without API errors, preserve the raw report, and compare accuracy and failure categories with the initial baseline. Do not overwrite historical results or count rate-limited questions as successful.

## Conclusion

Local tests and reference-query audits pass. However, answerable-query accuracy remains low in the recorded baseline, and a valid, completed follow-up model evaluation is still required. The system should not be described as production-ready based on these results.