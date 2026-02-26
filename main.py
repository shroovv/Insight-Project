"""
main.py
Streamlit entry point for the SEC Filing Summarizer.
"""

import streamlit as st
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go

from sec_fetcher import fetch_filing_urls
from market_data import get_price_history, get_price_summary, get_financials
from summarizer import fetch_filings_content, synthesize_report
from news_insights import fetch_news_sentiment, generate_signal

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SEC Filing Summarizer",
    page_icon="📊",
    layout="wide",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 SEC Filing Summarizer")
st.markdown("Enter a ticker and date range to get an AI-powered investor briefing from SEC filings and market data.")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    ticker_input = st.text_input("Stock Ticker", placeholder="e.g. AAPL, MSFT, TSLA").upper().strip()

    default_end = date.today()
    default_start = default_end - relativedelta(months=6)

    start_date = st.date_input("Start Date", value=default_start)
    end_date = st.date_input("End Date", value=default_end)

    run_button = st.button("🔍 Generate Report", use_container_width=True, type="primary")

    st.divider()
    st.markdown("**Pipeline:**")
    st.markdown("1. Fetch filing URLs from SEC API")
    st.markdown("2. GPT-4.1 web-fetches all URLs")
    st.markdown("3. yfinance pulls OHLC + margins")
    st.markdown("4. GPT-4.1 compiles final report")

# ── Validation ────────────────────────────────────────────────────────────────
if run_button:
    if not ticker_input:
        st.warning("Please enter a ticker symbol.")
        st.stop()
    if start_date >= end_date:
        st.error("Start date must be before end date.")
        st.stop()

