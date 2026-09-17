import pytest
import app.sources as sources

class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self.data = data

    def json(self):
        return self.data


def test_sec_events(monkeypatch):
    data = {
        "filings": {
            "recent": {
                "form": ["8-K", "10-Q"],
                "filingDate": ["2026-08-10", "2026-07-20"],
                "accessionNumber": [
                    "0000000000-26-000001",
                    "0000000000-26-000002"
                ]
            }
        }
    }

    def fake_get(*args, **kwargs):
        return FakeResponse(200, data)

    monkeypatch.setattr(sources.httpx, "get", fake_get)

    events = sources.get_sec_events("2026-08-01")

    assert len(events) == 1
    assert events[0]["type"] == "filing"
    assert events[0]["date"] == "2026-08-10"


def test_finnhub_events(monkeypatch):
    data = [
        {
            "datetime": 1754784000,
            "headline": "NVIDIA announces new product",
            "source": "Test Source",
            "url": "https://example.com/news"
        }
    ]

    def fake_get(*args, **kwargs):
        return FakeResponse(200, data)

    monkeypatch.setattr(sources.httpx, "get", fake_get)

    events = sources.get_finnhub_events("2026-08-01")

    assert len(events) == 1
    assert events[0]["type"] == "news"
    assert events[0]["headline"] == "NVIDIA announces new product"


def test_source_failure(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(500, {})

    monkeypatch.setattr(sources.httpx, "get", fake_get)

    with pytest.raises(RuntimeError):
        sources.get_sec_events("2026-08-01")


def test_bad_source_data(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(200, {"invalid": "data"})

    monkeypatch.setattr(sources.httpx, "get", fake_get)

    with pytest.raises(RuntimeError):
        sources.get_finnhub_events("2026-08-01")