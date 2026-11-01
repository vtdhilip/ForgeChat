import json
import asyncpg
from typing import Optional, List, Dict, Any
from app.core.config import settings

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initializes the asyncpg connection pool with json codecs."""
        if self.pool is not None:
            return

        async def init_connection(conn):
            # Automatic json/jsonb codec
            await conn.set_type_codec(
                'json',
                encoder=json.dumps,
                decoder=json.loads,
                schema='pg_catalog'
            )
            await conn.set_type_codec(
                'jsonb',
                encoder=json.dumps,
                decoder=json.loads,
                schema='pg_catalog'
            )

        # asyncpg needs standard postgresql:// URL
        dsn = settings.DATABASE_URL
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql://", 1)

        self.pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=2,
            max_size=20,
            init=init_connection,
            server_settings={"application_name": "synapticchat-fastapi"}
        )
        print("[database] Connected to PostgreSQL pool (application: synapticchat-fastapi)")

    async def disconnect(self):
        """Closes the asyncpg connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            print("[database] PostgreSQL connection pool closed.")

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Executes a query and returns a list of dictionaries."""
        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, *args)
            return [dict(r) for r in records]

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Executes a query and returns a single record as a dict, or None."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, *args)
            return dict(record) if record else None

    async def fetchval(self, query: str, *args) -> Any:
        """Executes a query and returns a single value."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args) -> str:
        """Executes a query and returns the status string."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

db = Database()
