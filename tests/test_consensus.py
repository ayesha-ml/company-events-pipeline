from app.consensus import create_consensus

def test_matching_events():
    sec_events = [
        {
            "type": "filing",
            "date": "2026-08-10",
            "form": "8-K",
            "accession_number": "123"
        }
    ]

    finnhub_events = [
        {
            "type": "news",
            "date": "2026-08-10",
            "headline": "NVIDIA announces new company event",
            "source": "Test Source",
            "url": "https://example.com"
        }
    ]

    result = create_consensus(
        sec_events,
        finnhub_events
    )

    assert len(result["events"]) == 1
    assert result["events"][0]["type"] == "company_event"
    assert result["events"][0]["sources"] == ["SEC", "Finnhub"]
    assert result["confidence"] == 1.0
    assert result["quality_score"] == 1.0
    assert result["verified"] is True

def test_no_matching_date():
    sec_events = [
        {
            "type": "filing",
            "date": "2026-08-10",
            "form": "8-K",
            "accession_number": "123"
        }
    ]

    finnhub_events = [
        {
            "type": "news",
            "date": "2026-08-11",
            "headline": "NVIDIA company news",
            "source": "Test Source",
            "url": "https://example.com"
        }
    ]

    result = create_consensus(
        sec_events,
        finnhub_events
    )

    assert len(result["events"]) == 0
    assert result["confidence"] == 0.0
    assert result["quality_score"] == 0.0
    assert result["verified"] is False

def test_non_material_sec_form():
    sec_events = [
        {
            "type": "filing",
            "date": "2026-08-10",
            "form": "4",
            "accession_number": "123"
        }
    ]

    finnhub_events = [
        {
            "type": "news",
            "date": "2026-08-10",
            "headline": "NVIDIA company news",
            "source": "Test Source",
            "url": "https://example.com"
        }
    ]

    result = create_consensus(
        sec_events,
        finnhub_events
    )

    assert len(result["events"]) == 0
    assert result["verified"] is False

def test_non_nvidia_news():
    sec_events = [
        {
            "type": "filing",
            "date": "2026-08-10",
            "form": "8-K",
            "accession_number": "123"
        }
    ]

    finnhub_events = [
        {
            "type": "news",
            "date": "2026-08-10",
            "headline": "Apple announces new product",
            "source": "Test Source",
            "url": "https://example.com"
        }
    ]

    result = create_consensus(
        sec_events,
        finnhub_events
    )

    assert len(result["events"]) == 0
    assert result["verified"] is False

def test_empty_sources():
    result = create_consensus([], [])

    assert result["events"] == []
    assert result["confidence"] == 0.0
    assert result["quality_score"] == 0.0
    assert result["verified"] is False