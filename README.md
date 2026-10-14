# Text-to-SQL Agent

A Python application that converts natural-language questions into SQL queries for the Chinook SQLite database using Groq.

## Features

- Compact database schema and relationship context for SQL generation
- Groq-powered natural-language-to-SQL conversion
- SQLGlot validation before execution
- Read-only SQLite database access
- Query result limit of 100 rows
- Refusal for configured unsupported question categories
- Automated tests for SQL generation, validation, and database tools
- A 35-question evaluation dataset: 30 answerable and 5 unanswerable questions

## Requirements

- Python 3.12
- A Groq API key
- Dependencies listed in `requirements.txt`

## Setup

From the project root, activate the virtual environment and install dependencies:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a local `.env` file containing:

```text
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
```

Replace the placeholder with your own key. Never commit `.env` or expose your API key.

## Run the agent

Import `ask_database()` from `src.sql_generator` in your Python application. It generates SQL, validates the query, and executes supported queries against the Chinook database.

## Run tests

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest -q
```

## Evaluation status

The evaluation dataset contains 35 questions: 30 answerable questions and 5 unanswerable questions.

The initial recorded evaluation passed 11 of 30 answerable questions (36.67%) and correctly refused all 5 unanswerable questions. This is a baseline result, not a claim of production readiness.

A subsequent run passed 8 of 30 answerable questions, recorded 1 incorrect result, and encountered 21 API errors due to Groq token-per-day rate limits. This run is incomplete; its 26.67% pass rate must not be interpreted as a valid full-run accuracy score.

See `docs/EVALUATION_RESULTS.md` for the measurements, limitations, and failed evaluation attempt. Live model performance remains to be re-evaluated when API quota is available.

## Project structure

- `src/sql_generator.py` — SQL generation and orchestration
- `src/sql_safety.py` — SQL validation and read-only execution
- `src/database_tools.py` — schema inspection and query execution tools
- `src/inspect_schema.py` — schema inspection utility
- `docs/SCHEMA.md` — database schema documentation
- `data/chinook.db` — SQLite database
- `evals/questions.json` — evaluation questions and reference SQL
- `evals/golden_set.json` — expected evaluation results
- `evals/` — evaluation scripts, audits, and reports
- `tests/` — automated tests

## Safety

SQL is validated before execution. Only permitted query statements are accepted; destructive statements and multiple SQL statements are rejected. Queries execute through a read-only SQLite connection, and results are limited to 100 rows. These controls reduce risk but do not replace testing and review.

## Verification and limitations

Latest local verification completed:

- Automated tests: 48 passed
- Golden-set consistency audit: 30/30 passed
- Reference SQL execution audit: 30/30 answerable questions executed successfully
- SQL safety and read-only execution checks passed

**Live generation performance is not yet confirmed.** Groq rate limits interrupted the full evaluation. Rate-limited or incomplete runs should not be treated as final benchmark results. Re-run the full evaluation when API quota is available and document the resulting metrics, failures, and limitations.
