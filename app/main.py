import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from app.database import init_db, close_db, save_event_record, get_company_events
from app.sources import get_sec_events, get_finnhub_events
from app.consensus import create_consensus

# managing database connection pool lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Company Intelligence Events API", version="1.0.0", lifespan=lifespan)


# serving standardized company events payload
@app.get("/v1/company/events")
async def get_events(
    company_id: str = Query(..., description="target company identifier"),
    since: str = Query(..., description="start date filter YYYY-MM-DD")
):
    start_time = time.perf_counter()
    now_utc = datetime.now(timezone.utc)
    served_at = now_utc.isoformat()

    sec_events = []
    finnhub_events = []
    warnings = []
    provenance = []

    # fetching live data from sec edgar provider
    try:
        sec_events = await get_sec_events(company_id, since)
        provenance.append({
            "source_id": "SRC-SEC-EDGAR",
            "publisher": "U.S. Securities and Exchange Commission",
            "retrieved_at": served_at
        })
    except Exception as err:
        warnings.append(f"SEC provider degraded: {str(err)}")

    # fetching live data from finnhub provider
    try:
        finnhub_events = await get_finnhub_events(company_id, since)
        provenance.append({
            "source_id": "SRC-FINNHUB-NEWS",
            "publisher": "Finnhub Financial API",
            "retrieved_at": served_at
        })
    except Exception as err:
        warnings.append(f"Finnhub provider degraded: {str(err)}")

    # raising error when both data providers fail completely
    if not sec_events and not finnhub_events and len(warnings) == 2:
        raise HTTPException(
            status_code=502,
            detail={"error": "upstream_provider_failure", "details": warnings}
        )

    # executing consensus verification and scoring
    consensus = create_consensus(sec_events, finnhub_events)

    # preparing timeline metadata and lifecycle parameters
    ttl_seconds = 86400
    expires_at = datetime.fromtimestamp(now_utc.timestamp() + ttl_seconds, timezone.utc)

    # persisting audit and record data into postgresql
    await save_event_record(
        company_id=company_id,
        source_id="CONSENSUS-ENGINE-V1",
        raw_payload={"sec": sec_events, "finnhub": finnhub_events},
        normalized_data={"events": consensus["events"]},
        consensus_data=consensus,
        audit_metadata={"warnings": warnings, "provenance": provenance},
        retrieved_at=now_utc,
        expires_at=expires_at
    )

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    # assembling standardized agent servicing payload
    return {
        "data": {
            "company_id": company_id,
            "events": consensus["events"]
        },
        "meta": {
            "request_id": f"req_{uuid.uuid4().hex[:16]}",
            "product_id": "company.intelligence.events.v1",
            "version": "1.0.0",
            "served_at": served_at,
            "source_last_updated_at": served_at,
            "freshness": {
                "age_seconds": 0,
                "ttl_seconds": ttl_seconds,
                "stale": False
            },
            "provenance": provenance,
            "trust": {
                "confidence": consensus["confidence"],
                "quality_score": consensus["quality_score"],
                "verified": consensus["verified"]
            },
            "license": {
                "type": "commercial",
                "usage": "agent_runtime"
            },
            "api": {
                "latency_ms": elapsed_ms,
                "rate_limit": {
                    "limit": 100,
                    "window_seconds": 60
                }
            },
            "warnings": warnings
        }
    }