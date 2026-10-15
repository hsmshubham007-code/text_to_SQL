
"""Streamlit UI for the read-only Text-to-SQL agent."""

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.agent import ask_agent


load_dotenv()

st.set_page_config(
    page_title="Chinook Text-to-SQL Agent",
    page_icon="🎵",
    layout="wide",
)

st.title("🎵 Text-to-SQL Agent")
st.caption(
    "Ask questions about the Chinook music-store database "
    "using natural language."
)

with st.sidebar:
    st.header("Database safety")
    st.success("Read-only SQL execution")
    st.info("SQL validation is handled by the existing safety layer.")
    st.caption("Maximum result size: 100 rows")
    st.divider()
    st.caption("Model: " + os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"))

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
        "Ask database",
        type="primary",
        use_container_width=True,
    )

if submitted:
    if not question.strip():
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Analyzing your question and querying the database..."):
            try:
                result = ask_agent(question.strip())

                st.subheader("Answer")
                if result.get("supported") is False:
                    st.warning(result.get("answer", "This question is not supported."))
                else:
                    answer = result.get("answer")
                    if answer:
                        st.write(answer)
                    else:
                        st.info("The agent returned no natural-language answer.")

                sql = result.get("sql")
                st.subheader("Generated SQL")
                if sql:
                    st.code(sql, language="sql")
                else:
                    st.info("No SQL query was executed for this question.")

                columns = result.get("columns", [])
                rows = result.get("rows", [])

                st.subheader("Query results")
                if columns and rows:
                    if isinstance(rows[0], dict):
                        dataframe = pd.DataFrame(rows)
                    else:
                        dataframe = pd.DataFrame(rows, columns=columns)

                    st.dataframe(
                        dataframe,
                        use_container_width=True,
                        hide_index=True,
                    )
                elif result.get("refusal"):
                    st.caption("No database query was needed.")
                else:
                    st.info("The query returned no rows.")

                col1, col2 = st.columns(2)
                col1.metric("Rows returned", result.get("row_count", len(rows)))
                col2.metric("SQL execution attempts", result.get("attempts", 0))

                if result.get("limit_reached"):
                    st.warning(
                        "The agent reached its tool-call limit before finishing. "
                        "Try a more specific question."
                    )

            except Exception as error:
                st.error("The request could not be completed.")
                message = str(error)

                if "429" in message or "rate limit" in message.lower():
                    st.warning(
                        "The Groq API rate limit may have been reached. "
                        "Wait for the quota to reset before trying again."
                    )
                else:
                    st.caption(f"Error details: {message}")