# ── Main Pipeline ─────────────────────────────────────────────────────────────
if run_button and ticker_input:

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    with st.status(f"🔎 Building report for **{ticker_input}**...", expanded=True) as status:

        # Step 1: Fetch filing URLs
        st.write("📡 Fetching SEC filing URLs...")
        try:
            filings = fetch_filing_urls(ticker_input, start_str, end_str)
        except Exception as e:
            st.error(f"SEC API error: {e}")
            st.stop()

        if filings:
            st.write(f"✅ Found **{len(filings)}** filings — sending to GPT-4.1 for web fetch...")
        else:
            st.warning("No filings found in this date range. Continuing with market data only.")

        # Step 2: GPT-4.1 fetches all filing URLs at once
        st.write(f"🤖 GPT-4.1 reading {len(filings)} filing(s)...")
        filings_content = fetch_filings_content(ticker_input, filings)
        st.write("✅ Filings processed.")

        # Step 3: yfinance market data
        st.write("📈 Fetching market data...")
        try:
            price_history = get_price_history(ticker_input)
            price_summary = get_price_summary(ticker_input)
            financials = get_financials(ticker_input)
            st.write(f"✅ Market data loaded for **{financials['company_name']}**.")
        except Exception as e:
            st.error(f"yfinance error: {e}")
            st.stop()

        # Step 4: News sentiment via GPT-4.1 web search
        st.write("📰 Fetching news sentiment via GPT-4.1 web search...")
        news_sentiment = fetch_news_sentiment(ticker_input, start_str, end_str)
        st.write("✅ News sentiment ready.")

        # Step 5: Generate BUY / HOLD / SELL signal
        st.write("🧠 Generating investment signal...")
        signal_data = generate_signal(
            ticker=ticker_input,
            start_date=start_str,
            end_date=end_str,
            news_sentiment=news_sentiment,
            price_summary=price_summary,
            financials=financials,
            filings_content=filings_content,
        )
        st.write("✅ Signal generated.")

        # Step 7: Synthesize final report
        st.write("✍️ Compiling investor report...")
        final_report = synthesize_report(ticker_input, filings_content, price_summary, financials)
        st.write("✅ Done!")
        status.update(label="✅ Report ready!", state="complete", expanded=False)

    # ── Metrics Row ───────────────────────────────────────────────────────────
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"${price_summary['current_price']}")
    col2.metric("Period High", f"${price_summary['six_month_high']}")
    col3.metric("Period Low", f"${price_summary['six_month_low']}")
    delta_str = f"{price_summary['price_change_pct']}%"
    col4.metric("Return", delta_str, delta=delta_str)

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab0, tab1, tab2, tab3, tab4 = st.tabs(["📡 Signal & Insights", "📝 Investor Report", "📉 Price Chart", "💰 Financials", "📁 Filing URLs"])

    # ── Tab 0: Signal & Insights ──────────────────────────────────────────
    with tab0:
        signal = signal_data.get("signal", "HOLD")
        confidence = signal_data.get("confidence", "Low")
        dimensions = signal_data.get("dimensions", {})
        summary = signal_data.get("summary", "")
        disclaimer = signal_data.get("disclaimer", "")

        # Signal badge
        signal_colors = {"BUY": "#00c853", "HOLD": "#ffd600", "SELL": "#d50000"}
        signal_emoji = {"BUY": "🟢", "HOLD": "🟡", "SELL": "🔴"}
        confidence_colors = {"High": "#00c853", "Medium": "#ffd600", "Low": "#ff6d00"}
        color = signal_colors.get(signal, "#888")
        conf_color = confidence_colors.get(confidence, "#888")

        st.markdown(
            f"""
            <div style="text-align:center; padding: 2rem 1rem 1rem;">
                <div style="font-size: 5rem; font-weight: 900; color: {color}; letter-spacing: 4px;">
                    {signal_emoji.get(signal, "")} {signal}
                </div>
                <div style="font-size: 1.1rem; color: {conf_color}; margin-top: 0.5rem;">
                    Confidence: <strong>{confidence}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Dimension cards
        verdict_colors = {"Bullish": "#00c853", "Neutral": "#ffd600", "Bearish": "#d50000"}
        verdict_emoji = {"Bullish": "📈", "Neutral": "➡️", "Bearish": "📉"}

        dim_labels = {
            "news": "📰 News Sentiment",
            "sec_filings": "📁 SEC Filings",
            "momentum": "⚡ Price Momentum",
            "fundamentals": "📊 Fundamentals",
        }

        cols = st.columns(2)
        for i, (key, label) in enumerate(dim_labels.items()):
            dim = dimensions.get(key, {})
            verdict = dim.get("verdict", "Neutral")
            reasoning = dim.get("reasoning", "No data available.")
            vc = verdict_colors.get(verdict, "#888")
            ve = verdict_emoji.get(verdict, "")

            with cols[i % 2]:
                st.markdown(
                    f"""
                    <div style="border: 1px solid {vc}; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 1rem;">
                        <div style="font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem;">{label}</div>
                        <div style="font-size: 1.3rem; font-weight: 800; color: {vc};">{ve} {verdict}</div>
                        <div style="font-size: 0.88rem; margin-top: 0.6rem; color: #ccc;">{reasoning}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.divider()

        # Summary + analyst detail
        st.subheader("Overall Reasoning")
        st.markdown(summary)

        with st.expander("📁 SEC Filings Content Used"):
            st.markdown(filings_content)

        with st.expander("📰 Full News Sentiment Analysis"):
            st.markdown(news_sentiment)

        st.divider()
        st.caption(f"⚠️ {disclaimer}")

    with tab1:
        st.markdown(final_report)

    with tab2:
        st.subheader(f"{ticker_input} — Price History")
        fig = go.Figure(go.Candlestick(
            x=price_history.index,
            open=price_history["Open"],
            high=price_history["High"],
            low=price_history["Low"],
            close=price_history["Close"],
            name=ticker_input,
        ))
        fig.update_layout(
            xaxis_title="Date", yaxis_title="Price (USD)",
            xaxis_rangeslider_visible=False, height=500, template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

        fig_vol = go.Figure(go.Bar(
            x=price_history.index, y=price_history["Volume"],
            marker_color="steelblue",
        ))
        fig_vol.update_layout(height=200, template="plotly_dark", showlegend=False, title="Volume")
        st.plotly_chart(fig_vol, use_container_width=True)

    with tab3:
        st.subheader("Profit & Loss Margins")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Gross Margin", financials["gross_margin"])
            st.metric("Operating Margin", financials["operating_margin"])
            st.metric("Net Profit Margin", financials["net_profit_margin"])
            st.metric("EBITDA Margin", financials["ebitda_margin"])
        with col2:
            st.metric("Revenue (TTM)", financials["revenue_ttm"])
            st.metric("Net Income (TTM)", financials["net_income_ttm"])
            st.metric("EPS (TTM)", str(financials["eps_ttm"]))
            st.metric("P/E Ratio", str(financials["pe_ratio"]))
            st.metric("Market Cap", financials["market_cap"])
        st.divider()
        st.subheader("Raw Price Table")
        st.dataframe(price_history, use_container_width=True)

    with tab4:
        st.subheader(f"SEC Filings Found ({start_str} → {end_str})")
        if not filings:
            st.info("No filings found for this ticker in the selected date range.")
        else:
            for f in filings:
                st.markdown(f"**{f['form_type']}** | Filed: `{f['filed_at']}` | Period: `{f['period_of_report']}`")
                st.markdown(f"🔗 {f['url']}")
                st.divider()