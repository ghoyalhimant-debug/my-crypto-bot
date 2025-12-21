import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Universal Crypto Scanner", layout="centered")

# --- 1. SETUP AI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("⚠️ API Key Missing. Check Secrets.")

# --- 2. SMART DATA FETCHER (With Fallback) ---
def fetch_market_data(symbol, timeframe='1h'):
    """
    Tries to fetch USDT data. If fails, falls back to USD.
    """
    # Clean the input (remove /USDT if user typed it)
    # Example: "BTC/USDT" -> "BTC"
    base_coin = symbol.upper().replace("/USDT", "").replace("-USDT", "").replace("USDT", "").replace("/", "")

    # Define the pair variations to try
    # Priority 1: USDT pair
    # Priority 2: USD pair (Always works as backup)
    tickers_to_try = [f"{base_coin}-USDT", f"{base_coin}-USD"]

    # Map timeframe to Yahoo's required 'period'
    period_map = {'15m': '5d', '1h': '1mo', '4h': '1mo', '1d': '1y'}
    chosen_period = period_map.get(timeframe, '1mo')

    for ticker_name in tickers_to_try:
        try:
            ticker = yf.Ticker(ticker_name)
            df = ticker.history(period=chosen_period, interval=timeframe)
            
            if not df.empty:
                # FOUND DATA!
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                current_price = df['Close'].iloc[-1]
                data_text = df.tail(15).to_string()
                
                # Return 3 values: Data, Ticker Name, Price
                return data_text, ticker_name, current_price
        
        except Exception:
            continue # Try the next ticker in the list

    # If loop finishes and nothing found:
    return None, base_coin, 0

# --- 3. THE STRATEGY ---
system_prompt = """
You are a Crypto Signal Generator.
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
st.title("⚡ Universal Crypto Scanner")
st.write("Enter coin name (e.g. `BTC` or `ETH`).")

col1, col2 = st.columns(2)
with col1:
    user_symbol = st.text_input("Symbol", "BTC")
with col2:
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "1d"], index=1)

if st.button("🔴 Scan Market"):
    with st.spinner(f"Searching data for {user_symbol}..."):
        
        # Get Data
        data_text, symbol_used, current_price = fetch_market_data(user_symbol, timeframe)
        
        if data_text:
            st.success(f"✅ Found data for **{symbol_used}** | Price: **{current_price:.4f}**")
            
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
            st.error(f"❌ Could not find data for **{user_symbol}**. Try checking the spelling.")
