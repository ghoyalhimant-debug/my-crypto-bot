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

# --- 2. DATA FETCHER (KRAKEN - Works Everywhere) ---
def fetch_data(symbol, timeframe):
    """
    Fetches real USDT data from Kraken.
    Works in India and on Cloud (No Blocking).
    """
    try:
        exchange = ccxt.kraken()
        
        # Format Symbol: Kraken expects 'BTC/USDT'
        clean_symbol = symbol.upper().replace("-", "/")
        if "/" not in clean_symbol:
            # If user types "BTC", assume "BTC/USDT"
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

# --- 3. THE 3-CHANNEL STRATEGY BRAIN ---
def get_system_prompt(mode):
    """
    Switches the AI strategy based on your selected channel.
    """
    base_prompt = """
    You are a Professional Crypto Signal Generator. 
    Analyze the provided market data and finding the best trade setup.
    """

    if mode == "🟢 SPOT (Safe/Swing)":
        return base_prompt + """
        **STRATEGY: SPOT SWING**
        - **Goal**: Daily/Weekly trend capture.
        - **Leverage**: NONE (Spot).
        - **Stop Loss**: Wide & Safe (Below major support).
        - **Risk**: Low.
        
        **OUTPUT FORMAT:**
        #[COIN] #SPOT #LONG
        Entry: [Price]
        Targets: [TP1] - [TP2]
        SL: [Price]
        #SMITH_SPOT
        """
    
    elif mode == "🟡 SCALPING (Intraday)":
        return base_prompt + """
        **STRATEGY: INTRADAY SCALPING**
        - **Goal**: Quick 15m/1h flips.
        - **Leverage**: 2x - 10x.
        - **Stop Loss**: Tight. Max risk 20-25% of margin.
        - **Risk**: Medium.
        
        **OUTPUT FORMAT:**
        #[COIN] #[DIRECTION] #SCALP
        Entry: [Price]
        Leverage: [Calc 2x-10x]
        TP: [TP1]  [TP2]  [TP3]
        SL: [Price]
        #SMITH_SCALP
        """

    elif mode == "🔴 RISK/REWARD (Degen)":
        return base_prompt + """
        **STRATEGY: HIGH RISK SNIPER**
        - **Goal**: Catching wicks and aggressive reversals.
        - **Leverage**: 10x - 50x.
        - **Stop Loss**: Very Tight. Max risk 80-90% of margin (High Reward).
        - **Risk**: Very High.
        
        **OUTPUT FORMAT:**
        #[COIN] #[DIRECTION] #RISK_TRADE
        Entry: [Price]
        Leverage: [Calc 10x-50x]
        TP: [TP1]  [TP2]  [TP3]  [TP4]
        SL: [Price]
        #SMITH_DEGEN
        """

# --- 4. APP INTERFACE ---
st.title("📲 3-Channel Signal Generator")
st.write("Select a channel mode to generate the perfect signal.")

# CHANNEL SELECTOR
mode = st.radio("Select Telegram Channel:", 
    ["🟢 SPOT (Safe/Swing)", "🟡 SCALPING (Intraday)", "🔴 RISK/REWARD (Degen)"], 
    horizontal=True)

col1, col2 = st.columns(2)
with col1:
    symbol = st.text_input("Coin Symbol", "BTC") # Just type BTC, ETH, etc.
with col2:
    # Auto-select best timeframe for the mode
    default_tf = 2 if "SPOT" in mode else 1 
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=default_tf)

if st.button(f"⚡ Generate {mode.split()[1]} Signal"):
    with st.spinner(f"Scanning {symbol} on Kraken..."):
        
        # Get Data
        data_text, clean_symbol, price = fetch_data(symbol, timeframe)
        
        if data_text:
            st.success(f"✅ Data Fetched: **{clean_symbol}** @ **{price} USDT**")
            
            # AI Analysis
            with st.spinner("Calculating Leverage & Targets..."):
                try:
                    # 1. Get the correct instructions
                    prompt = get_system_prompt(mode)
                    
                    # 2. Send to Gemini
                    full_prompt = f"{prompt}\n\nMARKET DATA:\n{data_text}"
                    response = model.generate_content(full_prompt)
                    
                    # 3. Show Result
                    st.code(response.text, language="markdown")
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error(f"❌ Could not find data for {symbol}. Try typing just 'BTC' or 'ETH'.")
