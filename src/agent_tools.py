"""Tools for inspecting and querying the Chinook database."""

import ast
import json
import operator

from langchain_core.tools import tool

from src.database_tools import (
    get_table_schema,
    list_tables,
    run_sql,
)


@tool
def list_database_tables() -> str:
    """List all tables available in the database."""
    return json.dumps(list_tables())


@tool
def inspect_schema(table_name: str) -> str:
    """Inspect a table's columns, types, primary keys, and foreign keys."""
    return json.dumps(get_table_schema(table_name))


@tool
def get_database_overview() -> str:
    """Return database table names and their schemas."""
    tables = list_tables()
    schemas = {
        table_name: get_table_schema(table_name)
        for table_name in tables
    }

    return json.dumps({
        "tables": tables,
        "schemas": schemas,
    })


@tool
def run_query(sql: str) -> str:
    """Validate and execute one read-only SQL query."""
    return json.dumps(run_sql(sql))


@tool
def get_distinct_values(
    table_name: str,
    column_name: str,
    limit: int = 20,
) -> str:
    """Get sample distinct values from a valid table column."""
    schema = get_table_schema(table_name)
    valid_columns = {column["name"] for column in schema["columns"]}

    if column_name not in valid_columns:
        raise ValueError(
            f"Unknown column {column_name!r} in table {table_name!r}."
        )

    if not 1 <= limit <= 50:
        raise ValueError("Limit must be between 1 and 50.")

    def quote_identifier(value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    table = quote_identifier(table_name)
    column = quote_identifier(column_name)

    sql = (
        f"SELECT DISTINCT {column} "
        f"FROM {table} "
        f"WHERE {column} IS NOT NULL "
        f"ORDER BY {column} "
        f"LIMIT {limit}"
    )
    return json.dumps(run_sql(sql))


_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _calculate_node(node):
    """Evaluate basic arithmetic without eval()."""
    if isinstance(node, ast.Expression):
        return _calculate_node(node.body)

    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        left = _calculate_node(node.left)
        right = _calculate_node(node.right)

        if isinstance(node.op, ast.Pow) and abs(right) > 12:
            raise ValueError("Exponent magnitude cannot exceed 12.")

        result = _ALLOWED_OPERATORS[type(node.op)](left, right)

        if abs(result) > 1e100:
            raise ValueError("Calculation result is too large.")

        return result

    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_calculate_node(node.operand))

    raise ValueError("Only basic numeric arithmetic is allowed.")


@tool
def calculate(expression: str) -> str:
    """Calculate a basic arithmetic expression."""
    try:
        result = _calculate_node(ast.parse(expression, mode="eval"))
    except (SyntaxError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"Invalid calculation: {exc}") from exc

    return str(result)


@tool
def inspect_database_table(table_name: str) -> str:
    """Compatibility tool for inspecting a database table."""
    return json.dumps(get_table_schema(table_name))


@tool
def execute_readonly_sql(sql: str) -> str:
    """Compatibility tool for validated, read-only SQL execution."""
    return json.dumps(run_sql(sql))


AGENT_TOOLS = [
    list_database_tables,
    inspect_schema,
    get_database_overview,
    run_query,
    get_distinct_values,
    calculate,
]