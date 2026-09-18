import asyncio
from datetime import datetime, timezone, timedelta

from app.sources import COMPANY, get_sec_events, get_finnhub_events
from app.consensus import create_consensus
from app.database import save_event_record, cleanup_expired_records


INGESTION_INTERVAL = 86400


async def run_ingestion():
    since = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).date().isoformat()

    warnings = []

    sec_events = []
    finnhub_events = []

    sec_failed = False
    finnhub_failed = False

    # get SEC data
    try:
        sec_events = get_sec_events(since)
    except RuntimeError as error:
        sec_failed = True
        warnings.append(f"SEC source unavailable: {error}")

    # get Finnhub data
    try:
        finnhub_events = get_finnhub_events(since)
    except RuntimeError as error:
        finnhub_failed = True
        warnings.append(f"Finnhub source unavailable: {error}")

    # do not store anything if both sources failed
    if sec_failed and finnhub_failed:
        print("Both sources are unavailable")
        return

    # create consensus
    consensus = create_consensus(
        sec_events,
        finnhub_events
    )

    # reduce trust when one source failed
    if sec_failed or finnhub_failed:
        consensus["confidence"] = 0.5
        consensus["quality_score"] = 0.5
        consensus["verified"] = False

    retrieved_at = datetime.now(timezone.utc)
    expires_at = retrieved_at + timedelta(seconds=INGESTION_INTERVAL)

    # store raw source data
    raw_payload = {
        "sec": sec_events,
        "finnhub": finnhub_events
    }

    # store normalized source data
    normalized_data = {
        "sec_events": sec_events,
        "finnhub_events": finnhub_events
    }

    # store audit information
    audit_metadata = {
        "retrieved_at": retrieved_at.isoformat(),
        "since": since,
        "warnings": warnings
    }

    await save_event_record(
        COMPANY["company_id"],
        "SEC+Finnhub",
        raw_payload,
        normalized_data,
        consensus,
        audit_metadata,
        retrieved_at,
        expires_at
    )

    print(
        f"Ingestion completed at {retrieved_at.isoformat()}"
    )


async def run_worker():
    while True:
        try:
            await run_ingestion()
            await cleanup_expired_records()
        except Exception as error:
            print(f"Worker error: {error}")

        await asyncio.sleep(INGESTION_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_worker())