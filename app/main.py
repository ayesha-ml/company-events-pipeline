import time
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException, Query

from app.sources import COMPANY, get_sec_events, get_finnhub_events
from app.consensus import create_consensus
from app.database import save_event_record


app = FastAPI()


@app.get("/v1/company/events")
async def get_company_events(
    company_id: str = Query(...),
    since: str = Query(...)
):
    start_time = time.perf_counter()

    request_id = "req_" + uuid.uuid4().hex[:12]

    # check company
    if company_id != COMPANY["company_id"]:
        raise HTTPException(
            status_code=404,
            detail="Company is not supported"
        )

    # check date format
    try:
        datetime.strptime(since, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="since must use YYYY-MM-DD format"
        )

    retrieved_at = datetime.now(timezone.utc)
    expires_at = retrieved_at + timedelta(days=1)

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

    # both sources failed
    if sec_failed and finnhub_failed:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Both sources are unavailable",
                "request_id": request_id,
                "warnings": warnings
            }
        )

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

    # combine source events
    all_events = sec_events + finnhub_events

    # source data was retrieved just now
    source_last_updated_at = retrieved_at

    age_seconds = 0
    ttl_seconds = 86400
    stale = False

    # calculate API latency
    latency_ms = round(
        (time.perf_counter() - start_time) * 1000,
        2
    )

    # store data in PostgreSQL
    raw_payload = {
        "sec": sec_events,
        "finnhub": finnhub_events
    }

    normalized_data = {
        "sec_events": sec_events,
        "finnhub_events": finnhub_events
    }

    audit_metadata = {
        "request_id": request_id,
        "since": since,
        "retrieved_at": retrieved_at.isoformat(),
        "warnings": warnings
    }

    await save_event_record(
        company_id,
        "SEC+Finnhub",
        raw_payload,
        normalized_data,
        consensus,
        audit_metadata,
        retrieved_at,
        expires_at
    )

    # add only successful sources to provenance
    provenance = []

    if not sec_failed:
        provenance.append(
            {
                "source_id": "SRC-SEC-001",
                "publisher": "SEC EDGAR",
                "retrieved_at": retrieved_at.isoformat()
            }
        )

    if not finnhub_failed:
        provenance.append(
            {
                "source_id": "SRC-FINNHUB-001",
                "publisher": "Finnhub",
                "retrieved_at": retrieved_at.isoformat()
            }
        )

    # final API response
    response = {
        "data": {
            "company_id": company_id,
            "company_name": COMPANY["name"],
            "events": all_events,
            "verified_events": consensus["events"]
        },
        "meta": {
            "request_id": request_id,
            "product_id": "company.events.v1",
            "version": "1.0.0",
            "served_at": retrieved_at.isoformat(),
            "source_last_updated_at": source_last_updated_at.isoformat(),
            "freshness": {
                "age_seconds": age_seconds,
                "ttl_seconds": ttl_seconds,
                "stale": stale
            },
            "provenance": provenance,
            "trust": {
                "confidence": consensus["confidence"],
                "quality_score": consensus["quality_score"],
                "verified": consensus["verified"]
            },
            "license": {
                "type": "unknown",
                "usage": "agent_runtime"
            },
            "api": {
                "latency_ms": latency_ms,
                "rate_limit": {
                    "limit": None,
                    "window_seconds": None
                }
            },
            "warnings": warnings
        }
    }

    return response