"""
sec_fetcher.py
Takes a ticker + date range, queries SEC via sec-api SDK, returns filing URLs.
"""

from sec_api import QueryApi
from config import SEC_API_KEY


def fetch_filing_urls(ticker: str, start_date: str, end_date: str) -> list[dict]:
    """
    Queries sec-api for 10-K, 10-Q, 8-K filings for the given ticker
    between start_date and end_date (format: "YYYY-MM-DD").

    Returns a list of dicts:
        [{ "form_type", "filed_at", "period_of_report", "url" }, ...]
    """
    query_api = QueryApi(api_key=SEC_API_KEY)

    query = {
        "query": {
            "query_string": {
                "query": f"""
                    ticker:{ticker} AND
                    (formType:"10-K" OR formType:"10-Q" OR formType:"8-K") AND
                    filedAt:[{start_date} TO {end_date}]
                """
            }
        },
        "from": 0,
        "size": 50,
        "sort": [{"filedAt": {"order": "desc"}}]
    }

    response = query_api.get_filings(query)
    filings = response.get("filings", [])

    return [
        {
            "form_type": f.get("formType", ""),
            "filed_at": f.get("filedAt", "")[:10],
            "period_of_report": f.get("periodOfReport", ""),
            "url": f.get("linkToFilingDetails", ""),
        }
        for f in filings
        if f.get("linkToFilingDetails")
    ]