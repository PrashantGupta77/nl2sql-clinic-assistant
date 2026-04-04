import json
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.io as pio
import requests
import streamlit as st

st.set_page_config(
    page_title="Clinic NL2SQL Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
SAMPLE_QUESTIONS = [
    "How many patients do we have?",
    "List all doctors and their specializations",
    "Show me appointments for last month",
    "Which doctor has the most appointments?",
    "What is the total revenue?",
    "Show revenue by doctor",
    "How many cancelled appointments last quarter?",
    "Top 5 patients by spending",
    "Average treatment cost by specialization",
    "Show monthly appointment count for the past 6 months",
    "Which city has the most patients?",
    "List patients who visited more than 3 times",
    "Show unpaid invoices",
    "What percentage of appointments are no-shows?",
    "Show the busiest day of the week for appointments",
    "Revenue trend by month",
    "Average appointment duration by doctor",
    "List patients with overdue invoices",
    "Compare revenue between departments",
    "Show patient registration trend by month",
]


def init_session_state() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_response" not in st.session_state:
        st.session_state.last_response = None
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = DEFAULT_API_BASE_URL
    if "question_input" not in st.session_state:
        st.session_state.question_input = ""


def get_health(api_base_url: str) -> dict[str, Any]:
    response = requests.get(f"{api_base_url}/health", timeout=20)
    response.raise_for_status()
    return response.json()


def ask_question(api_base_url: str, question: str) -> dict[str, Any]:
    response = requests.post(
        f"{api_base_url}/chat",
        json={"question": question},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def add_to_history(question: str, response_data: dict[str, Any]) -> None:
    st.session_state.history.insert(
        0,
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "response": response_data,
        },
    )
    st.session_state.history = st.session_state.history[:25]


def render_metric_cards(response_data: dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Success", "Yes" if response_data.get("success") else "No")

    with col2:
        st.metric("Rows Returned", response_data.get("row_count", 0))

    with col3:
        st.metric("Source", response_data.get("source") or "N/A")

    with col4:
        st.metric("Execution Time", f"{response_data.get('execution_time_ms', 0)} ms")


def render_results(response_data: dict[str, Any]) -> None:
    st.subheader("Result Summary")
    if response_data.get("success"):
        st.success(response_data.get("message", "Query completed successfully."))
    else:
        st.error(response_data.get("message", "Request failed."))
        if response_data.get("error"):
            st.code(response_data["error"], language="text")
        return

    render_metric_cards(response_data)

    sql_query = response_data.get("sql_query")
    if sql_query:
        with st.expander("Generated SQL", expanded=True):
            st.code(sql_query, language="sql")

    columns = response_data.get("columns", [])
    rows = response_data.get("rows", [])

    if columns and rows is not None:
        st.subheader("Query Results")
        df = pd.DataFrame(rows, columns=columns)
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Results as CSV",
            data=csv_data,
            file_name="query_results.csv",
            mime="text/csv",
        )

    chart_data = response_data.get("chart")
    if chart_data:
        st.subheader("Visualization")
        try:
            fig = pio.from_json(json.dumps(chart_data))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:
            st.warning(f"Chart could not be rendered: {exc}")

    with st.expander("Raw API Response"):
        st.json(response_data)


def render_history() -> None:
    st.subheader("Recent Query History")

    if not st.session_state.history:
        st.info("No query history yet.")
        return

    for index, item in enumerate(st.session_state.history):
        response = item["response"]
        title = f"{item['timestamp']} — {item['question']}"
        with st.expander(title, expanded=index == 0):
            top_cols = st.columns([3, 1, 1, 1])

            with top_cols[0]:
                st.write(f"**Question:** {item['question']}")
            with top_cols[1]:
                st.write(f"**Rows:** {response.get('row_count', 0)}")
            with top_cols[2]:
                st.write(f"**Source:** {response.get('source', 'N/A')}")
            with top_cols[3]:
                st.write(f"**Time:** {response.get('execution_time_ms', 0)} ms")

            if response.get("sql_query"):
                st.code(response["sql_query"], language="sql")


def render_sidebar() -> tuple[str, bool]:
    with st.sidebar:
        st.title("⚙️ Control Panel")

        api_base_url = st.text_input(
            "FastAPI Base URL",
            value=st.session_state.api_base_url,
            help="Example: http://127.0.0.1:8000",
        ).strip()
        st.session_state.api_base_url = api_base_url

        auto_health_check = st.checkbox("Check API health on refresh", value=True)

        st.markdown("---")
        st.subheader("Sample Questions")

        for sample in SAMPLE_QUESTIONS[:10]:
            if st.button(sample, use_container_width=True):
                st.session_state.question_input = sample

        st.markdown("---")
        st.subheader("History Tools")

        if st.button("Clear Query History", use_container_width=True):
            st.session_state.history = []
            st.session_state.last_response = None
            st.success("History cleared.")

        st.markdown("---")
        st.caption("Built with Streamlit + FastAPI + Vanna 2.0")

    return api_base_url, auto_health_check


def render_health_banner(api_base_url: str, auto_health_check: bool) -> None:
    st.subheader("API Status")

    if not auto_health_check:
        st.info("Automatic health check is disabled.")
        return

    try:
        health = get_health(api_base_url)
        status = health.get("status", "unknown")
        database = health.get("database", "unknown")

        cols = st.columns(5)
        cols[0].metric("Service Status", status)
        cols[1].metric("Database", database)
        cols[2].metric("Cache Size", health.get("cache_size", 0))
        cols[3].metric("Rate-Limited Clients", health.get("rate_limited_clients", 0))
        cols[4].metric("Known Shortcuts", health.get("known_shortcuts", 0))

        if status == "ok":
            st.success("Backend is healthy and ready.")
        else:
            st.warning("Backend is reachable but not fully healthy.")
    except Exception as exc:
        st.error(f"Health check failed: {exc}")


def main() -> None:
    init_session_state()

    st.title("🩺 Clinic NL2SQL Assistant")
    st.caption("Ask clinic database questions in plain English and get SQL-backed answers instantly.")

    api_base_url, auto_health_check = render_sidebar()
    render_health_banner(api_base_url, auto_health_check)

    st.markdown("---")

    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("Ask a Question")

        question = st.text_area(
            "Enter your natural language question",
            key="question_input",
            height=110,
            placeholder="Example: Show revenue by doctor",
        )

        action_cols = st.columns([1, 1, 4])

        submit_clicked = action_cols[0].button("Run Query", type="primary", use_container_width=True)
        clear_clicked = action_cols[1].button("Clear", use_container_width=True)

        if clear_clicked:
            st.session_state.question_input = ""
            st.session_state.last_response = None
            st.rerun()

        if submit_clicked:
            if not question.strip():
                st.warning("Please enter a question first.")
            else:
                with st.spinner("Querying backend and processing results..."):
                    try:
                        response_data = ask_question(api_base_url, question.strip())
                        st.session_state.last_response = response_data
                        add_to_history(question.strip(), response_data)
                    except Exception as exc:
                        st.session_state.last_response = {
                            "success": False,
                            "message": "Failed to connect to backend.",
                            "error": str(exc),
                            "row_count": 0,
                            "rows": [],
                            "columns": [],
                            "chart": None,
                            "chart_type": None,
                            "source": None,
                            "execution_time_ms": 0,
                            "sql_query": None,
                        }

        if st.session_state.last_response is not None:
            render_results(st.session_state.last_response)

    with right_col:
        st.subheader("Quick Insights")
        st.info(
            "This UI connects to the FastAPI backend. "
            "Use benchmark questions for deterministic results and explore custom questions for agent-based behavior."
        )

        st.markdown("### Tips")
        st.markdown(
            """
- Ask aggregate questions like revenue, counts, and trends
- Use time-based prompts like "last month" or "past 6 months"
- Benchmark questions are optimized for consistent output
- Download results as CSV after each successful query
            """
        )

        st.markdown("### Suggested Queries")
        for q in SAMPLE_QUESTIONS[10:15]:
            st.code(q, language="text")

    st.markdown("---")
    render_history()


if __name__ == "__main__":
    main()