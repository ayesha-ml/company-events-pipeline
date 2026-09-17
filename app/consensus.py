def create_consensus(sec_events, finnhub_events):
    consensus_events = []

    for sec_event in sec_events:
        for news_event in finnhub_events:
            if (
                sec_event.get("type") == news_event.get("type")
                and sec_event.get("date") == news_event.get("date")
            ):
                consensus_events.append(
                    {
                        "type": sec_event["type"],
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

    if consensus_events:
        confidence = 1.0
        quality_score = 1.0
        verified = True
    else:
        confidence = 0.5
        quality_score = 0.5
        verified = False

    return {
        "events": consensus_events,
        "confidence": confidence,
        "quality_score": quality_score,
        "verified": verified
    }