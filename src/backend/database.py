import asyncpg
import os
import time
from backend import log, queries

class Database:
    def __init__(self):
        self.user = os.getenv('DB_USERNAME')
        self.password = os.getenv('DB_PASSWORD')
        self.pool = None

    async def connect(self):
        for attempts in range(5):
            try:
                self.pool = await asyncpg.create_pool(os.getenv('DB_URL'))
                log("Connected to database.")
                await self.create_tables()
                break
            except Exception as e:
                if attempts < 4:
                    log(f"Database connection failed ({e}). Retrying...")
                    time.sleep(3)
                else:
                    log("Could not connect to database.")
                    exit(1)
    
    async def create_tables(self):
        await self.execute(queries.create_tables)

    async def execute(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetchone(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)