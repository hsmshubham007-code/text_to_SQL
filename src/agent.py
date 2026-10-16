"""Model-driven Text-to-SQL agent with bounded tool calling."""

import json
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq

from src.agent_tools import AGENT_TOOLS
from src.sql_generator import ask_database, unsupported_reason


load_dotenv()

MAX_AGENT_ITERATIONS = 8

SYSTEM_PROMPT = """
You are a precise Text-to-SQL agent for the read-only Chinook SQLite
music-store database.

## Required workflow

1. Use database tools to answer the user's actual question.
2. Use inspect_schema or get_database_overview when you need schema details.
3. Use get_distinct_values when a filter value is uncertain.
4. Use run_query to execute database SQL.
5. Use calculate for standalone arithmetic when useful.
6. If execution returns an error, treat it as an observation, correct the SQL,
   and retry within the available tool-call limit.
7. Never claim a query succeeded if execution returned an error.
8. Base database claims only on successful query results.
9. If the database cannot answer the question, explain the limitation.
10. Stop when you have enough evidence to answer in concise plain English.

## SQL correctness and safety rules

- Generate one valid SQLite SELECT query or read-only CTE at a time.
- Never attempt INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or PRAGMA.
- Use valid schema names and explicit JOIN ... ON conditions.
- Use correct foreign-key relationships.
- Select only the requested columns, in the requested order.
- Use lowercase snake_case aliases for descriptive and aggregate output columns.
- Match required output aliases when the question specifies them.
- For currency aggregates requiring two decimal places, use ROUND(expr, 2).
- For currency totals calculated from line items, use
  ROUND(SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity), 2).
- For genre revenue, use Genre.Name AS genre and the revenue expression
  AS revenue.
- For media-type revenue, use MediaType.Name AS media_type and the revenue
  expression AS revenue.
- For genre revenue ties, sort by revenue descending and then by genre name ascending to make the results deterministic.
- Apply requested sorting before LIMIT.
- Do not add arbitrary LIMIT clauses when the question requests all results.
- Use GROUP BY and HAVING when required by aggregate queries.
- For rankings, sort by the requested metric in the correct direction and
  use a deterministic secondary sort to break ties.
- Do not invent columns, values, or query results.
- Never claim a query succeeded if execution returned an error.

## SQL examples

Question: Show the first five customers alphabetically by last name.
SQL:
SELECT CustomerId, FirstName, LastName
FROM Customer
ORDER BY LastName, FirstName
LIMIT 5

Question: Show five albums and the artists who created them.
SQL:
SELECT Album.Title AS album, Artist.Name AS artist
FROM Album
JOIN Artist ON Album.ArtistId = Artist.ArtistId
ORDER BY Album.Title
LIMIT 5

Question: What is the average invoice total?
SQL:
SELECT ROUND(AVG(Invoice.Total), 2) AS average_invoice_total
FROM Invoice

Question: Show revenue by genre.
SQL:
SELECT Genre.Name AS genre,
       ROUND(SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity), 2) AS revenue
FROM Genre
JOIN Track ON Track.GenreId = Genre.GenreId
JOIN InvoiceLine ON InvoiceLine.TrackId = Track.TrackId
GROUP BY Genre.Name
ORDER BY revenue DESC, genre ASC

Question: Show revenue by media type.
SQL:
SELECT MediaType.Name AS media_type,
       ROUND(SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity), 2) AS revenue
FROM MediaType
JOIN Track ON Track.MediaTypeId = MediaType.MediaTypeId
JOIN InvoiceLine ON InvoiceLine.TrackId = Track.TrackId
GROUP BY MediaType.Name
ORDER BY revenue DESC, media_type ASC

Follow these examples' output conventions:
- Select the required columns, not every available column.
- Preserve required aliases and column order.
- Apply requested sorting before limiting results.
- Round currency aggregates when required.
- Do not copy an example's LIMIT or sorting into unrelated questions.
- Use run_query to execute SQL before answering.
- Correct failed SQL using the returned database error.
- Answer from actual query results, not assumed results.
"""


