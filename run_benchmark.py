import json
from pathlib import Path

import requests

API_URL = "http://127.0.0.1:8000/chat"
OUTPUT_JSON = Path("benchmark_results.json")
OUTPUT_MD = Path("RESULTS.md")

BENCHMARK_QUESTIONS = [
    {
        "id": 1,
        "question": "How many patients do we have?",
        "expected_behavior": "Returns count",
    },
    {
        "id": 2,
        "question": "List all doctors and their specializations",
        "expected_behavior": "Returns doctor list",
    },
    {
        "id": 3,
        "question": "Show me appointments for last month",
        "expected_behavior": "Filters by date",
    },
    {
        "id": 4,
        "question": "Which doctor has the most appointments?",
        "expected_behavior": "Aggregation + ordering",
    },
    {
        "id": 5,
        "question": "What is the total revenue?",
        "expected_behavior": "SUM of invoice amounts",
    },
    {
        "id": 6,
        "question": "Show revenue by doctor",
        "expected_behavior": "JOIN + GROUP BY",
    },
    {
        "id": 7,
        "question": "How many cancelled appointments last quarter?",
        "expected_behavior": "Status filter + date",
    },
    {
        "id": 8,
        "question": "Top 5 patients by spending",
        "expected_behavior": "JOIN + ORDER + LIMIT",
    },
    {
        "id": 9,
        "question": "Average treatment cost by specialization",
        "expected_behavior": "Multi-table JOIN + AVG",
    },
    {
        "id": 10,
        "question": "Show monthly appointment count for the past 6 months",
        "expected_behavior": "Date grouping",
    },
    {
        "id": 11,
        "question": "Which city has the most patients?",
        "expected_behavior": "GROUP BY + COUNT",
    },
    {
        "id": 12,
        "question": "List patients who visited more than 3 times",
        "expected_behavior": "HAVING clause",
    },
    {
        "id": 13,
        "question": "Show unpaid invoices",
        "expected_behavior": "Status filter",
    },
    {
        "id": 14,
        "question": "What percentage of appointments are no-shows?",
        "expected_behavior": "Percentage calculation",
    },
    {
        "id": 15,
        "question": "Show the busiest day of the week for appointments",
        "expected_behavior": "Date function",
    },
    {
        "id": 16,
        "question": "Revenue trend by month",
        "expected_behavior": "Time series",
    },
    {
        "id": 17,
        "question": "Average appointment duration by doctor",
        "expected_behavior": "AVG + GROUP BY",
    },
    {
        "id": 18,
        "question": "List patients with overdue invoices",
        "expected_behavior": "JOIN + filter",
    },
    {
        "id": 19,
        "question": "Compare revenue between departments",
        "expected_behavior": "JOIN + GROUP BY",
    },
    {
        "id": 20,
        "question": "Show patient registration trend by month",
        "expected_behavior": "Date grouping",
    },
]


def call_api(question: str) -> dict:
    response = requests.post(API_URL, json={"question": question}, timeout=60)
    response.raise_for_status()
    return response.json()


def evaluate_result(result: dict) -> tuple[str, str]:
    if not result.get("success"):
        return "Fail", result.get("error") or "API returned unsuccessful response"

    sql_query = (result.get("sql_query") or "").strip().lower()
    row_count = result.get("row_count", 0)

    if not sql_query.startswith("select"):
        return "Fail", "Generated SQL is missing or not a SELECT statement"

    if row_count == 0:
        return "Partial", "SQL executed but returned no rows"

    return "Pass", "SQL executed successfully and returned rows"


def summarize_rows(rows: list, limit: int = 2) -> str:
    if not rows:
        return "No rows returned"
    preview = rows[:limit]
    return json.dumps(preview, ensure_ascii=False)


def generate_markdown(results: list[dict]) -> str:
    total = len(results)
    passed = sum(1 for item in results if item["status"] == "Pass")
    partial = sum(1 for item in results if item["status"] == "Partial")
    failed = sum(1 for item in results if item["status"] == "Fail")

    lines = []
    lines.append("# RESULTS")
    lines.append("")
    lines.append("## Benchmark Summary")
    lines.append("")
    lines.append(f"- Total Questions: {total}")
    lines.append(f"- Passed: {passed}")
    lines.append(f"- Partial: {partial}")
    lines.append(f"- Failed: {failed}")
    lines.append("")
    lines.append("## Detailed Results")
    lines.append("")

    for item in results:
        lines.append(f"### {item['id']}. {item['question']}")
        lines.append(f"- Expected Behavior: {item['expected_behavior']}")
        lines.append(f"- Status: **{item['status']}**")
        lines.append(f"- Notes: {item['notes']}")
        lines.append(f"- Source: {item.get('source')}")
        lines.append(f"- Row Count: {item.get('row_count')}")
        lines.append(f"- Execution Time (ms): {item.get('execution_time_ms')}")
        lines.append("")
        lines.append("**Generated SQL:**")
        lines.append("```sql")
        lines.append(item.get("sql_query") or "-- No SQL generated")
        lines.append("```")
        lines.append("")
        lines.append("**Result Preview:**")
        lines.append("```json")
        lines.append(item.get("result_preview", "[]"))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    results = []

    print("Running benchmark against API...")
    print()

    for item in BENCHMARK_QUESTIONS:
        question = item["question"]
        print(f"[{item['id']}/20] {question}")

        try:
            api_result = call_api(question)
            status, notes = evaluate_result(api_result)

            result_entry = {
                "id": item["id"],
                "question": question,
                "expected_behavior": item["expected_behavior"],
                "status": status,
                "notes": notes,
                "sql_query": api_result.get("sql_query"),
                "row_count": api_result.get("row_count"),
                "execution_time_ms": api_result.get("execution_time_ms"),
                "source": api_result.get("source"),
                "result_preview": summarize_rows(api_result.get("rows", [])),
                "raw_response": api_result,
            }
        except Exception as exc:
            result_entry = {
                "id": item["id"],
                "question": question,
                "expected_behavior": item["expected_behavior"],
                "status": "Fail",
                "notes": f"{type(exc).__name__}: {exc}",
                "sql_query": None,
                "row_count": 0,
                "execution_time_ms": None,
                "source": None,
                "result_preview": "[]",
                "raw_response": None,
            }

        results.append(result_entry)
        print(f"    -> {result_entry['status']}: {result_entry['notes']}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    markdown = generate_markdown(results)
    OUTPUT_MD.write_text(markdown, encoding="utf-8")

    print()
    print(f"Saved JSON results to {OUTPUT_JSON}")
    print(f"Saved markdown report to {OUTPUT_MD}")


if __name__ == "__main__":
    main()