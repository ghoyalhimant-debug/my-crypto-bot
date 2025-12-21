import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Live AI Trader (Unblocked)", layout="centered")

# --- 1. SETUP AI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # Use 2.5 or 1.5 depending on what works for your key
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("⚠️ API Key Missing. Check Secrets.")

# --- 2. ROBUST DATA FETCHER (Yahoo Finance) ---
def fetch_market_data(symbol, timeframe='1h'):
    """
    Fetches data from Yahoo Finance (Bypasses Binance/Bybit bans).
    Converts crypto symbols to Yahoo format (BTC-USD).
    """
    # Auto-Fix Symbol for Yahoo (BTC/USDT -> BTC-USD)
    # Yahoo uses dashes (BTC-USD), not slashes (BTC/USDT)
    clean_symbol = symbol.replace("/", "").replace("USDT", "-USD").upper()
    if "-USD" not in clean_symbol:
        clean_symbol += "-USD"

    try:
        # Fetch data
        # Period/Interval mapping: 15m=1d/15m, 1h=2y/1h, 4h=2y/1h (approx)
        interval_map = {'15m': '15m', '1h': '1h', '4h': '1h', '1d': '1d'}
        chosen_interval = interval_map.get(timeframe, '1h')
        
        # Yahoo requires a 'period' argument. 
        # For 15m data, we can only get last 60 days.
        ticker = yf.Ticker(clean_symbol)
        df = ticker.history(period="5d", interval=chosen_interval)
        
        if df.empty:
            return None, clean_symbol
            
        # Clean up data
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Return the last 15 candles as text string
        return df.tail(15).to_string(), clean_symbol
        
    except Exception as e:
        return None, f"Error: {e}"

# --- 3. THE STRATEGY ---
system_prompt = """
You are a Crypto Signal Generator.
I will provide recent market data (Open, High, Low, Close).

STRATEGY INSTRUCTIONS:
1. **Trend**: Identify if Highs/Lows are increasing (UP) or decreasing (DOWN).
2. **Setup**: Look for the "Daily Low Breakout" logic inside the data numbers.
3. **Signal**:
   - If Bullish: Entry at current price. SL below lowest recent low.
   - If Bearish: Entry at current price. SL above highest recent high.

OUTPUT FORMAT (STRICT):
#[COIN] #[DIRECTION]

Entry: [Current Price]

Leverage: [5X - 10X]

TP: [TP1 (+2%)]  [TP2 (+4%)]

SL: [Stop Price]

#SMITH
"""

# --- 4. APP INTERFACE ---
st.title("⚡ Live Market AI Scanner (Unblocked)")
st.write("Enter coin (e.g. `BTC` or `ETH`). Works globally.")

user_input = st.text_input("Coin Name", "BTC")
timeframe = st.selectbox("Timeframe", ["15m", "1h", "1d"], index=1)

if st.button("🔴 Scan Market"):
    with st.spinner(f"Fetching global data for {user_input}..."):
        
        # Get Data via Yahoo Finance
        data_text, symbol_used = fetch_market_data(user_input, timeframe)
        
        if data_text:
            st.success(f"✅ Data fetched for **{symbol_used}**")
            
            # Show Data used
            with st.expander("See Raw Data"):
                st.code(data_text)

            # AI Analysis
            with st.spinner("AI is calculating signal..."):
                try:
                    full_prompt = f"{system_prompt}\n\nDATA FOR {symbol_used}:\n{data_text}"
                    response = model.generate_content(full_prompt)
                    st.code(response.text, language="markdown")
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error(f"❌ Could not find data for {user_input}. Try typing just 'BTC' or 'ETH'.")
