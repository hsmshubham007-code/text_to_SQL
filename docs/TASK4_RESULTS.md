
# Task 4 Results — Text-to-SQL UI and Guardrails

## Objective

Provide a Streamlit interface that displays generated SQL, applies safety controls before execution, requires confirmation for potentially expensive queries, and documents prompt-injection testing.

## Implementation

- Added a Streamlit SQL-preview and execution-confirmation workflow.
- Added query-risk classification in `src/query_guardrails.py`.
- Preserved SQL validation, read-only SQLite execution, and the 100-row maximum.
- Added a five-second execution timeout in `src/sql_safety.py`.
- Added offline prompt-injection regression tests in `tests/test_prompt_injection.py`.
- Added regression coverage for query classification and timeout handling.

## Verification results

| Check | Recorded result |
|---|---|
| Query guardrails, SQL safety, read-only execution, timeout, and injection tests | 46 passed |
| Query-risk classifier smoke test | Passed |
| Streamlit startup | Passed |
| SQL preview before execution | Browser-verified |
| Confirmation required for classified expensive query | Browser-verified |
| Unchecked confirmation blocks execution | Browser-verified |
| Timeout deadline regression test | 1 passed |

The 46-test result is from the combined focused run. The complete project test suite must be run after final documentation and code changes to record the final overall test count.

## Prompt-injection tests

Five simulated injection questions were passed through the SQL-generation function while a mocked model returned destructive SQL. The validation layer rejected the generated SQL in each case. An additional destructive-SQL regression test also passed.

These are offline regression tests; they do not represent a live penetration test of the browser interface or prove protection against all prompt-injection attacks.

## Safety controls

The application validates SQL before execution, uses a read-only database connection, caps results at 100 rows, and enforces a configured five-second execution timeout. Potentially expensive queries are flagged using a heuristic and require confirmation.

The query-risk classifier is not a query-cost estimator. The UI revalidates SQL before execution. These safeguards reduce risk but do not guarantee that generated SQL is correct or inexpensive.

## Limitations and remaining verification

- The UI currently displays a generic execution summary and result table, not an LLM-generated interpretation of the returned data.
- The focused regression tests have passed, but the full test suite must be rerun after the final changes.
- Clean-clone reproducibility, hosted deployment, and independent security testing have not been established by these checks.

## Conclusion

The Task 4 UI and core safety changes have passed the recorded focused tests and manual browser checks. Final task completion remains conditional on a passing full test suite and verification that the repository documentation matches the delivered implementation.
