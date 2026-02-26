"""
news_insights.py

Two steps:
1. fetch_news_sentiment()  — GPT-4.1 web search for news within the user's date range
2. generate_signal()       — GPT-4.1 synthesizes news + SEC filings into BUY / HOLD / SELL
                             with structured per-dimension reasoning
"""

from openai import OpenAI
from config import OPENAI_API_KEY, GPT_WEB_SEARCH_MODEL, GPT_SUMMARY_MODEL
import json

client = OpenAI(api_key=OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# Step 1: GPT-4.1 web search for news within the user's date range
# ---------------------------------------------------------------------------

def fetch_news_sentiment(ticker: str, start_date: str, end_date: str) -> str:
    """
    Uses GPT-4.1 with web_search_preview to find and assess news
    for the ticker within the given date range.
    """
    prompt = f"""You are a financial news analyst. Search for news about stock ticker {ticker} 
between {start_date} and {end_date}.

Search for:
1. Major company news (earnings, guidance, product launches, partnerships, layoffs, leadership changes)
2. Analyst upgrades or downgrades and price target changes
3. Macroeconomic or sector-level factors affecting {ticker}
4. Any controversies, legal issues, or regulatory developments
5. Insider buying or selling activity

For each finding, note:
- The headline or event
- The approximate date
- Whether it is a POSITIVE, NEGATIVE, or NEUTRAL signal for the stock

End with a one-paragraph overall news sentiment summary.
Be specific and factual. Cite sources where possible."""

    response = client.responses.create(
        model=GPT_WEB_SEARCH_MODEL,
        tools=[{"type": "web_search_preview"}],
        input=prompt,
    )

    result = ""
    for item in response.output:
        if hasattr(item, "content"):
            for block in item.content:
                if hasattr(block, "text"):
                    result += block.text

    return result.strip() or "No news data could be retrieved."


# ---------------------------------------------------------------------------
# Step 2: Synthesize news + SEC filings + price/fundamentals into signal
# ---------------------------------------------------------------------------

def generate_signal(
    ticker: str,
    start_date: str,
    end_date: str,
    news_sentiment: str,
    price_summary: dict,
    financials: dict,
    filings_content: str,
) -> dict:
    """
    Synthesizes news, SEC filings content, price momentum, and fundamentals
    into a structured BUY / HOLD / SELL signal with per-dimension reasoning.

    Returns:
    {
        "signal":       "BUY" | "HOLD" | "SELL",
        "confidence":   "High" | "Medium" | "Low",
        "dimensions": {
            "news":         { "verdict": "Bullish/Neutral/Bearish", "reasoning": "..." },
            "sec_filings":  { "verdict": "...", "reasoning": "..." },
            "momentum":     { "verdict": "...", "reasoning": "..." },
            "fundamentals": { "verdict": "...", "reasoning": "..." },
        },
        "summary": "...",
        "disclaimer": "..."
    }
    """

    price_text = f"""
- Current Price: ${price_summary['current_price']}
- Period High: ${price_summary['six_month_high']} | Period Low: ${price_summary['six_month_low']}
- Price Change over period: {price_summary['price_change_pct']}%
- Average Close: ${price_summary['avg_close']}
"""

    fundamentals_text = f"""
- Revenue (TTM): {financials['revenue_ttm']}
- Net Income (TTM): {financials['net_income_ttm']}
- Gross Margin: {financials['gross_margin']}
- Operating Margin: {financials['operating_margin']}
- Net Profit Margin: {financials['net_profit_margin']}
- EPS (TTM): {financials['eps_ttm']}
- P/E Ratio: {financials['pe_ratio']}
- Market Cap: {financials['market_cap']}
"""

    prompt = f"""You are a senior equity analyst generating a structured investment signal for {ticker}
covering the period {start_date} to {end_date}.

Analyze each dimension independently, then synthesize a final BUY / HOLD / SELL signal.

---

## DIMENSION 1 — NEWS SENTIMENT (from web search)
{news_sentiment}

## DIMENSION 2 — SEC FILINGS (10-K / 10-Q / 8-K extracted content)
{filings_content}

## DIMENSION 3 — PRICE MOMENTUM
{price_text}

## DIMENSION 4 — FUNDAMENTALS
{fundamentals_text}

---

Respond ONLY with a valid JSON object in exactly this format — no markdown, no text outside the JSON:

{{
  "signal": "BUY" or "HOLD" or "SELL",
  "confidence": "High" or "Medium" or "Low",
  "dimensions": {{
    "news": {{
      "verdict": "Bullish" or "Neutral" or "Bearish",
      "reasoning": "2-3 sentences explaining why, referencing specific news findings"
    }},
    "sec_filings": {{
      "verdict": "Bullish" or "Neutral" or "Bearish",
      "reasoning": "2-3 sentences grounded in the actual filing content above"
    }},
    "momentum": {{
      "verdict": "Bullish" or "Neutral" or "Bearish",
      "reasoning": "2-3 sentences on price trend and what it signals"
    }},
    "fundamentals": {{
      "verdict": "Bullish" or "Neutral" or "Bearish",
      "reasoning": "2-3 sentences on margins, earnings, valuation"
    }}
  }},
  "summary": "3-4 sentence plain-English synthesis of why the overall signal is what it is, weighing all four dimensions",
  "disclaimer": "This is not financial advice. This signal is generated by AI based on publicly available data and should not be used as the sole basis for investment decisions."
}}"""

    response = client.chat.completions.create(
        model=GPT_SUMMARY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content.strip())