import streamlit as st
import google.generativeai as genai
import ccxt
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="Multi-Channel AI Trader", layout="centered")

# --- 1. SETUP AI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("⚠️ API Key Missing. Please set GEMINI_API_KEY in secrets.")

# --- 2. DATA FETCHER (Binance Local/Proxy) ---
def fetch_data(symbol, timeframe):
    """
    Fetches data. Works best running LOCALLY in India.
    """
    clean_symbol = symbol.upper().replace("-", "/")
    if "/" not in clean_symbol:
        clean_symbol += "/USDT"
    
    # Try multiple Binance endpoints to bypass blocks
    urls = [
        'https://api.binance.com', 'https://api1.binance.com', 
        'https://api2.binance.com', 'https://api3.binance.com'
    ]
    
    exchange = ccxt.binance({'enableRateLimit': True})
    
    for url in urls:
        try:
            exchange.urls['api']['public'] = url
            ohlcv = exchange.fetch_ohlcv(clean_symbol, timeframe, limit=50)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df.tail(20).to_string(index=False), clean_symbol, df['close'].iloc[-1]
        except:
            continue
            
    return None, clean_symbol, 0

# --- 3. DYNAMIC STRATEGY BRAIN ---
def get_system_prompt(mode):
    """
    Returns the specific instructions for the selected Channel.
    """
    base_prompt = """
    You are a Crypto Signal Generator. Analyze the provided market data.
    Determine the Trend and find a Setup (Breakout, Retest, Reversal).
    """

    if mode == "🟢 SPOT (Safe)":
        return base_prompt + """
        **MODE: SPOT TRADING (Swing)**
        - **Frequency**: High quality, weekly setups (2-3/week).
        - **Leverage**: NONE (Spot).
        - **Stop Loss**: Wide/Safe (Support levels).
        - **Strategy**: Look for strong 4H/Daily trend reversals.
        
        **OUTPUT FORMAT:**
        #[COIN] #SPOT #LONG
        Entry: [Price]
        Target: [TP1] [TP2]
        SL: [Price]
        #SMITH_SPOT
        """
    
    elif mode == "🟡 SCALPING (Normal)":
        return base_prompt + """
        **MODE: SCALPING (Intraday)**
        - **Frequency**: Daily setups (4-5/day).
        - **Leverage**: 2x - 10x (Strict).
        - **Risk Rule**: Max Loss at SL must be approx 20-25% of margin.
        - **Strategy**: Quick 15m/1h breakouts.
        
        **OUTPUT FORMAT:**
        #[COIN] #[DIRECTION]
        Entry: [Price]
        Leverage: [Calc 2-10x]
        TP: [TP1] [TP2] [TP3]
        SL: [Price]
        #SMITH_SCALP
        """

    elif mode == "🔴 RISK/REWARD (High Risk)":
        return base_prompt + """
        **MODE: HIGH RISK / REWARD (Degen)**
        - **Frequency**: Sniper entries (2/day).
        - **Leverage**: 10x - 50x (High).
        - **Risk Rule**: Stop Loss can risk 80-90% of margin (Tight SL, High Lev).
        - **Strategy**: Hunting wicks, liquidity sweeps, aggressive reversals.
        
        **OUTPUT FORMAT:**
        #[COIN] #[DIRECTION] #RISK_TRADE
        Entry: [Price]
        Leverage: [Calc 10-50x]
        TP: [TP1] [TP2] [TP3] [TP4]
        SL: [Price]
        #SMITH_DEGEN
        """

# --- 4. APP INTERFACE ---
st.title("🤖 Master Signal Generator")
st.write("Generate signals for your 3 Telegram Channels.")

# 1. SELECT CHANNEL
mode = st.radio("Select Telegram Channel:", 
    ["🟢 SPOT (Safe)", "🟡 SCALPING (Normal)", "🔴 RISK/REWARD (High Risk)"], 
    horizontal=True)

# 2. INPUTS
col1, col2 = st.columns(2)
with col1:
    symbol = st.text_input("Coin Symbol", "BTC")
with col2:
    # Auto-select timeframe based on mode
    default_tf = 2 if "SPOT" in mode else 1 # Index 2 is 4h, 1 is 1h
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=default_tf)

# 3. GENERATE
if st.button(f"⚡ Generate {mode.split()[1]} Signal"):
    with st.spinner(f"Scanning {symbol} for {mode} Setup..."):
        
        # Get Data
        data_text, clean_symbol, price = fetch_data(symbol, timeframe)
        
        if data_text:
            st.success(f"Data Found: {clean_symbol} @ {price}")
            
            # Get the correct Prompt for the selected mode
            prompt = get_system_prompt(mode)
            full_prompt = f"{prompt}\n\nMARKET DATA:\n{data_text}"
            
            try:
                response = model.generate_content(full_prompt)
                st.code(response.text, language="markdown")
            except Exception as e:
                st.error(f"AI Error: {e}")
        else:
            st.error("❌ Connection failed. Ensure you are running LOCALLY on Laptop.")
