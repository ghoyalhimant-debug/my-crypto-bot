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
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("⚠️ API Key Missing. Check Secrets.")

# --- 2. SETUP BINANCE CONNECTION ---
def fetch_market_data(symbol, timeframe='1h'):
    """Fetches the last 50 candles from Binance"""
    try:
        exchange = ccxt.binance()
        # Fetch OHLCV data (Open, High, Low, Close, Volume)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=50)
        
        # Convert to readable format
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Create a text string of data for the AI to read
        data_string = df.tail(20).to_string(index=False)
        return data_string, df['close'].iloc[-1] # Return data string and current price
    except Exception as e:
        return None, None

# --- 3. THE STRATEGY BRAIN ---
system_prompt = """
You are an Algorithmic Trading Bot. 
I will give you the last 20 candles of market data (Open, High, Low, Close).
Analyze the trend and volatility based on these numbers.

STRATEGY:
1. Identify the trend (Higher Highs = Long, Lower Lows = Short).
2. Check for "Daily Low Breakout" patterns in the data.
3. Use the current price as Entry.

OUTPUT FORMAT (STRICT):
If valid trade found, output:
#[COIN] #[DIRECTION]
Entry: [Current Price]
Leverage: [Calc 2x-10x]
TP: [TP1] [TP2] [TP3] [TP4]
SL: [Calc SL]
#SMITH

If market is choppy/unclear, output:
"❌ Market unclear. No safe entry."
"""

# --- 4. APP INTERFACE ---
st.title("⚡ Live Market AI Scanner")
st.write("Enter a coin name (e.g., BTC/USDT) to scan live Binance data.")

# Input for Coin Name
symbol = st.text_input("Enter Coin Symbol (Format: BTC/USDT, ETH/USDT)", "BTC/USDT").upper()
timeframe = st.selectbox("Select Timeframe", ["15m", "1h", "4h", "1d"], index=1)

if st.button("🔴 Fetch Live Data & Scan"):
    with st.spinner(f"Connecting to Binance... Fetching {symbol} data..."):
        
        # 1. Get Real Data
        market_data_text, current_price = fetch_market_data(symbol, timeframe)
        
        if market_data_text:
            st.success(f"✅ Data Received. Current Price: {current_price}")
            
            # Show the data to user (Optional, hidden in expander)
            with st.expander("View Raw Data"):
                st.code(market_data_text)

            # 2. Ask AI to analyze it
            with st.spinner("AI analyzing price action..."):
                try:
                    # We send the TEXT data instead of an image
                    full_prompt = system_prompt + f"\n\nHere is the {symbol} market data:\n" + market_data_text
                    response = model.generate_content(full_prompt)
                    st.code(response.text, language="markdown")
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error("❌ Could not fetch data. Make sure the symbol is correct (e.g., 'BTC/USDT').")
