import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from datetime import datetime, timezone, timedelta
from app import database

async def test_ttl_purging():
    await database.init_db()
    
    now = datetime.now(timezone.utc)
    past_expiration = now - timedelta(hours=1)
    
    # inserting an expired test record
    await database.save_event_record(
        company_id="PURGE_TEST",
        source_id="TEST_SRC",
        raw_payload={},
        normalized_data={"events": []},
        consensus_data={},
        audit_metadata={},
        retrieved_at=now - timedelta(hours=25),
        expires_at=past_expiration
    )
    print("Inserted expired test record.")

    # executing database cleanup function
    deleted_rows = await database.cleanup_expired_records()
    print(f"Purge output: {deleted_rows} expired row(s) deleted.")

    # checking if test record was removed
    async with database.pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM company_event_records WHERE company_id = $1", 
            "PURGE_TEST"
        )
    await database.close_db()

    if count == 0:
        print("SUCCESS: Expired record was successfully purged from PostgreSQL!")
    else:
        print("FAILURE: Expired record still exists in database.")

if __name__ == "__main__":
    asyncio.run(test_ttl_purging())
