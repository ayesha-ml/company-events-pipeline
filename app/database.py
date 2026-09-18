import os
import json
import asyncpg
from dotenv import load_dotenv
from datetime import datetime, date, timezone

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
pool: asyncpg.Pool = None

async def init_db():
    global pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

async def close_db():
    global pool
    if pool:
        await pool.close()

async def save_event_record(
    company_id, source_id, raw_payload, normalized_data, consensus_data, audit_metadata, retrieved_at, expires_at
):
    async with pool.acquire() as connection:
        await connection.execute(
            """
            INSERT INTO company_event_records (
                company_id, source_id, raw_payload, normalized_data, consensus_data, audit_metadata, retrieved_at, expires_at
            )
            VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, $7, $8)
            """,
            company_id,
            source_id,
            json.dumps(raw_payload),
            json.dumps(normalized_data),
            json.dumps(consensus_data),
            json.dumps(audit_metadata),
            retrieved_at,
            expires_at,
        )

async def get_company_events(company_id: str, since: str | date | datetime):
    """fetches event records for a company filtered by since date"""
    if isinstance(since, str):
        since_dt = datetime.strptime(since[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    elif isinstance(since, date) and not isinstance(since, datetime):
        since_dt = datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc)
    else:
        since_dt = since

    async with pool.acquire() as connection:
        records = await connection.fetch(
            """
            SELECT id, company_id, source_id, normalized_data, consensus_data, retrieved_at
            FROM company_event_records
            WHERE company_id = $1 AND retrieved_at >= $2
            ORDER BY retrieved_at DESC
            """,
            company_id,
            since_dt
        )
        return records

async def cleanup_expired_records():
    async with pool.acquire() as connection:
        return await connection.fetchval("SELECT purge_expired_records();")


