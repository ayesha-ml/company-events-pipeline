import time
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_get_events_schema_and_freshness(monkeypatch):
    # mocking upstream providers and database persistence
    async def fake_sec(company_id, since):
        return [{"type": "filing", "date": "2026-08-10", "form": "8-K", "accession_number": "123"}]

    async def fake_finnhub(company_id, since):
        return [{"type": "news", "date": "2026-08-10", "headline": "event headline", "source": "news", "url": "http://ex.com"}]

    async def fake_save(*args, **kwargs):
        pass

    monkeypatch.setattr("app.main.get_sec_events", fake_sec)
    monkeypatch.setattr("app.main.get_finnhub_events", fake_finnhub)
    monkeypatch.setattr("app.main.save_event_record", fake_save)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/company/events?company_id=NVDA&since=2026-08-01")

    # checking schema compliance and trust flags
    assert response.status_code == 200
    json_data = response.json()

    assert "data" in json_data
    assert "meta" in json_data
    assert json_data["meta"]["trust"]["verified"] is True
    assert json_data["meta"]["freshness"]["stale"] is False


@pytest.mark.asyncio
async def test_source_failover_degradation(monkeypatch):
    async def fake_sec(company_id, since):
        return [{"type": "filing", "date": "2026-08-10", "form": "8-K", "accession_number": "123"}]

    # simulating upstream provider error
    async def fake_finnhub_fail(company_id, since):
        raise RuntimeError("finnhub rate limit exceeded")

    async def fake_save(*args, **kwargs):
        pass

    monkeypatch.setattr("app.main.get_sec_events", fake_sec)
    monkeypatch.setattr("app.main.get_finnhub_events", fake_finnhub_fail)
    monkeypatch.setattr("app.main.save_event_record", fake_save)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/company/events?company_id=NVDA&since=2026-08-01")

    # validating degraded response state and warnings
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data["meta"]["warnings"]) == 1
    assert "Finnhub provider degraded" in json_data["meta"]["warnings"][0]
    assert json_data["meta"]["trust"]["confidence"] == 0.85


@pytest.mark.asyncio
async def test_p95_latency_sla(monkeypatch):
    async def fake_sec(company_id, since):
        return [{"type": "filing", "date": "2026-08-10", "form": "8-K", "accession_number": "123"}]

    async def fake_finnhub(company_id, since):
        return [{"type": "news", "date": "2026-08-10", "headline": "event headline", "source": "news", "url": "http://ex.com"}]

    async def fake_save(*args, **kwargs):
        pass

    monkeypatch.setattr("app.main.get_sec_events", fake_sec)
    monkeypatch.setattr("app.main.get_finnhub_events", fake_finnhub)
    monkeypatch.setattr("app.main.save_event_record", fake_save)

    # executing polling requests to measure response duration
    transport = ASGITransport(app=app)
    latencies = []

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(25):
            start = time.perf_counter()
            res = await client.get("/v1/company/events?company_id=NVDA&since=2026-08-01")
            latencies.append(time.perf_counter() - start)
            assert res.status_code == 200

    # evaluating 95th percentile latency threshold
    latencies.sort()
    p95_index = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_index]
    assert p95_latency < 0.20


@pytest.mark.asyncio
async def test_freshness_sla_enforcement(monkeypatch):
    async def fake_sec(company_id, since):
        return [{"type": "filing", "date": "2026-08-10", "form": "8-K", "accession_number": "123"}]

    async def fake_finnhub(company_id, since):
        return [{"type": "news", "date": "2026-08-10", "headline": "event headline", "source": "news", "url": "http://ex.com"}]

    async def fake_save(*args, **kwargs):
        pass

    monkeypatch.setattr("app.main.get_sec_events", fake_sec)
    monkeypatch.setattr("app.main.get_finnhub_events", fake_finnhub)
    monkeypatch.setattr("app.main.save_event_record", fake_save)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/v1/company/events?company_id=NVDA&since=2026-08-01")

    # verifying data age against defined time to live limit
    freshness = res.json()["meta"]["freshness"]
    assert freshness["age_seconds"] <= freshness["ttl_seconds"]
    assert freshness["stale"] is False