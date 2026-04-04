import os
import json
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.core.tool import ToolContext
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
    SaveTextMemoryTool,
)
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.openai import OpenAILlmService

load_dotenv()

DB_PATH = "clinic.db"
SEED_FILE = Path("seed_data.json")

DEFAULT_USER_ID = "default_user"
DEFAULT_USER_EMAIL = "default_user@example.com"
ADMIN_GROUP = "admin"
USER_GROUP = "user"


class DefaultUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id=DEFAULT_USER_ID,
            email=DEFAULT_USER_EMAIL,
            group_memberships=[ADMIN_GROUP, USER_GROUP],
        )


def build_default_user() -> User:
    return User(
        id=DEFAULT_USER_ID,
        email=DEFAULT_USER_EMAIL,
        group_memberships=[ADMIN_GROUP, USER_GROUP],
    )


def create_llm_service() -> OpenAILlmService:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing. Add GROQ_API_KEY=your_key in .env"
        )

    return OpenAILlmService(
        api_key=api_key,
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
    )


def create_agent_memory() -> DemoAgentMemory:
    return DemoAgentMemory(max_items=1000)


def create_tool_registry() -> ToolRegistry:
    tools = ToolRegistry()

    tools.register_local_tool(
        RunSqlTool(sql_runner=SqliteRunner(database_path=DB_PATH)),
        access_groups=[ADMIN_GROUP, USER_GROUP],
    )
    tools.register_local_tool(
        VisualizeDataTool(),
        access_groups=[ADMIN_GROUP, USER_GROUP],
    )
    tools.register_local_tool(
        SaveQuestionToolArgsTool(),
        access_groups=[ADMIN_GROUP],
    )
    tools.register_local_tool(
        SearchSavedCorrectToolUsesTool(),
        access_groups=[ADMIN_GROUP, USER_GROUP],
    )
    tools.register_local_tool(
        SaveTextMemoryTool(),
        access_groups=[ADMIN_GROUP, USER_GROUP],
    )

    return tools


def create_vanna_agent() -> Agent:
    memory = create_agent_memory()

    agent = Agent(
        llm_service=create_llm_service(),
        tool_registry=create_tool_registry(),
        user_resolver=DefaultUserResolver(),
        agent_memory=memory,
        config=AgentConfig(),
    )
    return agent


