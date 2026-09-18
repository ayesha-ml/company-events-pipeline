import os
from datetime import datetime, timezone
import httpx
from dotenv import load_dotenv

load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

COMPANY_REGISTRY = {
    "NVDA": {"cik": "0001045810", "symbol": "NVDA", "name": "NVIDIA"},
    "AAPL": {"cik": "0000320193", "symbol": "AAPL", "name": "Apple"},
    "MSFT": {"cik": "0000789019", "symbol": "MSFT", "name": "Microsoft"},
    "12345": {"cik": "0001045810", "symbol": "NVDA", "name": "NVIDIA"}  
}

SEC_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
FINNHUB_URL = "https://finnhub.io/api/v1/company-news"

def _resolve_company(company_id: str) -> dict:
    company = COMPANY_REGISTRY.get(company_id.upper())
    if not company:
        raise ValueError(f"Unsupported company_id: {company_id}")
    return company

async def get_sec_events(company_id: str, since: str) -> list[dict]:
    company = _resolve_company(company_id)
    url = SEC_URL.format(cik=company["cik"])
    headers = {"User-Agent": "Company Events Pipeline i232503@isb.nu.edu.pk"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
        except httpx.RequestError as exc:
            raise RuntimeError(f"SEC connection error: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(f"SEC request failed with status {response.status_code}")

    data = response.json()
    recent = data.get("filings", {}).get("recent", {})

    if not isinstance(recent, dict):
        raise RuntimeError("SEC returned an invalid response structure")

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])

    if not (isinstance(forms, list) and isinstance(dates, list) and isinstance(accession_numbers, list)):
        raise RuntimeError("SEC filing lists are malformed")

    if not (len(forms) == len(dates) == len(accession_numbers)):
        raise RuntimeError("SEC filing field lengths mismatch")

    events = []
    for i in range(len(forms)):
        if dates[i] >= since:
            event_type = "executive_change" if forms[i] == "8-K" else "filing"
            events.append({
                "type": event_type,
                "form": forms[i],
                "date": dates[i],
                "accession_number": accession_numbers[i],
                "company_id": company_id
            })

    return events

async def get_finnhub_events(company_id: str, since: str) -> list[dict]:
    if not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY is not configured")

    company = _resolve_company(company_id)
    today = datetime.now(timezone.utc).date().isoformat()
    params = {
        "symbol": company["symbol"],
        "from": since,
        "to": today,
        "token": FINNHUB_API_KEY
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(FINNHUB_URL, params=params, timeout=10.0)
        except httpx.RequestError as exc:
            raise RuntimeError(f"Finnhub connection error: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(f"Finnhub request failed with status {response.status_code}")

    data = response.json()
    if not isinstance(data, list):
        raise RuntimeError("Finnhub returned an invalid response format")

    events = []
    for item in data:
        if not isinstance(item, dict) or "datetime" not in item:
            raise RuntimeError("Finnhub event item is malformed")

        try:
            event_date = datetime.fromtimestamp(item["datetime"], timezone.utc).date().isoformat()
        except (TypeError, ValueError, OSError) as exc:
            raise RuntimeError("Finnhub timestamp conversion failed") from exc

        if event_date >= since:
            events.append({
                "type": "news",
                "date": event_date,
                "headline": item.get("headline"),
                "source": item.get("source"),
                "url": item.get("url"),
                "company_id": company_id
            })

    return events