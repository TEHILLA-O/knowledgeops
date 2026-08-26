import asyncio

import asyncpg


async def main() -> None:
    for port in (5433, 5432):
        try:
            conn = await asyncpg.connect(
                user="knowledgeops",
                password="knowledgeops",
                database="knowledgeops",
                host="127.0.0.1",
                port=port,
            )
            val = await conn.fetchval("SELECT 1")
            print(f"port {port}: OK -> {val}")
            await conn.close()
        except Exception as exc:
            print(f"port {port}: FAIL -> {exc}")


asyncio.run(main())
