import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_get_events_success_schema(monkeypatch):
    # testing endpoint payload structure and metadata against specification
    async def fake_sec(company_id, since):
        return [{"type": "filing", "date": "2026-08-10", "form": "8-K", "accession_number": "123"}]

    async def fake_finnhub(company_id, since):
        return [{"type": "news", "date": "2026-08-10", "headline": "Event headline", "source": "News", "url": "http://ex.com"}]

    async def fake_save(*args, **kwargs):
        pass

    monkeypatch.setattr("app.main.get_sec_events", fake_sec)
    monkeypatch.setattr("app.main.get_finnhub_events", fake_finnhub)
    monkeypatch.setattr("app.main.save_event_record", fake_save)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/company/events?company_id=NVDA&since=2026-08-01")

    assert response.status_code == 200
    json_data = response.json()

    assert "data" in json_data
    assert "meta" in json_data
    assert json_data["meta"]["trust"]["verified"] is True
    assert json_data["meta"]["freshness"]["stale"] is False


@pytest.mark.asyncio
async def test_source_failover_degradation(monkeypatch):
    # testing provider failure logging and degraded trust evaluation
    async def fake_sec(company_id, since):
        return [{"type": "filing", "date": "2026-08-10", "form": "8-K", "accession_number": "123"}]

    async def fake_finnhub_fail(company_id, since):
        raise RuntimeError("Finnhub rate limit exceeded")

    async def fake_save(*args, **kwargs):
        pass

    monkeypatch.setattr("app.main.get_sec_events", fake_sec)
    monkeypatch.setattr("app.main.get_finnhub_events", fake_finnhub_fail)
    monkeypatch.setattr("app.main.save_event_record", fake_save)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/company/events?company_id=NVDA&since=2026-08-01")

    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data["meta"]["warnings"]) == 1
    assert "Finnhub provider degraded" in json_data["meta"]["warnings"][0]
    assert json_data["meta"]["trust"]["confidence"] == 0.85