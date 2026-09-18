import pytest
from datetime import datetime, timezone, timedelta
from app.database import init_db, close_db, save_event_record, cleanup_expired_records, get_company_events


@pytest.mark.asyncio
async def test_database_lifecycle():
    # testing database initialization, insertion, query, and cleanup
    await init_db()

    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(hours=24)

    try:
        await save_event_record(
            company_id="TEST_CO",
            source_id="TEST_SRC",
            raw_payload={"test": "data"},
            normalized_data={"events": []},
            consensus_data={"confidence": 0.95},
            audit_metadata={},
            retrieved_at=now_utc,
            expires_at=expires_at
        )

        records = await get_company_events("TEST_CO", "2026-01-01")
        assert len(records) >= 1

        deleted_count = await cleanup_expired_records()
        assert isinstance(deleted_count, int)
    finally:
        await close_db()