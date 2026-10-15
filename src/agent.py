"""Text-to-SQL agent backed by the validated SQL generation pipeline."""

from src.sql_generator import ask_database, unsupported_reason


SYSTEM_PROMPT = """
You are a precise Text-to-SQL assistant for the read-only Chinook SQLite
music-store database.

## Required workflow
1. Use database tools to answer the user's actual question.
2. Inspect the schema when necessary to confirm table names, columns,
   and relationships.
3. Execute SQL using execute_readonly_sql before presenting database results.
4. If execution returns an error, correct the SQL and retry within the
   available tool-call limit.
5. Base your answer only on the returned database results.
6. If the database cannot answer the question, explain the limitation.

## SQL correctness rules
- Use clear, lowercase snake_case aliases for descriptive output columns.
- For genre revenue, use Genre.Name AS genre and the revenue expression
  AS revenue.
- For media-type revenue, use MediaType.Name AS media_type and the revenue
  expression AS revenue.
- For genre revenue ties, sort by revenue descending and then genre name ascending to make the result deterministic.
- For currency aggregates that require two decimal places, use ROUND(expr, 2).
- For currency totals calculated from line items, use
  ROUND(SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity), 2).
- Generate one valid SQLite SELECT query or read-only CTE.
- Never attempt INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or PRAGMA.
- Select only the requested columns, in the requested order.
- Do not add unrelated IDs, emails, or other fields.
- Match expected output aliases when the question calls for named fields.
- For "first", "alphabetically", or similar requests, use the appropriate
  ORDER BY clause on the requested field.
- For a specific number of rows, use the requested LIMIT.
- For rankings, sort by the requested metric in the correct direction and
  use a deterministic secondary sort to break ties.
- Use explicit JOIN ... ON conditions and valid foreign-key relationships.
- Use GROUP BY and HAVING when required by aggregate queries.
- Do not add arbitrary LIMIT clauses when the question requests all results.
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

Follow these examples' output conventions:
- Select the required columns, not every available column.
- Preserve required aliases and column order.
- Apply requested sorting before limiting results.
- Round currency aggregates when required.
- Do not copy an example's LIMIT or sorting into unrelated questions.
"""


def ask_agent(question: str) -> dict:
    """Answer a business question through the safe SQL pipeline."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    question = question.strip()
    reason = unsupported_reason(question)

    if reason:
        return {
            "question": question,
            "answer": reason,
            "supported": False,
            "refusal": reason,
            "sql": None,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "attempts": 0,
            "tool_calls": [],
        }

    result = ask_database(question)

    if not result["supported"]:
        reason = result.get("refusal") or (
            "The database cannot answer this question."
        )
        return {
            **result,
            "answer": reason,
            "refusal": reason,
            "attempts": result.get("attempts", 0),
            "tool_calls": result.get("tool_calls", []),
        }

    return {
        **result,
        "answer": (
            "Query completed successfully and returned "
            f"{result['row_count']} row(s)."
        ),
        "attempts": result.get("attempts", 0),
        "tool_calls": result.get("tool_calls", []),
    }