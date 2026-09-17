import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    return await asyncpg.connect(DATABASE_URL)


async def save_event_record(
    company_id,
    source_id,
    raw_payload,
    normalized_data,
    consensus_data,
    audit_metadata,
    retrieved_at,
    expires_at,
):
    connection = await get_connection()

    try:
        await connection.execute(
            """
            INSERT INTO company_event_records (
                company_id,
                source_id,
                raw_payload,
                normalized_data,
                consensus_data,
                audit_metadata,
                retrieved_at,
                expires_at
            )
            VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, $7, $8)
            """,
            company_id,
            source_id,
            raw_payload,
            normalized_data,
            consensus_data,
            audit_metadata,
            retrieved_at,
            expires_at,
        )
    finally:
        await connection.close()


async def cleanup_expired_records():
    connection = await get_connection()

    try:
        deleted_count = await connection.fetchval(
            "SELECT purge_expired_records();"
        )
        return deleted_count
    finally:
        await connection.close()
