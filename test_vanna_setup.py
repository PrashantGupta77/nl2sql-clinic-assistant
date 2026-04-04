import asyncio
from vanna_setup import create_vanna_agent, hydrate_agent_memory, save_seed_examples_to_file

async def main():
    save_seed_examples_to_file()
    agent = create_vanna_agent()
    count = await hydrate_agent_memory(agent, verbose=True)
    print()
    print("Agent created successfully.")
    print(f"Hydrated memory items: {count}")

if __name__ == "__main__":
    asyncio.run(main())