"""Generate and execute safe SQL from natural-language questions."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from src.database_tools import get_table_schema, list_tables, run_sql
from src.sql_safety import validate_sql


load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-20b"
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
}


def unsupported_reason(question: str) -> str | None:
    """Detect requests for data known to be absent from this database."""
    text = question.casefold()

    for phrases, reason in UNSUPPORTED_TOPICS.values():
        if any(phrase in text for phrase in phrases):
            return reason

    return None


def build_compact_schema() -> str:
    """Build a schema summary containing columns and relationships."""
    sections = []

    for table in list_tables():
        schema = get_table_schema(table)
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


def load_sql_prompt(question: str) -> str:
    """Load the external prompt and insert the schema and question."""
    if not PROMPT_PATH.is_file():
        raise FileNotFoundError(
            f"SQL generation prompt not found: {PROMPT_PATH}"
        )

    template = PROMPT_PATH.read_text(encoding="utf-8")

    return template.format(
        schema=build_compact_schema(),
        question=question.strip(),
    )


def generate_sql(question: str) -> str:
    """Generate one validated SELECT query using the external prompt."""
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

    prompt = load_sql_prompt(question)
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
    """Return a refusal or execute validated, read-only SQL."""
    try:
        sql = validate_sql(generate_sql(question))
    except UnsupportedQuestionError as error:
        return {
            "question": question,
            "supported": False,
            "refusal": str(error),
            "sql": None,
            "columns": [],
            "rows": [],
            "row_count": 0,
        }

    result = run_sql(sql)

    return {
        "question": question,
        "supported": True,
        "refusal": None,
        "sql": result["sql"],
        "columns": result["columns"],
        "rows": result["rows"],
        "row_count": result["row_count"],
    }