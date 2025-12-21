import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="USDT Live Scanner", layout="centered")

# --- 1. SETUP AI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("⚠️ API Key Missing. Check Secrets.")

# --- 2. DATA FETCHER (USDT Supported) ---
def fetch_market_data(symbol, timeframe='1h'):
    """
    Fetches USDT data from Yahoo Finance (Bypasses Binance Ban).
    Converts 'BTC/USDT' -> 'BTC-USDT'.
    """
    # 1. Format Symbol for Yahoo Finance
    # Yahoo uses dashes: BTC-USDT, ETH-USDT, SOL-USDT
    clean_symbol = symbol.replace("/", "-").upper()
    
    # If user just typed "BTC", default to BTC-USDT (Tether)
    if "-" not in clean_symbol:
        clean_symbol += "-USDT"

    try:
        # 2. Define Timeframe mapping
        # Yahoo requires specific 'period' for intraday data
        # 15m needs '5d' period, 1h needs '1mo' period to work well
        period_map = {'15m': '5d', '1h': '1mo', '4h': '1mo', '1d': '1y'}
        chosen_period = period_map.get(timeframe, '1mo')
        
        # 3. Fetch Data
        ticker = yf.Ticker(clean_symbol)
        df = ticker.history(period=chosen_period, interval=timeframe)
        
        if df.empty:
            return None, clean_symbol
            
        # 4. Clean Data
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Get current price and last 15 candles
        current_price = df['Close'].iloc[-1]
        data_text = df.tail(15).to_string()
        
        return data_text, clean_symbol, current_price
        
    except Exception as e:
        return None, f"Error: {e}", 0

# --- 3. THE STRATEGY ---
system_prompt = """
You are a Crypto Signal Generator (USDT Pairs).
I will provide recent market data for a specific coin.

STRATEGY INSTRUCTIONS:
1. **Trend**: Identify if Highs/Lows are increasing (UP) or decreasing (DOWN).
2. **Setup**: Look for "Daily Low Breakout" or "Support/Resistance" logic.
3. **Signal**:
   - If Bullish: Entry at current price. SL below recent structure low.
   - If Bearish: Entry at current price. SL above recent structure high.

OUTPUT FORMAT (STRICT):
#[COIN] #[DIRECTION]

Entry: [Current Price]

Leverage: [5X - 10X]

TP: [TP1 (+2%)]  [TP2 (+4%)]  [TP3 (+6%)]

SL: [Stop Price]

#SMITH
"""

# --- 4. APP INTERFACE ---
st.title("⚡ Live USDT Scanner (Unblocked)")
st.write("Enter coin (e.g. `BTC` or `ETH`). Fetches **USDT** prices.")

col1, col2 = st.columns(2)
with col1:
    user_symbol = st.text_input("Symbol", "BTC/USDT")
with col2:
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "1d"], index=1)

if st.button("🔴 Scan USDT Market"):
    with st.spinner(f"Fetching {user_symbol} data..."):
        
        # Get Data
        data_text, symbol_used, current_price = fetch_market_data(user_symbol, timeframe)
        
        if data_text:
            st.success(f"✅ Data fetched for **{symbol_used}** | Price: **{current_price:.4f}**")
            
            # Show Data used (Debug)
            with st.expander("See Raw Candle Data"):
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
            st.error(f"❌ Could not find data for {symbol_used}. Try typing 'BTC' or 'ETH'.")