def default_seed_examples() -> list[dict[str, Any]]:
    return [
        {
            "question": "How many patients do we have?",
            "args": {"sql": "SELECT COUNT(*) AS total_patients FROM patients;"},
        },
        {
            "question": "List all doctors and their specializations",
            "args": {"sql": "SELECT name, specialization FROM doctors ORDER BY name;"},
        },
        {
            "question": "Which city has the most patients?",
            "args": {
                "sql": """
                    SELECT city, COUNT(*) AS patient_count
                    FROM patients
                    GROUP BY city
                    ORDER BY patient_count DESC
                    LIMIT 1;
                """
            },
        },
        {
            "question": "Show patients by gender",
            "args": {
                "sql": """
                    SELECT gender, COUNT(*) AS total_patients
                    FROM patients
                    GROUP BY gender
                    ORDER BY total_patients DESC;
                """
            },
        },
        {
            "question": "Show patient registration trend by month",
            "args": {
                "sql": """
                    SELECT strftime('%Y-%m', registered_date) AS month,
                           COUNT(*) AS registrations
                    FROM patients
                    GROUP BY month
                    ORDER BY month;
                """
            },
        },
        {
            "question": "Which doctor has the most appointments?",
            "args": {
                "sql": """
                    SELECT d.name, COUNT(*) AS appointment_count
                    FROM appointments a
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.id, d.name
                    ORDER BY appointment_count DESC
                    LIMIT 1;
                """
            },
        },
        {
            "question": "Show appointments by status",
            "args": {
                "sql": """
                    SELECT status, COUNT(*) AS total_appointments
                    FROM appointments
                    GROUP BY status
                    ORDER BY total_appointments DESC;
                """
            },
        },
        {
            "question": "Show me appointments for last month",
            "args": {
                "sql": """
                    SELECT id, patient_id, doctor_id, appointment_date, status
                    FROM appointments
                    WHERE appointment_date >= date('now', 'start of month', '-1 month')
                      AND appointment_date < date('now', 'start of month')
                    ORDER BY appointment_date;
                """
            },
        },
        {
            "question": "How many cancelled appointments last quarter?",
            "args": {
                "sql": """
                    SELECT COUNT(*) AS cancelled_count
                    FROM appointments
                    WHERE status = 'Cancelled'
                      AND appointment_date >= date('now', '-3 months');
                """
            },
        },
        {
            "question": "Show monthly appointment count for the past 6 months",
            "args": {
                "sql": """
                    SELECT strftime('%Y-%m', appointment_date) AS month,
                           COUNT(*) AS total_appointments
                    FROM appointments
                    WHERE appointment_date >= date('now', '-6 months')
                    GROUP BY month
                    ORDER BY month;
                """
            },
        },
        {
            "question": "Top 5 patients by spending",
            "args": {
                "sql": """
                    SELECT p.first_name,
                           p.last_name,
                           SUM(i.total_amount) AS total_spending
                    FROM invoices i
                    JOIN patients p ON i.patient_id = p.id
                    GROUP BY p.id, p.first_name, p.last_name
                    ORDER BY total_spending DESC
                    LIMIT 5;
                """
            },
        },
        {
            "question": "What is the total revenue?",
            "args": {"sql": "SELECT SUM(total_amount) AS total_revenue FROM invoices;"},
        },
        {
            "question": "Show revenue by doctor",
            "args": {
                "sql": """
                    SELECT d.name,
                           SUM(i.total_amount) AS total_revenue
                    FROM invoices i
                    JOIN appointments a ON i.patient_id = a.patient_id
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.id, d.name
                    ORDER BY total_revenue DESC;
                """
            },
        },
        {
            "question": "Average treatment cost by specialization",
            "args": {
                "sql": """
                    SELECT d.specialization,
                           AVG(t.cost) AS avg_treatment_cost
                    FROM treatments t
                    JOIN appointments a ON t.appointment_id = a.id
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.specialization
                    ORDER BY avg_treatment_cost DESC;
                """
            },
        },
        {
            "question": "Show unpaid invoices",
            "args": {
                "sql": """
                    SELECT id, patient_id, invoice_date, total_amount, paid_amount, status
                    FROM invoices
                    WHERE status IN ('Pending', 'Overdue')
                    ORDER BY invoice_date DESC;
                """
            },
        },
        {
            "question": "List patients with overdue invoices",
            "args": {
                "sql": """
                    SELECT DISTINCT p.first_name, p.last_name, p.city
                    FROM invoices i
                    JOIN patients p ON i.patient_id = p.id
                    WHERE i.status = 'Overdue'
                    ORDER BY p.last_name, p.first_name;
                """
            },
        },
        {
            "question": "Revenue trend by month",
            "args": {
                "sql": """
                    SELECT strftime('%Y-%m', invoice_date) AS month,
                           SUM(total_amount) AS total_revenue
                    FROM invoices
                    GROUP BY month
                    ORDER BY month;
                """
            },
        },
        {
            "question": "List patients who visited more than 3 times",
            "args": {
                "sql": """
                    SELECT p.first_name,
                           p.last_name,
                           COUNT(a.id) AS visit_count
                    FROM appointments a
                    JOIN patients p ON a.patient_id = p.id
                    GROUP BY p.id, p.first_name, p.last_name
                    HAVING COUNT(a.id) > 3
                    ORDER BY visit_count DESC;
                """
            },
        },
        {
            "question": "What percentage of appointments are no-shows?",
            "args": {
                "sql": """
                    SELECT ROUND(
                        100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*),
                        2
                    ) AS no_show_percentage
                    FROM appointments;
                """
            },
        },
        {
            "question": "Compare revenue between departments",
            "args": {
                "sql": """
                    SELECT d.department,
                           SUM(i.total_amount) AS total_revenue
                    FROM invoices i
                    JOIN appointments a ON i.patient_id = a.patient_id
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.department
                    ORDER BY total_revenue DESC;
                """
            },
        },
        {
            "question": "Show the busiest day of the week for appointments",
            "args": {
                "sql": """
                    SELECT CASE strftime('%w', appointment_date)
                               WHEN '0' THEN 'Sunday'
                               WHEN '1' THEN 'Monday'
                               WHEN '2' THEN 'Tuesday'
                               WHEN '3' THEN 'Wednesday'
                               WHEN '4' THEN 'Thursday'
                               WHEN '5' THEN 'Friday'
                               WHEN '6' THEN 'Saturday'
                           END AS weekday,
                           COUNT(*) AS total_appointments
                    FROM appointments
                    GROUP BY weekday
                    ORDER BY total_appointments DESC
                    LIMIT 1;
                """
            },
        },
        {
            "question": "Average appointment duration by doctor",
            "args": {
                "sql": """
                    SELECT d.name,
                           AVG(t.duration_minutes) AS avg_duration_minutes
                    FROM treatments t
                    JOIN appointments a ON t.appointment_id = a.id
                    JOIN doctors d ON a.doctor_id = d.id
                    GROUP BY d.id, d.name
                    ORDER BY avg_duration_minutes DESC;
                """
            },
        },
    ]


def save_seed_examples_to_file(path: Path = SEED_FILE) -> None:
    examples = default_seed_examples()
    with open(path, "w", encoding="utf-8") as file:
        json.dump(examples, file, indent=2, ensure_ascii=False)


def build_tool_context(agent: Agent, user: User) -> ToolContext:
    return ToolContext(
        user=user,
        conversation_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        agent_memory=agent.agent_memory,
    )


async def hydrate_agent_memory(agent: Agent, verbose: bool = True) -> int:
    if SEED_FILE.exists():
        with open(SEED_FILE, "r", encoding="utf-8") as file:
            examples = json.load(file)
    else:
        examples = default_seed_examples()

    if not hasattr(agent.agent_memory, "save_tool_usage"):
        raise AttributeError(
            "This Vanna version does not expose agent_memory.save_tool_usage(). "
            "Your local package is not compatible with the current docs-based seeding approach."
        )

    saved_count = 0
    user = build_default_user()

    for index, item in enumerate(examples, start=1):
        question = item["question"]
        args = item["args"]

        try:
            context = build_tool_context(agent, user)
            await agent.agent_memory.save_tool_usage(
                question=question,
                tool_name="RunSqlTool",
                args=args,
                context=context,
                success=True,
            )
            saved_count += 1
            if verbose:
                print(f"[OK {index}] {question}")
        except Exception as exc:
            if verbose:
                print(f"[FAIL {index}] {question}")
                print(f"        {type(exc).__name__}: {exc}")

    return saved_count