import streamlit as st
import google.generativeai as genai
import ccxt
import pandas as pd
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="Unlimited AI Trader", layout="centered")

# --- 1. SETUP AI (With Backup Models) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    # We create a list of models to try. 
    # 'gemini-1.5-flash' is the Standard (1500 req/day free).
    # 'gemini-1.5-flash-8b' is the High-Speed version.
    model_name = 'gemini-1.5-flash' 
    model = genai.GenerativeModel(model_name)
    
except Exception as e:
    st.error(f"⚠️ API Key Error: {e}")

# --- 2. DATA FETCHER (Kraken - Works Everywhere) ---
def fetch_data(symbol, timeframe):
    """
    Fetches real USDT data from Kraken.
    """
    try:
        exchange = ccxt.kraken()
        
        # Format Symbol: Kraken expects 'BTC/USDT'
        clean_symbol = symbol.upper().replace("-", "/")
        if "/" not in clean_symbol:
            clean_symbol += "/USDT"
            
        # Fetch Candles
        ohlcv = exchange.fetch_ohlcv(clean_symbol, timeframe, limit=30)
        
        # Process Data
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        current_price = df['close'].iloc[-1]
        data_text = df.tail(15).to_string(index=False)
        
        return data_text, clean_symbol, current_price
        
    except Exception as e:
        return None, symbol, 0

# --- 3. THE STRATEGY BRAIN ---
def get_system_prompt(mode):
    base_prompt = """
    You are a Crypto Signal Generator. Analyze the provided market data.
    Determine the Trend and find a Setup.
    """

    if mode == "🟢 SPOT (Safe)":
        return base_prompt + """
        **MODE: SPOT TRADING**
        - No Leverage.
        - Look for Trend Reversals.
        - Output: #[COIN] #SPOT #LONG ...
        """
    
    elif mode == "🟡 SCALPING (Normal)":
        return base_prompt + """
        **MODE: SCALPING**
        - Leverage: 2x-10x.
        - Max Risk: 25% of margin.
        - Output: #[COIN] #[DIRECTION] #SCALP ...
        """

    elif mode == "🔴 RISK/REWARD (High Risk)":
        return base_prompt + """
        **MODE: HIGH RISK**
        - Leverage: 10x-50x.
        - Max Risk: 90% of margin.
        - Output: #[COIN] #[DIRECTION] #RISK_TRADE ...
        """
    return base_prompt

# --- 4. SAFE AI CALLER (Prevents Crashing) ---
def ask_ai_safely(full_prompt):
    """
    Tries to talk to AI. If rate limit hit, waits 2 seconds and tries again.
    """
    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            st.warning("⏳ Too fast! Cooling down for 5 seconds...")
            time.sleep(5)
            try:
                # Retry once
                response = model.generate_content(full_prompt)
                return response.text
            except:
                return "❌ Daily Quota Exceeded. Please try again tomorrow or create a new API Key."
        else:
            return f"❌ AI Error: {e}"

# --- 5. APP INTERFACE ---
st.title("🤖 Multi-Channel AI (Unlimited)")
st.write("Fixed: Uses Standard Model (1500 scans/day).")

# CHANNEL SELECTOR
mode = st.radio("Channel Mode:", 
    ["🟢 SPOT (Safe)", "🟡 SCALPING (Normal)", "🔴 RISK/REWARD (High Risk)"], 
    horizontal=True)

col1, col2 = st.columns(2)
with col1:
    symbol = st.text_input("Symbol", "BTC")
with col2:
    default_tf = 2 if "SPOT" in mode else 1 
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=default_tf)

if st.button(f"⚡ Scan {symbol}"):
    with st.spinner(f"Scanning {symbol} on Kraken..."):
        
        # Get Data
        data_text, clean_symbol, price = fetch_data(symbol, timeframe)
        
        if data_text:
            st.success(f"Price: **{price} USDT**")
            
            # AI Analysis
            with st.spinner("Analyzing..."):
                prompt = get_system_prompt(mode)
                full_prompt = f"{prompt}\n\nMARKET DATA:\n{data_text}"
                
                # Use the Safe Function
                result = ask_ai_safely(full_prompt)
                
                st.code(result, language="markdown")
        else:
            st.error(f"❌ Could not find {symbol}. Check spelling.")
