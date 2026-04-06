from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_fts_index(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(
            """
            CREATE INDEX IF NOT EXISTS ix_users_fts
            ON users
            USING GIN (to_tsvector('english', full_name || ' ' || email));
            """
        ))