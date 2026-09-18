# High-Performance Data Engineering Pipeline

An asynchronous FastAPI data pipeline that ingests, reconciles, and stores financial event data from SEC EDGAR and Finnhub in real-time.

## Architecture & Features

* **Asynchronous Ingestion:** Concurrent fetching from SEC EDGAR and Finnhub via `httpx`.
* **Consensus Engine:** In-memory reconciliation, deduplication, and confidence scoring.
* **Storage & Lifecycle:** Write-through persistence to PostgreSQL JSONB with automated TTL purging and GIN indexing.
* **SLA & Performance:** Sub-200ms p95 response time tracked via `time.perf_counter()`.
* **Resilience:** Explicit 502 error handling for upstream failures with zero silent fallbacks.

## Project Structure

```text
.
├── app/                  # Main application code (main, consensus, sources, database)
├── sql/                  # Schema, JSONB indexes, and TTL purge functions
├── scripts/              # TTL verification & utility scripts
├── tests/                # Automated pytest test suite (12 test cases)
├── requirements.txt      # Dependency manifest
└── README.md

## Quick Start

1. Install Dependencies
pip install -r requirements.txt

2. Run Application
uvicorn app.main:app --reload

3. Run Test Suite
pytest -v
