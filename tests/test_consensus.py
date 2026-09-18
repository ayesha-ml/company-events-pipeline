from app.consensus import create_consensus


def test_matching_dual_source_events():
    # testing dual source event verification when matching sec filing with news
    sec_events = [{
        "type": "filing",
        "date": "2026-08-10",
        "form": "8-K",
        "accession_number": "123"
    }]
    finnhub_events = [{
        "type": "news",
        "date": "2026-08-10",
        "headline": "Company announces quarterly leadership changes",
        "source": "Wire",
        "url": "https://example.com"
    }]

    result = create_consensus(sec_events, finnhub_events)

    assert len(result["events"]) == 1
    assert result["events"][0]["status"] == "dual_verified"
    assert result["confidence"] == 1.0
    assert result["quality_score"] == 1.0
    assert result["verified"] is True


def test_sec_only_event_failover():
    # verifying fallback behavior when receiving only sec filings
    sec_events = [{
        "type": "filing",
        "date": "2026-08-10",
        "form": "8-K",
        "accession_number": "123"
    }]

    result = create_consensus(sec_events, [])

    assert len(result["events"]) == 1
    assert result["events"][0]["status"] == "sec_only"
    assert result["confidence"] == 0.85
    assert result["verified"] is True


def test_non_material_sec_form_filtering():
    # checking filtering out of non-material sec forms
    sec_events = [{
        "type": "filing",
        "date": "2026-08-10",
        "form": "4",
        "accession_number": "123"
    }]

    result = create_consensus(sec_events, [])

    assert len(result["events"]) == 0
    assert result["confidence"] == 0.0
    assert result["verified"] is False


def test_empty_sources():
    # evaluating response structure when processing empty input streams
    result = create_consensus([], [])

    assert result["events"] == []
    assert result["confidence"] == 0.0
    assert result["quality_score"] == 0.0
    assert result["verified"] is False