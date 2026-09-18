MATERIAL_SEC_FORMS = {
    "8-K",
    "10-K",
    "10-Q",
    "20-F",
    "6-K",
    "DEF 14A"
}

FORM_TYPE_MAP = {
    "8-K": "executive_change_or_material_event",
    "10-K": "annual_report",
    "10-Q": "quarterly_report",
    "20-F": "foreign_annual_report",
    "6-K": "foreign_interim_report",
    "DEF 14A": "proxy_statement"
}


def create_consensus(sec_events: list[dict], finnhub_events: list[dict]) -> dict:
    """processing multi-source event data and building consensus metrics"""
    # filtering material sec filings and valid news records
    material_sec = [e for e in sec_events if e.get("form") in MATERIAL_SEC_FORMS]
    valid_news = [e for e in finnhub_events if e.get("date")]

    merged_events = []
    matched_news_indices = set()

    # reconciling official sec filings with news reports
    for sec in material_sec:
        sec_date = sec.get("date")
        sec_form = sec.get("form")

        matching_news = None
        for idx, news in enumerate(valid_news):
            if idx not in matched_news_indices and news.get("date") == sec_date:
                matching_news = news
                matched_news_indices.add(idx)
                break

        if matching_news:
            merged_events.append({
                "type": FORM_TYPE_MAP.get(sec_form, "company_event"),
                "date": sec_date,
                "sec_form": sec_form,
                "sec_accession_number": sec.get("accession_number"),
                "headline": matching_news.get("headline"),
                "news_source": matching_news.get("source"),
                "news_url": matching_news.get("url"),
                "sources": ["SEC", "Finnhub"],
                "status": "dual_verified"
            })
        else:
            merged_events.append({
                "type": FORM_TYPE_MAP.get(sec_form, "company_event"),
                "date": sec_date,
                "sec_form": sec_form,
                "sec_accession_number": sec.get("accession_number"),
                "sources": ["SEC"],
                "status": "sec_only"
            })

    # appending standalone news reports not matching any filing
    for idx, news in enumerate(valid_news):
        if idx not in matched_news_indices:
            merged_events.append({
                "type": "news_announcement",
                "date": news.get("date"),
                "headline": news.get("headline"),
                "news_source": news.get("source"),
                "news_url": news.get("url"),
                "sources": ["Finnhub"],
                "status": "news_only"
            })

    # returning empty structure when finding no events
    if not merged_events:
        return {
            "events": [],
            "confidence": 0.0,
            "quality_score": 0.0,
            "verified": False
        }

    # computing overall confidence and quality metrics
    scores = []
    for ev in merged_events:
        if ev["status"] == "dual_verified":
            scores.append(1.0)
        elif ev["status"] == "sec_only":
            scores.append(0.85)
        else:
            scores.append(0.60)

    avg_confidence = round(sum(scores) / len(scores), 2)
    dual_ratio = sum(1 for ev in merged_events if ev["status"] == "dual_verified") / len(merged_events)
    quality_score = round(min(1.0, 0.70 + (0.30 * dual_ratio)), 2)
    verified = any(ev["status"] in ["dual_verified", "sec_only"] for ev in merged_events)

    return {
        "events": merged_events,
        "confidence": avg_confidence,
        "quality_score": quality_score,
        "verified": verified
    }