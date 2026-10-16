
"""Streamlit UI for the read-only Text-to-SQL agent."""

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.query_guardrails import requires_confirmation
from src.sql_generator import (
    UnsupportedQuestionError,
    execute_sql_tool,
    generate_sql,
)
from src.sql_safety import validate_sql

load_dotenv()

st.set_page_config(
    page_title="Chinook Text-to-SQL Agent",
    page_icon="🎵",
    layout="wide",
)

st.title("🎵 Text-to-SQL Agent")
st.caption("Ask business questions about the Chinook music-store database.")

st.sidebar.header("Database safety")
st.sidebar.success("Read-only SQL execution")
st.sidebar.info("SQL is validated before execution.")
st.sidebar.caption("Maximum result size: 100 rows")
st.sidebar.caption("Query timeout: 5 seconds")
st.sidebar.caption(f"Model: {os.getenv('GROQ_MODEL', 'qwen/qwen3.8-27b')}")

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "pending_sql" not in st.session_state:
    st.session_state.pending_sql = None
if "query_result" not in st.session_state:
    st.session_state.query_result = None
if "query_error" not in st.session_state:
    st.session_state.query_error = None

with st.form("question_form"):
    question = st.text_area(
        "Your business question",
        placeholder=(
            "Examples:\n"
            "• Which five customers have the most invoices?\n"
            "• What is the average invoice total?\n"
            "• How much revenue has each genre generated?"
        ),
        height=120,
    )
    submitted = st.form_submit_button(
        "Generate SQL",
        type="primary",
        use_container_width=True,
    )

if submitted:
    st.session_state.pending_question = None
    st.session_state.pending_sql = None
    st.session_state.query_result = None
    st.session_state.query_error = None

    if not question.strip():
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Generating and validating SQL..."):
            try:
                sql = generate_sql(question.strip())
                sql = validate_sql(sql)
                st.session_state.pending_question = question.strip()
                st.session_state.pending_sql = sql
            except UnsupportedQuestionError as error:
                st.warning(str(error))
            except Exception as error:
                st.error("SQL could not be generated or validated.")
                st.caption(str(error))

pending_sql = st.session_state.pending_sql
pending_question = st.session_state.pending_question

if pending_sql:
    st.subheader("Review generated SQL")
    st.code(pending_sql, language="sql")

    try:
        confirmation_required = requires_confirmation(pending_sql)
    except Exception:
        confirmation_required = True

    if confirmation_required:
        st.warning(
            "This query may be expensive. Review the SQL and confirm before "
            "execution. The query timeout and row limit still apply."
        )
    else:
        st.info("Review the SQL before running this query.")

    with st.form("execution_confirmation_form"):
        confirmed = st.checkbox(
            "I have reviewed the SQL and want to execute this query."
        )
        run_query = st.form_submit_button(
            "Confirm and execute",
            type="primary",
            use_container_width=True,
        )

    if run_query:
        if not confirmed:
            st.warning("Please confirm before executing the query.")
        else:
            with st.spinner("Executing validated read-only SQL..."):
                try:
                    # Validate again immediately before execution.
                    safe_sql = validate_sql(pending_sql)
                    raw_result = execute_sql_tool(safe_sql)
                    import json

                    result = json.loads(raw_result)
                    st.session_state.query_result = result
                    st.session_state.query_error = None
                    st.session_state.pending_sql = None
                except Exception as error:
                    st.session_state.query_error = str(error)

if st.session_state.query_error:
    st.error("The query could not be executed.")
    message = st.session_state.query_error
    if "timeout" in message.lower():
        st.warning("The query exceeded its execution time limit.")
    st.caption(message)

result = st.session_state.query_result

if result:
    st.subheader("Answer")
    st.write(
        f"The query completed successfully and returned "
        f"{result.get('row_count', 0)} row(s)."
    )

    st.subheader("Executed SQL")
    st.code(result.get("sql", ""), language="sql")

    st.subheader("Query results")
    columns = result.get("columns", [])
    rows = result.get("rows", [])

    if columns:
        if rows and isinstance(rows[0], dict):
            dataframe = pd.DataFrame(rows)
        else:
            dataframe = pd.DataFrame(rows, columns=columns)

        st.dataframe(dataframe, use_container_width=True, hide_index=True)
    else:
        st.info("The query returned no columns.")

    st.metric("Rows returned", result.get("row_count", len(rows)))
