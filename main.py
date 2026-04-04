import re
import time
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import plotly.express as px
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from vanna_setup import create_vanna_agent, hydrate_agent_memory, save_seed_examples_to_file
from vanna.core.user import RequestContext

DB_PATH = "clinic.db"
SEED_FILE = Path("seed_data.json")

app = FastAPI(
    title="Clinic NL2SQL API",
    version="1.0.0",
    description="Natural Language to SQL API using Vanna 2.0, FastAPI, and SQLite",
)

agent = None
query_cache: dict[str, dict[str, Any]] = {}
rate_limit_store: dict[str, list[float]] = {}
known_question_sql_map: dict[str, str] = {}

MAX_QUESTION_LENGTH = 300
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 20


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)


class ChatResponse(BaseModel):
    success: bool
    message: str
    sql_query: Optional[str] = None
    columns: list[str] = []
    rows: list[list[Any]] = []
    row_count: int = 0
    chart: Optional[dict[str, Any]] = None
    chart_type: Optional[str] = None
    source: Optional[str] = None
    execution_time_ms: Optional[int] = None
    error: Optional[str] = None


def normalize_question(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def load_known_question_sql_map() -> dict[str, str]:
    if not SEED_FILE.exists():
        return {}

    with open(SEED_FILE, "r", encoding="utf-8") as file:
        examples = json.load(file)

    mapping = {}
    for item in examples:
        question = normalize_question(item["question"])
        sql = item["args"]["sql"].strip()
        mapping[question] = sql

    return mapping


def validate_sql(sql: str) -> tuple[bool, str]:
    normalized = sql.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)

    blocked_keywords = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "exec",
        "xp_",
        "sp_",
        "grant",
        "revoke",
        "shutdown",
        "truncate",
        "attach",
        "detach",
        "create",
        "replace",
    ]

    if not normalized.startswith("select"):
        return False, "Only SELECT queries are allowed."

    for keyword in blocked_keywords:
        if keyword in normalized:
            return False, f"Blocked SQL keyword detected: {keyword}"

    blocked_system_refs = [
        "sqlite_master",
        "sqlite_temp_master",
        "pragma",
    ]
    for item in blocked_system_refs:
        if item in normalized:
            return False, f"System table or command not allowed: {item}"

    return True, ""


def execute_sql(sql: str) -> tuple[list[str], list[list[Any]]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description] if cursor.description else []
        data = [list(row) for row in rows]
        return columns, data
    finally:
        conn.close()


