"""
summarizer.py

Two steps:
1. fetch_filings_content()  — sends all SEC filing URLs to GPT-4.1 (web_search_preview)
                              which fetches + reads each one and returns extracted insights.
2. synthesize_report()      — compiles filing insights + yfinance market data into a
                              final investor briefing via GPT-4.1 chat completion.
"""

from openai import OpenAI
from config import OPENAI_API_KEY, GPT_WEB_SEARCH_MODEL, GPT_SUMMARY_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# Step 1: GPT-4.1 web-fetches all filing URLs and extracts key insights
# ---------------------------------------------------------------------------

def fetch_filings_content(ticker: str, filings: list[dict]) -> str:
    """
    Passes all filing URLs to GPT-4.1 with web_search_preview enabled.
    GPT fetches each URL and returns a consolidated extraction of key points.

    filings: list of dicts from sec_fetcher.fetch_filing_urls()
             [{ "form_type", "filed_at", "period_of_report", "url" }, ...]

    Returns: raw string of extracted insights from all filings.
    """
    if not filings:
        return "No filings found for this ticker in the selected date range."

    # Build a clear list of URLs for GPT to fetch
    filings_list = "\n".join(
        f"- [{f['form_type']} | Filed: {f['filed_at']} | Period: {f['period_of_report']}] {f['url']}"
        for f in filings
    )

    prompt = f"""You are a financial analyst. Below is a list of SEC filings for {ticker}.
Please visit each URL, read the filing, and extract the key information.

{filings_list}

For each filing, extract:
- **10-K**: Revenue, net income, EPS, YoY changes, key risks, business highlights, forward guidance
- **10-Q**: Quarterly financials, notable changes vs prior quarter/year, management commentary
- **8-K**: Event description, financial impact, material disclosures

Format your response as:
### [FORM TYPE] — [Filed Date]
<bullet points of key findings>

Be thorough but concise. Focus on what matters to an investor."""

    response = client.responses.create(
        model=GPT_WEB_SEARCH_MODEL,
        tools=[{"type": "web_search_preview"}],
        input=prompt,
    )

    # Extract text from response output blocks
    result = ""
    for item in response.output:
        if hasattr(item, "content"):
            for block in item.content:
                if hasattr(block, "text"):
                    result += block.text

    return result.strip() or "Could not extract content from filings."


# ---------------------------------------------------------------------------
# Step 2: Synthesize filing insights + market data into final report
# ---------------------------------------------------------------------------

def synthesize_report(
    ticker: str,
    filings_content: str,
    price_summary: dict,
    financials: dict,
) -> str:
    """
    Combines the extracted filing content with yfinance market data
    and produces a structured investor briefing report via GPT-4.1.
    """

    market_text = f"""
- Company: {financials['company_name']} | Sector: {financials['sector']} | Industry: {financials['industry']}
- Current Price: ${price_summary['current_price']} | 6-Month High: ${price_summary['six_month_high']} | 6-Month Low: ${price_summary['six_month_low']}
- Price Change: {price_summary['price_change_pct']}% (from ${price_summary['start_price']} on {price_summary['start_date']} to ${price_summary['current_price']} on {price_summary['end_date']})
- Revenue (TTM): {financials['revenue_ttm']} | Net Income (TTM): {financials['net_income_ttm']}
- Gross Margin: {financials['gross_margin']} | Operating Margin: {financials['operating_margin']} | Net Profit Margin: {financials['net_profit_margin']}
- EBITDA Margin: {financials['ebitda_margin']} | EPS (TTM): {financials['eps_ttm']} | P/E Ratio: {financials['pe_ratio']}
- Market Cap: {financials['market_cap']}
"""

    prompt = f"""You are a senior equity research analyst. Write a structured investor briefing report for {ticker}.

## SEC FILINGS (extracted content)
{filings_content}

## MARKET & FINANCIAL DATA (from yfinance)
{market_text}

---

Write the report with these sections:

1. **Executive Summary** — 3-5 sentence overview
2. **Key Financial Highlights** — Important metrics and trends
3. **Business Developments** — Notable events and strategic updates from filings
4. **Risk Factors** — Key risks identified in filings
5. **Stock Performance** — Price action over the selected period
6. **Analyst Takeaway** — Concise, balanced final assessment

Professional tone, data-driven, markdown formatted."""

    response = client.chat.completions.create(
        model=GPT_SUMMARY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()