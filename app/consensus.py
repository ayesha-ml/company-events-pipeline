MATERIAL_SEC_FORMS = {
    "8-K",
    "10-K",
    "10-Q",
    "20-F",
    "6-K",
    "DEF 14A"
}


def create_consensus(sec_events, finnhub_events):
    material_sec_events = []
    nvidia_news = []

    # keep material SEC filings
    for event in sec_events:
        if event.get("form") in MATERIAL_SEC_FORMS:
            material_sec_events.append(event)

    # keep NVIDIA-specific news
    for event in finnhub_events:
        headline = (event.get("headline") or "").lower()

        if "nvidia" in headline or "nvda" in headline:
            nvidia_news.append(event)

    consensus_events = []

    # comparing SEC events and news using the date
    for sec_event in material_sec_events:
        for news_event in nvidia_news:

            if sec_event.get("date") == news_event.get("date"):
                consensus_events.append(
                    {
                        "type": "company_event",
                        "date": sec_event["date"],
                        "sources": ["SEC", "Finnhub"],
                        "sec_form": sec_event.get("form"),
                        "sec_accession_number": sec_event.get(
                            "accession_number"
                        ),
                        "headline": news_event.get("headline"),
                        "news_source": news_event.get("source"),
                        "news_url": news_event.get("url")
                    }
                )

    #scores
    if consensus_events:
        confidence = 1.0
        quality_score = 1.0
        verified = True
    else:
        confidence = 0.0
        quality_score = 0.0
        verified = False

    return {
        "events": consensus_events,
        "confidence": confidence,
        "quality_score": quality_score,
        "verified": verified
    }