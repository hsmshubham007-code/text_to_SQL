"""Generate, validate, repair, and execute read-only SQL."""

import json
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq

def execute_sql_tool(sql: str) -> str:
    """Execute SQL through the registered read-only database tool."""
    return execute_readonly_sql.invoke({"sql": sql})

from src.agent_tools import execute_readonly_sql, get_database_overview
from src.sql_safety import validate_sql


load_dotenv()

DEFAULT_MODEL = "qwen/qwen3.8-27b"
MAX_SQL_ATTEMPTS = 2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = PROJECT_ROOT / "prompts" / "sql_generation.txt"


class UnsupportedQuestionError(ValueError):
    """Raised when the database cannot answer a question."""


UNSUPPORTED_TOPICS = {
    "inventory": (
        ("warehouse", "physical copies", "stock quantity", "inventory"),
        "The database has no warehouse inventory or stock quantity data.",
    ),
    "age": (
        ("customer's age", "customer age", "date of birth", "date-of-birth"),
        "The database has no customer date-of-birth data.",
    ),
    "satisfaction": (
        ("satisfaction score", "customer satisfaction", "survey score"),
        "The database has no customer satisfaction or survey score data.",
    ),
    "support_tickets": (
        ("support ticket", "support tickets", "unresolved ticket"),
        "The database has no support ticket records or ticket status data.",
    ),
    "marketing_roi": (
        ("marketing campaign", "campaign roi", "return on investment"),
        "The database has no marketing campaign cost or attribution data.",
    ),
    "weather": (
        ("weather", "forecast", "temperature on mars", "weather on mars"),
        "The Chinook database contains music-store data, not weather or planetary weather information.",
    ),
}


def unsupported_reason(question: str) -> str | None:
    """Detect requests for data known to be absent from this database."""
    text = question.casefold()

    for phrases, reason in UNSUPPORTED_TOPICS.values():
        if any(phrase in text for phrase in phrases):
            return reason

    return None


def build_compact_schema(tool_calls: list | None = None) -> str:
    """Get schema information through the registered overview tool."""
    entry = {
        "tool": "get_database_overview",
        "input": {},
    }

    try:
        raw_schema = get_database_overview.invoke({})
        overview = json.loads(raw_schema)
        entry["success"] = True
    except Exception as error:
        entry.update({"success": False, "error": str(error)})
        if tool_calls is not None:
            tool_calls.append(entry)
        raise

    if tool_calls is not None:
        tool_calls.append(entry)

    sections = []

    for table in overview["tables"]:
        schema = overview["schemas"][table]
        columns = []

        for column in schema["columns"]:
            description = column["name"]

            if column["type"]:
                description += f" {column['type']}"
            if column["primary_key"]:
                description += " PK"

            columns.append(description)

        section = f"{table}: " + ", ".join(columns)

        if schema["foreign_keys"]:
            relationships = [
                f"{key['column']} -> "
                f"{key['references_table']}.{key['references_column']}"
                for key in schema["foreign_keys"]
            ]
            section += "\n  Relationships: " + ", ".join(relationships)

        sections.append(section)

    return "\n".join(sections)


def load_sql_prompt(
    question: str,
    tool_calls: list | None = None,
) -> str:
    """Load the prompt and insert schema information from the schema tool."""
    if not PROMPT_PATH.is_file():
        raise FileNotFoundError(
            f"SQL generation prompt not found: {PROMPT_PATH}"
        )

    template = PROMPT_PATH.read_text(encoding="utf-8")

    return template.format(
        schema=build_compact_schema(tool_calls),
        question=question.strip(),
    )


def generate_sql(
    question: str,
    correction_error: str | None = None,
    previous_sql: str | None = None,
    tool_calls: list | None = None,
) -> str:
    """Generate SQL and validate it before returning it."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    reason = unsupported_reason(question)
    if reason:
        raise UnsupportedQuestionError(reason)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from your environment.")

    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", DEFAULT_MODEL),
        temperature=0,
        api_key=api_key,
    )

    prompt = load_sql_prompt(question, tool_calls)

    if correction_error:
        prompt += (
            "\n\nCORRECTION REQUIRED:\n"
            f"Previous SQL: {previous_sql or '(generation/validation failed)'}\n"
            f"Error: {correction_error}\n"
            "Correct the problem using only the provided schema. "
            "Return SQL only. Use one read-only SELECT query."
        )

    response = llm.invoke(prompt)
    sql = response.content

    if not isinstance(sql, str):
        raise ValueError("The model did not return SQL text.")

    sql = sql.strip()

    if sql.startswith("```"):
        lines = sql.splitlines()
        if lines and lines[-1].strip() == "```":
            sql = "\n".join(lines[1:-1]).strip()
        else:
            sql = "\n".join(lines[1:]).strip()

    return validate_sql(sql)


def ask_database(question: str) -> dict:
    """Generate, validate, and execute SQL with one bounded repair attempt."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    question = question.strip()
    reason = unsupported_reason(question)

    if reason:
        return {
            "question": question,
            "supported": False,
            "refusal": reason,
            "sql": None,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "attempts": 0,
            "tool_calls": [],
        }

    tool_calls = []
    last_error = None
    previous_sql = None

    for attempt in range(MAX_SQL_ATTEMPTS):
        try:
            sql = generate_sql(
                question,
                correction_error=str(last_error) if last_error else None,
                previous_sql=previous_sql,
                tool_calls=tool_calls,
            )

            # Validate again immediately before invoking the execution tool.
            sql = validate_sql(sql)
            previous_sql = sql

            entry = {
                "tool": "execute_readonly_sql",
                "input": {"sql": sql},
            }

            try:
                raw_result = execute_sql_tool(sql)
                result = json.loads(raw_result)
                entry["success"] = True
                tool_calls.append(entry)
            except Exception as error:
                entry.update({"success": False, "error": str(error)})
                tool_calls.append(entry)
                raise

            return {
                "question": question,
                "supported": True,
                "refusal": None,
                "sql": result["sql"],
                "columns": result["columns"],
                "rows": result["rows"],
                "row_count": result["row_count"],
                "attempts": attempt + 1,
                "tool_calls": tool_calls,
            }

        except UnsupportedQuestionError as error:
            return {
                "question": question,
                "supported": False,
                "refusal": str(error),
                "sql": None,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "attempts": attempt + 1,
                "tool_calls": tool_calls,
            }

        except (ValueError, sqlite3.Error) as error:
            last_error = error

    raise last_error