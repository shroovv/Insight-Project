import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SEC_API_KEY = os.getenv("SEC_API_KEY")


# --- OpenAI Models ---
GPT_WEB_SEARCH_MODEL = "gpt-4.1"   # Fetches & reads SEC filing URLs via web_search_preview
GPT_SUMMARY_MODEL = "gpt-5.2"      # Synthesizes final investor report

# --- yfinance ---
YFINANCE_PRICE_PERIOD = "6mo"
YFINANCE_PRICE_INTERVAL = "1d"