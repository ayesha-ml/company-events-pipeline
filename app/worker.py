import asyncio
import logging
from datetime import datetime, timezone, timedelta
from app.database import init_db, close_db, save_event_record, cleanup_expired_records
from app.sources import get_sec_events, get_finnhub_events
from app.consensus import create_consensus

# logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("ingestion_worker")

# company registry to poll continuously
COMPANY_REGISTRY = ["NVDA", "AAPL", "MSFT"]


async def process_company_ingestion(company_id: str, lookback_days: int = 30):
    """fetches live micro-data for a company, computes consensus, and stores in postgresql"""
    now_utc = datetime.now(timezone.utc)
    served_at = now_utc.isoformat()
    since_date = (now_utc - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    sec_events = []
    finnhub_events = []
    warnings = []
    provenance = []

    # fetching live sec filings
    try:
        sec_events = await get_sec_events(company_id, since_date)
        provenance.append({
            "source_id": "SRC-SEC-EDGAR",
            "publisher": "U.S. Securities and Exchange Commission",
            "retrieved_at": served_at
        })
    except Exception as err:
        warnings.append(f"SEC provider degraded: {str(err)}")
        logger.warning(f"[{company_id}] SEC ingestion failed: {err}")

    # fetching live finnhub news
    try:
        finnhub_events = await get_finnhub_events(company_id, since_date)
        provenance.append({
            "source_id": "SRC-FINNHUB-NEWS",
            "publisher": "Finnhub Financial API",
            "retrieved_at": served_at
        })
    except Exception as err:
        warnings.append(f"Finnhub provider degraded: {str(err)}")
        logger.warning(f"[{company_id}] Finnhub ingestion failed: {err}")

    # computing dynamic consensus and trust scores
    consensus = create_consensus(sec_events, finnhub_events)

    # setting lifecycle parameters (24 hours ttl)
    ttl_seconds = 86400
    expires_at = now_utc + timedelta(seconds=ttl_seconds)

    # saving normalized record into postgresql
    await save_event_record(
        company_id=company_id,
        source_id="WORKER-INGESTION-V1",
        raw_payload={"sec": sec_events, "finnhub": finnhub_events},
        normalized_data={"events": consensus["events"]},
        consensus_data=consensus,
        audit_metadata={"warnings": warnings, "provenance": provenance},
        retrieved_at=now_utc,
        expires_at=expires_at
    )

    logger.info(
        f"[{company_id}] Ingestion complete. "
        f"Events found: {len(consensus['events'])}, "
        f"Confidence: {consensus['confidence']}, "
        f"Warnings: {len(warnings)}"
    )


async def run_worker_loop(interval_seconds: int = 3600):
    """continuous worker loop executing periodic ingestion and database ttl cleanup"""
    logger.info("Starting background ingestion worker service...")
    await init_db()

    try:
        while True:
            logger.info("Starting background ingestion cycle across registered companies...")
            
            # running ingestion across registry
            for company_id in COMPANY_REGISTRY:
                try:
                    await process_company_ingestion(company_id)
                except Exception as err:
                    logger.error(f"[{company_id}] Unhandled error during worker cycle: {err}")

            # running database ttl cleanup to purge expired records
            try:
                deleted_rows = await cleanup_expired_records()
                if deleted_rows > 0:
                    logger.info(f"TTL Cleanup: Purged {deleted_rows} expired record(s).")
            except Exception as err:
                logger.error(f"TTL Cleanup failed: {err}")

            logger.info(f"Ingestion cycle completed. Sleeping for {interval_seconds} seconds...")
            await asyncio.sleep(interval_seconds)

    except asyncio.CancelledError:
        logger.info("Worker service cancellation requested.")
    finally:
        logger.info("Closing database connections...")
        await close_db()


if __name__ == "__main__":
    # polling every hour (3600 seconds)
    try:
        asyncio.run(run_worker_loop(interval_seconds=3600))
    except KeyboardInterrupt:
        logger.info("Worker stopped manually by user.")