def _empty_result(
    question: str,
    answer: str,
    supported: bool = False,
    tool_calls: list | None = None,
    refusal: str | None = None,
    attempts: int = 0,
) -> dict:
    """Return the stable response structure used by the application."""
    return {
        "question": question,
        "answer": answer,
        "supported": supported,
        "refusal": refusal,
        "sql": None,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "attempts": attempts,
        "tool_calls": tool_calls or [],
    }


def ask_agent(question: str) -> dict:
    """Answer a business question using model-driven tool calls."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    question = question.strip()
    reason = unsupported_reason(question)

    if reason:
        return _empty_result(
            question,
            reason,
            refusal=reason,
        )

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from your environment.")

    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
        temperature=0,
        api_key=api_key,
    )
    model = llm.bind_tools(AGENT_TOOLS)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]
    tool_map = {registered_tool.name: registered_tool for registered_tool in AGENT_TOOLS}
    tool_calls = []
    last_query_result = None
    query_attempts = 0

    for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
        response = model.invoke(messages)
        messages.append(response)

        requested_tools = getattr(response, "tool_calls", None) or []

        if not requested_tools:
            answer = response.content
            if not isinstance(answer, str):
                answer = str(answer)

            if last_query_result is None:
                return _empty_result(
                    question,
                    answer.strip()
                    or "The agent could not obtain a successful query result.",
                    tool_calls=tool_calls,
                    refusal=answer.strip() or "No successful query result.",
                    attempts=query_attempts,
                )

            return {
                "question": question,
                "answer": answer.strip()
                or (
                    "Query completed successfully and returned "
                    f"{last_query_result['row_count']} row(s)."
                ),
                "supported": True,
                "refusal": None,
                "sql": last_query_result["sql"],
                "columns": last_query_result["columns"],
                "rows": last_query_result["rows"],
                "row_count": last_query_result["row_count"],
                "attempts": query_attempts,
                "tool_calls": tool_calls,
            }

        for requested in requested_tools:
            name = requested.get("name", "")
            arguments = requested.get("args") or {}
            call_id = requested.get("id", f"{iteration}-{name}")

            entry = {
                "iteration": iteration,
                "tool": name,
                "input": arguments,
            }

            registered_tool = tool_map.get(name)

            if registered_tool is None:
                error_message = f"Unknown tool requested: {name}"
                entry.update({
                    "success": False,
                    "error": error_message,
                })
                tool_calls.append(entry)
                messages.append(
                    ToolMessage(
                        content=error_message,
                        tool_call_id=call_id,
                    )
                )
                continue

            if name in {"run_query", "execute_readonly_sql"}:
                query_attempts += 1

            try:
                output = registered_tool.invoke(arguments)
                entry["success"] = True
                entry["output"] = output
                tool_calls.append(entry)

                if name in {"run_query", "execute_readonly_sql"}:
                    parsed_output = (
                        json.loads(output) if isinstance(output, str) else output
                    )
                    if isinstance(parsed_output, dict) and "sql" in parsed_output:
                        last_query_result = parsed_output
                    else:
                        entry["success"] = False
                        entry["error"] = (
                            "Query tool returned an unexpected result structure."
                        )
                        tool_calls[-1] = entry
                        last_query_result = None

                observation = (
                    output if isinstance(output, str) else json.dumps(output)
                )

            except Exception as error:
                observation = f"Tool error: {type(error).__name__}: {error}"
                entry.update({
                    "success": False,
                    "error": observation,
                })
                tool_calls.append(entry)

            # Return successful outputs and errors to the model as observations.
            messages.append(
                ToolMessage(
                    content=observation,
                    tool_call_id=call_id,
                )
            )

    if last_query_result is not None:
        return {
            "question": question,
            "answer": (
                "A query succeeded, but the agent reached its iteration limit "
                "before completing its final explanation."
            ),
            "supported": True,
            "refusal": None,
            "sql": last_query_result["sql"],
            "columns": last_query_result["columns"],
            "rows": last_query_result["rows"],
            "row_count": last_query_result["row_count"],
            "attempts": query_attempts,
            "tool_calls": tool_calls,
        }

    return _empty_result(
    question,
    "The agent reached its iteration limit without a successful query.",
    tool_calls=tool_calls,
    refusal="Agent iteration limit reached.",
    attempts=query_attempts,
)