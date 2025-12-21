import streamlit as st
import google.generativeai as genai
import ccxt
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Live AI Trader", layout="centered")

# --- 1. SETUP AI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # Switch to 2.5 or 2.0 if 1.5 is deprecated
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("⚠️ API Key Missing. Check Secrets.")

# --- 2. ROBUST DATA FETCHER (With Backup) ---
def fetch_market_data(symbol, timeframe='1h'):
    """
    Fetches data from Binance. If that fails, tries Bybit.
    Auto-fixes symbol format (e.g. BTCUSDT -> BTC/USDT).
    """
    # 1. Auto-Fix Symbol Format
    if '/' not in symbol:
        # Assume the last 4 chars are the quote (e.g. USDT)
        symbol = f"{symbol[:-4]}/{symbol[-4:]}"
    symbol = symbol.upper()

    # 2. Try Binance First
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=30)
        return process_data(ohlcv), symbol, "Binance"
    except Exception as e_binance:
        # 3. If Binance fails, Try Bybit (Backup)
        try:
            exchange = ccxt.bybit()
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=30)
            return process_data(ohlcv), symbol, "Bybit"
        except Exception as e_bybit:
            # If both fail, return the error message
            return None, symbol, f"Binance Error: {e_binance} | Bybit Error: {e_bybit}"

def process_data(ohlcv):
    """Converts raw data to readable text"""
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Return the last 15 candles as text
    return df.tail(15).to_string(index=False)

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
TP: [TP1 (+2%)] [TP2 (+4%)]
SL: [Stop Price]
#SMITH
"""

# --- 4. APP INTERFACE ---
st.title("⚡ Live Market AI Scanner (Fixed)")
st.write("Enter coin (e.g. `BTCUSDT` or `ETH/USDT`).")

user_symbol = st.text_input("Symbol", "BTC/USDT")
timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h"], index=1)

if st.button("🔴 Scan Market"):
    with st.spinner(f"Fetching data for {user_symbol}..."):
        
        # Get Data
        data_text, fixed_symbol, source = fetch_market_data(user_symbol, timeframe)
        
        if data_text is not None:
            st.success(f"✅ Data fetched from **{source}** for **{fixed_symbol}**")
            
            # Show Data used (Debug)
            with st.expander("See Raw Data"):
                st.code(data_text)

            # AI Analysis
            with st.spinner("AI is calculating signal..."):
                try:
                    full_prompt = f"{system_prompt}\n\nDATA FOR {fixed_symbol}:\n{data_text}"
                    response = model.generate_content(full_prompt)
                    st.code(response.text, language="markdown")
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error(f"❌ Failed to fetch data. Error details:\n{source}")
