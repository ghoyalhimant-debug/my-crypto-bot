import streamlit as st
import google.generativeai as genai
import ccxt
import pandas as pd
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="Auto-Fixing AI Trader", layout="centered")

# --- 1. SETUP AI (Self-Healing) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"⚠️ API Key Error: {e}")

def get_working_model():
    """
    Tries to find a working model automatically.
    Priority: 2.0 Flash (High Limit) -> 2.5 Flash Lite -> 2.5 Flash (Low Limit)
    """
    # List of models to try in order
    model_candidates = [
        'gemini-2.0-flash',       # Standard Workhorse (Likely 1500/day)
        'gemini-2.5-flash-lite',  # New Lightweight (High Speed)
        'gemini-2.5-flash',       # Premium (Low Limit 20/day)
        'gemini-pro'              # Old Reliable Backup
    ]
    
    # We return the whole list so the app can loop through them if one fails
    return model_candidates

# --- 2. DATA FETCHER (Kraken - Works Worldwide) ---
def fetch_data(symbol, timeframe):
    """
    Fetches real USDT data from Kraken.
    """
    try:
        exchange = ccxt.kraken()
        clean_symbol = symbol.upper().replace("-", "/")
        if "/" not in clean_symbol:
            clean_symbol += "/USDT"
            
        ohlcv = exchange.fetch_ohlcv(clean_symbol, timeframe, limit=30)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df.tail(15).to_string(index=False), clean_symbol, df['close'].iloc[-1]
    except:
        return None, symbol, 0

# --- 3. THE STRATEGY BRAIN ---
def get_system_prompt(mode):
    base_prompt = "You are a Crypto Signal Generator. Analyze the data and find a trade setup."
    
    if mode == "🟢 SPOT (Safe)":
        return base_prompt + "\nMODE: SPOT. No Leverage. Look for Reversals. Output: #[COIN] #SPOT #LONG..."
    elif mode == "🟡 SCALPING (Normal)":
        return base_prompt + "\nMODE: SCALPING. Lev 2-10x. Max Risk 25%. Output: #[COIN] #[DIRECTION] #SCALP..."
    elif mode == "🔴 RISK/REWARD (High Risk)":
        return base_prompt + "\nMODE: DEGEN. Lev 10-50x. Max Risk 90%. Output: #[COIN] #[DIRECTION] #RISK_TRADE..."
    
    return base_prompt

# --- 4. ROBUST AI CALLER (The Fixer) ---
def ask_ai_smartly(full_prompt):
    """
    Loops through models until one works.
    """
    models_to_try = get_working_model()
    
    for model_name in models_to_try:
        try:
            # Try to load and use the model
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(full_prompt)
            return response.text, model_name # Success!
            
        except Exception as e:
            error_msg = str(e)
            # If 404 (Not Found) or 429 (Quota), just continue to next model
            if "404" in error_msg or "not found" in error_msg.lower():
                continue 
            elif "429" in error_msg or "quota" in error_msg.lower():
                continue
            else:
                return f"❌ Error: {e}", model_name

    return "❌ All AI models failed. Please check your API Key.", "None"

# --- 5. APP INTERFACE ---
st.title("🤖 Auto-Fixing AI Trader")
st.caption("Auto-switches models to find one that works.")

# Channel Selector
mode = st.radio("Channel:", ["🟢 SPOT (Safe)", "🟡 SCALPING (Normal)", "🔴 RISK/REWARD (High Risk)"], horizontal=True)

col1, col2 = st.columns(2)
with col1:
    symbol = st.text_input("Symbol", "BTC")
with col2:
    default_tf = 2 if "SPOT" in mode else 1 
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=default_tf)

if st.button(f"⚡ Scan {symbol}"):
    with st.spinner(f"Scanning {symbol} on Kraken..."):
        
        # 1. Get Data
        data_text, clean_symbol, price = fetch_data(symbol, timeframe)
        
        if data_text:
            st.success(f"Price: **{price} USDT**")
            
            # 2. Analyze with Auto-Switching AI
            with st.spinner("Trying different AI models..."):
                prompt = get_system_prompt(mode)
                full_prompt = f"{prompt}\n\nMARKET DATA:\n{data_text}"
                
                result, used_model = ask_ai_smartly(full_prompt)
                
                st.code(result, language="markdown")
                st.caption(f"✅ Analysis generated using: **{used_model}**")
        else:
            st.error(f"❌ Could not find data for {symbol}.")
