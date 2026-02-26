"""
market_data.py
Fetches OHLC price history and profit/loss margins using yfinance.
"""

import yfinance as yf
import pandas as pd
from config import YFINANCE_PRICE_PERIOD, YFINANCE_PRICE_INTERVAL


def get_price_history(ticker: str) -> pd.DataFrame:
    """
    Returns a DataFrame with OHLC + Volume for the last 6 months.
    Columns: Open, High, Low, Close, Volume
    """
    stock = yf.Ticker(ticker)
    hist = stock.history(period=YFINANCE_PRICE_PERIOD, interval=YFINANCE_PRICE_INTERVAL)

    if hist.empty:
        raise ValueError(f"No price data found for ticker: {ticker}")

    hist.index = hist.index.strftime("%Y-%m-%d")
    return hist[["Open", "High", "Low", "Close", "Volume"]].round(2)


def get_price_summary(ticker: str) -> dict:
    """
    Returns a summary of price stats over the last 6 months:
    - current price, 6mo high, 6mo low, average close, % change
    """
    hist = get_price_history(ticker)
    close = hist["Close"]

    summary = {
        "current_price": round(close.iloc[-1], 2),
        "six_month_high": round(hist["High"].max(), 2),
        "six_month_low": round(hist["Low"].min(), 2),
        "avg_close": round(close.mean(), 2),
        "price_change_pct": round(((close.iloc[-1] - close.iloc[0]) / close.iloc[0]) * 100, 2),
        "start_price": round(close.iloc[0], 2),
        "start_date": hist.index[0],
        "end_date": hist.index[-1],
    }
    return summary


def get_financials(ticker: str) -> dict:
    """
    Returns profit/loss margin data from yfinance:
    - gross margin, operating margin, net profit margin, EBITDA margin
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    margins = {
        "gross_margin": _format_pct(info.get("grossMargins")),
        "operating_margin": _format_pct(info.get("operatingMargins")),
        "net_profit_margin": _format_pct(info.get("profitMargins")),
        "ebitda_margin": _format_pct(info.get("ebitdaMargins")),
        "revenue_ttm": _format_large_num(info.get("totalRevenue")),
        "net_income_ttm": _format_large_num(info.get("netIncomeToCommon")),
        "eps_ttm": info.get("trailingEps"),
        "pe_ratio": info.get("trailingPE"),
        "market_cap": _format_large_num(info.get("marketCap")),
        "company_name": info.get("longName", ticker),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
    }
    return margins


def _format_pct(value) -> str:
    if value is None:
        return "N/A"
    return f"{round(value * 100, 2)}%"


def _format_large_num(value) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.0f}"