import json
import sqlite3
import asyncio
from pathlib import Path
from typing import Any

from vanna_setup import (
    create_vanna_agent,
    default_seed_examples,
    hydrate_agent_memory,
    save_seed_examples_to_file,
)

DB_PATH = "clinic.db"
SEED_FILE = Path("seed_data.json")


def load_seed_examples() -> list[dict[str, Any]]:
    if SEED_FILE.exists():
        with open(SEED_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return default_seed_examples()


def validate_seed_sql_examples(examples: list[dict[str, Any]]) -> tuple[int, list[str]]:
    conn = sqlite3.connect(DB_PATH)
    errors: list[str] = []
    valid_count = 0

    try:
        for item in examples:
            question = item["question"]
            sql = item["args"]["sql"].strip()

            try:
                conn.execute(sql).fetchmany(1)
                valid_count += 1
            except Exception as exc:
                errors.append(f"{question} -> {type(exc).__name__}: {exc}")
    finally:
        conn.close()

    return valid_count, errors


async def main() -> None:
    print("Saving seed examples...")
    save_seed_examples_to_file()

    examples = load_seed_examples()
    print(f"Loaded {len(examples)} seed examples from {SEED_FILE.name}")

    print("\nValidating SQL examples against clinic.db...")
    valid_count, validation_errors = validate_seed_sql_examples(examples)

    print(f"Valid SQL examples: {valid_count}/{len(examples)}")

    if validation_errors:
        print("\nValidation errors found:")
        for error in validation_errors:
            print(f"- {error}")
        print("\nFix the invalid SQL examples before seeding memory.")
        return

    print("\nCreating Vanna agent...")
    agent = create_vanna_agent()

    print("Hydrating DemoAgentMemory...")
    hydrated_count = await hydrate_agent_memory(agent, verbose=True)

    print("\n=== Seed Summary ===")
    print(f"Seed file: {SEED_FILE.name}")
    print(f"Examples saved: {len(examples)}")
    print(f"Examples validated: {valid_count}")
    print(f"Examples hydrated: {hydrated_count}")

    if hydrated_count == len(examples):
        print("\nAll seed examples were successfully hydrated into agent memory.")
    else:
        print("\nSome seed examples were not hydrated. Review the logs above.")


if __name__ == "__main__":
    asyncio.run(main())