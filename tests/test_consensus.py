from app.consensus import create_consensus

def test_matching_events():
    sec_events = [
        {
            "type": "executive_change",
            "date": "2026-08-10",
            "form": "8-K",
            "accession_number": "123"
        }
    ]

    finnhub_events = [
        {
            "type": "executive_change",
            "date": "2026-08-10",
            "headline": "NVIDIA announces executive change",
            "source": "Test Source",
            "url": "https://example.com"
        }
    ]

    result = create_consensus(sec_events, finnhub_events)

    assert len(result["events"]) == 1
    assert result["confidence"] == 1.0
    assert result["quality_score"] == 1.0
    assert result["verified"] is True

def test_no_matching_events():
    sec_events = [
        {
            "type": "executive_change",
            "date": "2026-08-10",
            "form": "8-K",
            "accession_number": "123"
        }
    ]

    finnhub_events = [
        {
            "type": "funding",
            "date": "2026-08-11",
            "headline": "NVIDIA news",
            "source": "Test Source",
            "url": "https://example.com"
        }
    ]

    result = create_consensus(sec_events, finnhub_events)

    assert len(result["events"]) == 0
    assert result["verified"] is False

def test_empty_sources():
    result = create_consensus([], [])

    assert result["events"] == []
    assert result["verified"] is False