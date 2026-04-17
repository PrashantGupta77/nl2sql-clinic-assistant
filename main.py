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
    version="1.4.1",
    description="Natural Language to SQL API using Vanna 2.0, FastAPI, and SQLite",
)

agent = None
query_cache: dict[str, dict[str, Any]] = {}
rate_limit_store: dict[str, list[float]] = {}
known_question_sql_map: dict[str, str] = {}
schema_context_cache: str = ""

MAX_QUESTION_LENGTH = 300
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 20
MAX_CACHE_ITEMS = 100

BLOCKED_KEYWORDS = [
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

BLOCKED_SYSTEM_REFS = [
    "sqlite_master",
    "sqlite_temp_master",
    "pragma",
]

KNOWN_QUERY_ALIASES: dict[str, str] = {
    "what is the busiest day": "show the busiest day of the week for appointments",
    "which is the busiest day": "show the busiest day of the week for appointments",
    "which day is the busiest": "show the busiest day of the week for appointments",
    "busiest day": "show the busiest day of the week for appointments",
    "show busiest day": "show the busiest day of the week for appointments",
    "what is the busiest day of the week": "show the busiest day of the week for appointments",
    "which is the busiest day of the week": "show the busiest day of the week for appointments",
    "which doctor has the least appointments": "which doctor has the least number of appointments",
    "doctor with least appointments": "which doctor has the least number of appointments",
    "least busy doctor": "which doctor has the least number of appointments",
    "which day has the most completed appointments": "which day of the week has the highest number of completed appointments",
    "busiest day for completed appointments": "which day of the week has the highest number of completed appointments",
}

RULE_BASED_SQL: dict[str, str] = {
    "which doctor has the least number of appointments": """
        SELECT d.name, COUNT(*) AS appointment_count
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        GROUP BY d.id, d.name
        ORDER BY appointment_count ASC, d.name ASC
        LIMIT 1;
    """.strip(),
    "which doctor has the least appointments": """
        SELECT d.name, COUNT(*) AS appointment_count
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        GROUP BY d.id, d.name
        ORDER BY appointment_count ASC, d.name ASC
        LIMIT 1;
    """.strip(),
    "which day of the week has the highest number of completed appointments": """
        SELECT CASE strftime('%w', appointment_date)
                   WHEN '0' THEN 'Sunday'
                   WHEN '1' THEN 'Monday'
                   WHEN '2' THEN 'Tuesday'
                   WHEN '3' THEN 'Wednesday'
                   WHEN '4' THEN 'Thursday'
                   WHEN '5' THEN 'Friday'
                   WHEN '6' THEN 'Saturday'
               END AS weekday,
               COUNT(*) AS total_completed_appointments
        FROM appointments
        WHERE status = 'Completed'
        GROUP BY weekday
        ORDER BY total_completed_appointments DESC
        LIMIT 1;
    """.strip(),
}


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
    text = re.sub(r"[^\w\s-]", "", text)
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


def get_schema_context() -> str:
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        tables = cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        ).fetchall()

        schema_lines: list[str] = []
        for (table_name,) in tables:
            columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
            col_parts = [f"{col[1]} {col[2]}" for col in columns]
            schema_lines.append(f"{table_name}({', '.join(col_parts)})")

        return "\n".join(schema_lines)
    finally:
        conn.close()


def resolve_shortcut_sql(question: str) -> tuple[Optional[str], Optional[str]]:
    normalized_question = normalize_question(question)

    if normalized_question in known_question_sql_map:
        return known_question_sql_map[normalized_question], "verified_seed_match"

    aliased_question = KNOWN_QUERY_ALIASES.get(normalized_question)
    if aliased_question:
        normalized_alias = normalize_question(aliased_question)
        if normalized_alias in known_question_sql_map:
            return known_question_sql_map[normalized_alias], "alias_seed_match"
        if normalized_alias in RULE_BASED_SQL:
            return RULE_BASED_SQL[normalized_alias], "alias_rule_match"

    if normalized_question in RULE_BASED_SQL:
        return RULE_BASED_SQL[normalized_question], "rule_based_match"

    return None, None


def normalize_sql_literals(sql: str) -> str:
    replacements = {
        "'cancelled'": "'Cancelled'",
        "'completed'": "'Completed'",
        "'scheduled'": "'Scheduled'",
        "'no-show'": "'No-Show'",
        "'noshow'": "'No-Show'",
        "'paid'": "'Paid'",
        "'pending'": "'Pending'",
        "'overdue'": "'Overdue'",
    }

    normalized_sql = sql
    for old, new in replacements.items():
        normalized_sql = re.sub(
            re.escape(old),
            new,
            normalized_sql,
            flags=re.IGNORECASE,
        )
    return normalized_sql


def finalize_sql(sql: str) -> str:
    return normalize_sql_literals(sql)


