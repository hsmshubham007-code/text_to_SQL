"""LangChain tools for safe, read-only Chinook database access."""

import json

from langchain_core.tools import tool

from src.database_tools import get_table_schema, list_tables, run_sql


@tool
def list_database_tables() -> str:
    """List all available tables in the Chinook database."""
    return json.dumps({"tables": list_tables()})


@tool
def inspect_database_table(table_name: str) -> str:
    """Inspect a table's columns, data types, primary key, and foreign keys."""
    return json.dumps(get_table_schema(table_name))


@tool
def get_database_overview() -> str:
    """Return all database table names and their schema information."""
    tables = list_tables()
    schemas = {
        table: get_table_schema(table)
        for table in tables
    }
    return json.dumps({"tables": tables, "schemas": schemas})


@tool
def execute_readonly_sql(sql: str) -> str:
    """Execute one validated, read-only SQL query and return its results."""
    return json.dumps(run_sql(sql))


DATABASE_TOOLS = [
    list_database_tables,
    inspect_database_table,
    get_database_overview,
    execute_readonly_sql,
]