def extract_sql(text: str) -> Optional[str]:
    if not text:
        return None

    sql_block_match = re.search(r"```sql\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if sql_block_match:
        return sql_block_match.group(1).strip()

    generic_block_match = re.search(r"```\s*(select .*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if generic_block_match:
        return generic_block_match.group(1).strip()

    select_statement_match = re.search(r"(select\s+.*?;)", text, flags=re.IGNORECASE | re.DOTALL)
    if select_statement_match:
        return select_statement_match.group(1).strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if line.lower().startswith("select "):
            return line

    return None


def choose_chart_type(columns: list[str], rows: list[list[Any]]) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    if not columns or not rows or len(columns) < 2:
        return None, None

    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return None, None

    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_columns:
        return None, None

    x_col = columns[0]
    y_col = numeric_columns[0]

    x_lower = x_col.lower()
    y_lower = y_col.lower()

    try:
        if "month" in x_lower or "date" in x_lower or "year" in x_lower:
            fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
            return json.loads(fig.to_json()), "line"

        if any(word in x_lower for word in ["status", "gender", "department", "specialization", "city"]) and df[x_col].nunique() <= 10:
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
            return json.loads(fig.to_json()), "bar"

        if len(columns) == 2 and df[x_col].nunique() <= 6 and any(word in y_lower for word in ["count", "percentage", "total"]):
            fig = px.pie(df, names=x_col, values=y_col, title=f"{y_col} by {x_col}")
            return json.loads(fig.to_json()), "pie"

        fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        return json.loads(fig.to_json()), "bar"
    except Exception:
        return None, None


def summarize_result(question: str, row_count: int) -> str:
    if row_count == 0:
        return f"No data found for: {question}"
    if row_count == 1:
        return "Query executed successfully. Returned 1 row."
    return f"Query executed successfully. Returned {row_count} rows."


def enforce_rate_limit(client_key: str) -> None:
    now = time.time()
    request_times = rate_limit_store.get(client_key, [])
    request_times = [timestamp for timestamp in request_times if now - timestamp < RATE_LIMIT_WINDOW_SECONDS]

    if len(request_times) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

    request_times.append(now)
    rate_limit_store[client_key] = request_times


async def collect_agent_response(question: str) -> str:
    context = RequestContext()
    stream = agent.send_message(context, question)

    collected_parts: list[str] = []

    async for chunk in stream:
        if hasattr(chunk, "simple_component") and chunk.simple_component:
            text = getattr(chunk.simple_component, "text", None)
            if text:
                cleaned = text.strip()
                if not cleaned:
                    continue
                if "Tool completed" in cleaned:
                    continue
                if "Results saved" in cleaned:
                    continue
                if "IMPORTANT: FOR VISUALIZE_DATA" in cleaned:
                    continue
                collected_parts.append(cleaned)

    raw_text = "\n".join(collected_parts).strip()
    return raw_text


def build_success_response(
    question: str,
    sql_query: str,
    columns: list[str],
    rows: list[list[Any]],
    source: str,
    start_time: float,
) -> ChatResponse:
    row_count = len(rows)
    chart, chart_type = choose_chart_type(columns, rows)
    message = summarize_result(question, row_count)

    response_payload = {
        "success": True,
        "message": message,
        "sql_query": sql_query,
        "columns": columns,
        "rows": rows,
        "row_count": row_count,
        "chart": chart,
        "chart_type": chart_type,
        "source": source,
        "execution_time_ms": int((time.time() - start_time) * 1000),
        "error": None,
    }

    return ChatResponse(**response_payload)


@app.on_event("startup")
async def startup_event() -> None:
    global agent, known_question_sql_map

    save_seed_examples_to_file()
    known_question_sql_map = load_known_question_sql_map()

    agent = create_vanna_agent()
    hydrated_count = await hydrate_agent_memory(agent, verbose=False)

    print(f"Startup complete. Hydrated memory items: {hydrated_count}")
    print(f"Loaded known SQL shortcuts: {len(known_question_sql_map)}")


@app.get("/health")
async def health() -> dict[str, Any]:
    db_status = "connected"
    db_error = None

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
    except Exception as exc:
        db_status = "disconnected"
        db_error = str(exc)

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "database_error": db_error,
        "cache_size": len(query_cache),
        "rate_limited_clients": len(rate_limit_store),
        "known_shortcuts": len(known_question_sql_map),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    question = payload.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(client_ip)

    cache_key = normalize_question(question)
    if cache_key in query_cache:
        cached = dict(query_cache[cache_key])
        cached["source"] = "cache"
        return ChatResponse(**cached)

    start_time = time.time()

    try:
        # 1) Exact known-question shortcut
        if cache_key in known_question_sql_map:
            sql_query = known_question_sql_map[cache_key]

            is_valid, validation_error = validate_sql(sql_query)
            if not is_valid:
                return ChatResponse(
                    success=False,
                    message="Known SQL failed validation.",
                    sql_query=sql_query,
                    error=validation_error,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            columns, rows = execute_sql(sql_query)
            response = build_success_response(
                question=question,
                sql_query=sql_query,
                columns=columns,
                rows=rows,
                source="verified_seed_match",
                start_time=start_time,
            )
            query_cache[cache_key] = response.model_dump()
            return response

        # 2) Agent path for non-seeded questions
        agent_response = await collect_agent_response(question)
        print("\n--- RAW AGENT RESPONSE ---")
        print(agent_response if agent_response else "[EMPTY RESPONSE]")
        print("--- END RAW AGENT RESPONSE ---\n")

        if not agent_response:
            return ChatResponse(
                success=False,
                message="The AI did not return any response.",
                error="Empty agent response",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        sql_query = extract_sql(agent_response)
        if not sql_query:
            return ChatResponse(
                success=False,
                message="The AI could not generate a valid SQL query.",
                error="No SQL query found in agent response",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        is_valid, validation_error = validate_sql(sql_query)
        if not is_valid:
            return ChatResponse(
                success=False,
                message="Generated SQL failed validation.",
                sql_query=sql_query,
                error=validation_error,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        columns, rows = execute_sql(sql_query)
        response = build_success_response(
            question=question,
            sql_query=sql_query,
            columns=columns,
            rows=rows,
            source="agent_generated",
            start_time=start_time,
        )

        query_cache[cache_key] = response.model_dump()
        return response

    except sqlite3.Error as exc:
        return ChatResponse(
            success=False,
            message="Database query failed.",
            error=str(exc),
            execution_time_ms=int((time.time() - start_time) * 1000),
        )
    except Exception as exc:
        return ChatResponse(
            success=False,
            message="Unexpected error while processing the request.",
            error=str(exc),
            execution_time_ms=int((time.time() - start_time) * 1000),
        )