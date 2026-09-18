import pytest
import app.sources as sources


class FakeAsyncResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


@pytest.mark.asyncio
async def test_sec_events(monkeypatch):
    # testing sec events parsing and form filtering
    data = {
        "filings": {
            "recent": {
                "form": ["8-K", "10-Q"],
                "filingDate": ["2026-08-10", "2026-07-20"],
                "accessionNumber": ["0000000000-26-000001", "0000000000-26-000002"]
            }
        }
    }

    async def fake_get(*args, **kwargs):
        return FakeAsyncResponse(200, data)

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    events = await sources.get_sec_events("NVDA", "2026-08-01")
    assert len(events) == 1
    assert events[0]["type"] == "executive_change"
    assert events[0]["date"] == "2026-08-10"


@pytest.mark.asyncio
async def test_finnhub_events(monkeypatch):
    # testing finnhub news parsing using 2026 timestamp
    data = [{
        "datetime": 1786320000, 
        "headline": "NVIDIA announces quarterly results",
        "source": "Financial Wire",
        "url": "https://example.com/news"
    }]

    async def fake_get(*args, **kwargs):
        return FakeAsyncResponse(200, data)

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    events = await sources.get_finnhub_events("NVDA", "2026-08-01")
    assert len(events) == 1
    assert events[0]["type"] == "news"


@pytest.mark.asyncio
async def test_source_failure(monkeypatch):
    # testing HTTP error handling when provider returns failure status
    async def fake_get(*args, **kwargs):
        return FakeAsyncResponse(500, {})

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    with pytest.raises(RuntimeError):
        await sources.get_sec_events("NVDA", "2026-08-01")