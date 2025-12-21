import streamlit as st
import google.generativeai as genai
import ccxt
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="USDT Real Data", layout="centered")

# --- 1. SETUP AI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("⚠️ API Key Missing. Check Secrets.")

# --- 2. DATA FETCHER (KRAKEN - USDT) ---
def fetch_market_data(symbol, timeframe='1h'):
    """
    Fetches REAL USDT data from Kraken (Allowed in US).
    """
    try:
        # Connect to Kraken (Does not block Streamlit Cloud)
        exchange = ccxt.kraken()
        
        # 1. Clean Symbol: Ensure it is 'BTC/USDT' format
        # User might type "btcusdt" or "BTC-USDT" -> convert to "BTC/USDT"
        clean_symbol = symbol.upper().replace("-", "/").replace("_", "/")
        if "/" not in clean_symbol:
            # If user typed "BTC", assume "BTC/USDT"
            if clean_symbol.endswith("USDT"):
                clean_symbol = clean_symbol.replace("USDT", "/USDT")
            else:
                clean_symbol += "/USDT"

        # 2. Fetch Data
        # Kraken uses 'BTC/USDT' standard
        ohlcv = exchange.fetch_ohlcv(clean_symbol, timeframe, limit=30)
        
        # 3. Process Data
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        current_price = df['close'].iloc[-1]
        data_text = df.tail(15).to_string(index=False)
        
        return data_text, clean_symbol, current_price, "Kraken"

    except Exception as e:
        return None, symbol, 0, str(e)

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
st.title("⚡ Real USDT Scanner")
st.write("Fetching data from **Kraken** (No Blocks).")

col1, col2 = st.columns(2)
with col1:
    user_symbol = st.text_input("Symbol", "BTC") # User can just type BTC
with col2:
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)

if st.button("🔴 Scan USDT Market"):
    with st.spinner(f"Connecting to Kraken for {user_symbol}/USDT..."):
        
        # Get Data
        data_text, symbol_used, current_price, source = fetch_market_data(user_symbol, timeframe)
        
        if data_text:
            st.success(f"✅ **{symbol_used}** Price: **{current_price} USDT** (Source: {source})")
            
            # Show Data used
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
            st.error(f"❌ Failed to get data. \n\n**Detailed Error:** {source}\n\n*Try typing exactly 'BTC' or 'ETH'.*")
