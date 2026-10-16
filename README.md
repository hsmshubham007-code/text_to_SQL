
# 🎵 Text-to-SQL Agent

A Python application that converts natural-language business questions into SQL queries for the Chinook SQLite music-store database using Groq, LangChain, SQLGlot, and Streamlit.

## Features

- Natural-language SQL generation using Groq
- Compact database schema and relationship context
- Six database tools for schema inspection, read-only querying, distinct-value lookup, and arithmetic
- SQLGlot validation before execution
- Read-only SQLite connections
- Automatic result limiting to 100 rows
- Five-second SQL execution timeout
- Query-risk classification and confirmation before potentially expensive queries
- SQL preview before execution
- Bounded SQL correction and retry logic in the agent workflow
- Refusals for configured unsupported question categories
- Streamlit UI displaying generated SQL and query results
- Automated tests for agent behavior, SQL safety, query guardrails, timeout handling, and prompt-injection scenarios
- A 35-question evaluation dataset: 30 answerable and 5 unanswerable questions

## Architecture Diagram

![Text-to-SQL Agent Architecture](docs/architecture.png)

The application generates SQL from a natural-language question, validates the SQL, and executes approved queries through a read-only SQLite connection.

## Requirements

- Python 3.12
- A Groq API key for live SQL generation
- Dependencies listed in `requirements.txt`

## Setup

Run these commands from the project root in PowerShell:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=qwen/qwen3.8-27b
```

Replace the placeholder with your own Groq API key. Never commit `.env` or expose your key.

The repository includes the Chinook database at `data/chinook.db`. Verify that it exists before running the application.

Live model requests require a valid Groq API key and available API quota. Automated regression tests should use mocks where possible and must not require live API calls.

## Run the Streamlit UI

From the project root, activate the virtual environment and run:

```powershell
python -m streamlit run .\app.py
```

Open the local URL displayed by Streamlit, usually `http://localhost:8501`.

1. Enter a business question.
2. Select **Generate SQL**.
3. Review the generated SQL.
4. If the query is classified as potentially expensive, review the warning.
5. Check the confirmation box and select **Confirm and execute**.
6. Review the executed SQL and returned rows.

The application requires explicit confirmation before executing a displayed query. The SQL is validated again immediately before execution.

The interface currently displays an execution summary and result table rather than a model-generated natural-language interpretation of the result.

## Architecture and important files

- `app.py` — Streamlit user interface
- `src/agent.py` — bounded tool-calling agent
- `src/agent_tools.py` — registered agent tools
- `src/sql_generator.py` — SQL generation, validation, and correction logic
- `src/sql_safety.py` — SQL validation and read-only execution safeguards
- `src/query_guardrails.py` — query-risk classification
- `src/database_tools.py` — database access helpers
- `src/inspect_schema.py` — schema inspection utility
- `data/chinook.db` — SQLite database
- `prompts/sql_generation.txt` — SQL-generation prompt
- `evals/` — evaluation scripts, golden set, and evaluation reports
- `tests/` — automated tests
- `docs/SCHEMA.md` — database schema documentation
- `docs/EVALUATION_RESULTS.md` — historical evaluation measurements and limitations
- `docs/TASK4_RESULTS.md` — Task 4 safety and UI verification report

## Safety controls

The application applies multiple safeguards:

- Only validated, read-only SQL is accepted.
- Destructive SQL and multiple SQL statements are rejected.
- Results are capped at 100 rows.
- Query execution has a configured five-second timeout.
- Potentially expensive queries require user confirmation.
- SQL is validated again immediately before execution.

The query-risk classifier uses SQL structure as a heuristic; it is not a database query planner and does not estimate actual execution cost. The timeout, row limit, read-only connection, and SQL validation remain necessary regardless of classification.

Prompt-injection regression tests simulate malicious model output and verify that destructive SQL is rejected. These offline tests do not establish immunity to every prompt-injection technique.

## Run tests

Activate the project virtual environment, then run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m pytest -q
```

Run focused Task 4 guardrail tests:

```powershell
python -m pytest .\tests\test_query_guardrails.py .\tests\test_sql_timeout.py .\tests\test_sql_safety.py .\tests\test_read_only_execution.py .\tests\test_prompt_injection.py -q
```

The recorded focused Task 4 test run passed all 46 tests. Run the complete test suite again after the final changes to establish the current overall result.

## Evaluation status

The evaluation dataset contains 30 answerable questions and 5 unanswerable questions.

Historical evaluation attempts included an initial run that passed 11 of 30 answerable questions (36.67%) and correctly refused all 5 unanswerable questions. Another incomplete run passed 8 questions, recorded 1 incorrect result, and encountered 21 API errors caused by Groq token-per-day limits.

A later complete recorded evaluation passed all 30 answerable questions and correctly refused all 5 unanswerable questions. These measurements apply to the recorded dataset and do not guarantee accuracy on new questions.

See `docs/EVALUATION_RESULTS.md` for historical results, failed attempts, and limitations.

## Limitations

- SQL generation depends on Groq availability and quota.
- Query-risk classification is heuristic and may misclassify expensive queries.
- A timeout and row limit do not guarantee low resource usage for every query.
- Prompt-injection regression tests cover selected simulated cases, not every possible attack.
- The current UI provides an execution summary rather than an LLM-generated explanation of returned data.
- Local UI and test verification do not constitute a production deployment or independent security audit.
