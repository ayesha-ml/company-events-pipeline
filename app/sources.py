import os
from datetime import datetime, timezone
import httpx
from dotenv import load_dotenv

load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")


COMPANY = {
    "company_id": "NVDA",
    "name": "NVIDIA",
    "cik": "0001045810",
    "symbol": "NVDA"
}


SEC_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
FINNHUB_URL = "https://finnhub.io/api/v1/company-news"


def get_sec_events(since):
    url = SEC_URL.format(cik=COMPANY["cik"])

    headers = {
        "User-Agent": "Company Events Pipeline i232503@isb.nu.edu.pk"
    }

    response = httpx.get(
        url,
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"SEC request failed with status {response.status_code}"
        )

    data = response.json()

    filings = data.get("filings", {})
    recent = filings.get("recent", {})

    if not isinstance(recent, dict):
        raise RuntimeError("SEC returned an invalid response")

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])

    if not (
        isinstance(forms, list)
        and isinstance(dates, list)
        and isinstance(accession_numbers, list)
    ):
        raise RuntimeError("SEC returned invalid filing data")

    if not (
        len(forms) == len(dates)
        and len(dates) == len(accession_numbers)
    ):
        raise RuntimeError("SEC filing fields have different lengths")

    events = []

    for i in range(len(forms)):
        if dates[i] >= since:
            events.append(
                {
                    "type": "filing",
                    "form": forms[i],
                    "date": dates[i],
                    "accession_number": accession_numbers[i]
                }
            )

    return events


def get_finnhub_events(since):
    if not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY is not configured")

    today = datetime.now(timezone.utc).date().isoformat()

    params = {
        "symbol": COMPANY["symbol"],
        "from": since,
        "to": today,
        "token": FINNHUB_API_KEY
    }

    response = httpx.get(
        FINNHUB_URL,
        params=params,
        timeout=10
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Finnhub request failed with status {response.status_code}"
        )

    data = response.json()

    if not isinstance(data, list):
        raise RuntimeError("Finnhub returned an invalid response")

    events = []

    for item in data:
        if not isinstance(item, dict):
            raise RuntimeError("Finnhub returned an invalid news item")

        if "datetime" not in item:
            raise RuntimeError("Finnhub news item is missing datetime")

        try:
            event_date = datetime.fromtimestamp(
                item["datetime"],
                timezone.utc
            ).date().isoformat()
        except (TypeError, ValueError, OSError):
            raise RuntimeError("Finnhub returned an invalid datetime")

        events.append(
            {
                "type": "news",
                "date": event_date,
                "headline": item.get("headline"),
                "source": item.get("source"),
                "url": item.get("url")
            }
        )

    return events