def validate_sql(sql: str) -> tuple[bool, str]:
    normalized = sql.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)

    if not normalized.startswith("select"):
        return False, "Only SELECT queries are allowed."

    if normalized.count(";") > 1:
        return False, "Multiple SQL statements are not allowed."

    for keyword in BLOCKED_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", normalized):
            return False, f"Blocked SQL keyword detected: {keyword}"

    for item in BLOCKED_SYSTEM_REFS:
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

    patterns = [
        r"```sql\s*(.*?)```",
        r"```\s*(select .*?)```",
        r"(select\s+.*?;)",
        r"(select\s+.*)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            candidate = re.sub(r"^sql\s*", "", candidate, flags=re.IGNORECASE).strip()
            if candidate.lower().startswith("select"):
                if not candidate.endswith(";"):
                    candidate += ";"
                return candidate

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sql_lines: list[str] = []
    started = False

    for line in lines:
        lower_line = line.lower()
        if lower_line.startswith("select "):
            started = True
        if started:
            sql_lines.append(line)
            if line.endswith(";"):
                break

    if sql_lines:
        candidate = " ".join(sql_lines).strip()
        if candidate.lower().startswith("select"):
            if not candidate.endswith(";"):
                candidate += ";"
            return candidate

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

        if any(word in x_lower for word in ["status", "gender", "department", "specialization", "city", "weekday"]) and df[x_col].nunique() <= 12:
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


def save_to_cache(cache_key: str, response: ChatResponse) -> None:
    if len(query_cache) >= MAX_CACHE_ITEMS:
        oldest_key = next(iter(query_cache))
        query_cache.pop(oldest_key, None)
    query_cache[cache_key] = response.model_dump()


async def collect_agent_response(question: str) -> str:
    context = RequestContext()

    prompt = f"""
You are generating SQL for a SQLite clinic database.

Return exactly one valid SQLite SELECT query and nothing else.
Do not use markdown.
Do not explain anything.
Do not include bullets, comments, or prose.

Database schema:
{schema_context_cache}

Allowed categorical values:
- appointments.status: Scheduled, Completed, Cancelled, No-Show
- invoices.status: Paid, Pending, Overdue

Important constraints:
- Use only SQLite-compatible SQL.
- Use only SELECT queries.
- Prefer existing table and column names exactly as given.
- Use the exact categorical values listed above when needed.
- If grouping by weekday, use strftime('%w', appointment_date).
- If the user asks about busiest day, compute weekday from appointments.

Question: {question}
""".strip()

    stream = agent.send_message(context, prompt)

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


async def collect_agent_response_retry(question: str) -> str:
    context = RequestContext()

    prompt = f"""
Return only one SQLite SELECT query for this question.
No markdown.
No explanation.
No prose.
Only SQL starting with SELECT and ending with semicolon.

Schema:
{schema_context_cache}

Allowed values:
- appointments.status: Scheduled, Completed, Cancelled, No-Show
- invoices.status: Paid, Pending, Overdue

Question: {question}
""".strip()

    stream = agent.send_message(context, prompt)

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
    global agent, known_question_sql_map, schema_context_cache

    save_seed_examples_to_file()
    known_question_sql_map = load_known_question_sql_map()
    schema_context_cache = get_schema_context()

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
        # 1) Exact, alias, or rule-based shortcut
        shortcut_sql, shortcut_source = resolve_shortcut_sql(question)
        if shortcut_sql:
            shortcut_sql = finalize_sql(shortcut_sql)

            is_valid, validation_error = validate_sql(shortcut_sql)
            if not is_valid:
                return ChatResponse(
                    success=False,
                    message="Shortcut SQL failed validation.",
                    sql_query=shortcut_sql,
                    error=validation_error,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            columns, rows = execute_sql(shortcut_sql)
            response = build_success_response(
                question=question,
                sql_query=shortcut_sql,
                columns=columns,
                rows=rows,
                source=shortcut_source or "verified_seed_match",
                start_time=start_time,
            )
            save_to_cache(cache_key, response)
            return response

        # 2) Agent path for non-seeded questions
        agent_response = await collect_agent_response(question)

        print("\n--- RAW AGENT RESPONSE (ATTEMPT 1) ---")
        print(agent_response if agent_response else "[EMPTY RESPONSE]")
        print("--- END RAW AGENT RESPONSE ---\n")

        sql_query = extract_sql(agent_response)

        # 3) Retry once with stricter prompt if extraction fails
        if not sql_query:
            retry_response = await collect_agent_response_retry(question)

            print("\n--- RAW AGENT RESPONSE (ATTEMPT 2) ---")
            print(retry_response if retry_response else "[EMPTY RESPONSE]")
            print("--- END RAW AGENT RESPONSE ---\n")

            sql_query = extract_sql(retry_response)

        if not sql_query:
            return ChatResponse(
                success=False,
                message="The AI could not generate a valid SQL query.",
                error="No SQL query found in agent response",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        sql_query = finalize_sql(sql_query)

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

        save_to_cache(cache_key, response)
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