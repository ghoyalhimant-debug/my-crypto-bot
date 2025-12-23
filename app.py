import streamlit as st
import google.generativeai as genai
import ccxt
import pandas as pd
import time
import pytz
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Impulse Trading Bot", layout="centered")

# --- 1. SETUP AI (Self-Healing) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"⚠️ API Key Error: {e}")

def get_working_model():
    """Tries to find a working model automatically."""
    return [
        'gemini-2.5-flash',       
        'gemini-1.5-flash',       
        'gemini-1.5-pro'              
    ]

# --- 2. DATA FETCHER (Kraken - Works Worldwide) ---
def fetch_data(symbol, timeframe="15m"):
    """
    Fetches real USDT data from Kraken.
    """
    try:
        exchange = ccxt.kraken()
        clean_symbol = symbol.upper().replace("-", "/")
        if "/" not in clean_symbol:
            clean_symbol += "/USDT"
            
        # We need enough candles to see the 3 green + 2 red pattern
        ohlcv = exchange.fetch_ohlcv(clean_symbol, timeframe, limit=30)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Convert to IST (Indian Standard Time)
        ist = pytz.timezone('Asia/Kolkata')
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(ist)
        
        current_price = df['close'].iloc[-1]
        
        # We send the last 15 candles to AI to find the pattern
        data_text = df.tail(15).to_string(index=False)
        
        return data_text, clean_symbol, current_price
    except Exception as e:
        return None, symbol, 0

# --- 3. THE STRATEGY BRAIN (Your Specific Rules) ---
system_prompt = """
You are a Strict Algorithmic Trading Bot. 
Analyze the chart data provided based on the "3-Impulse + 2-Retracement" Strategy.

### 🕒 SESSION TIME
- Ensure the current analysis considers the session starting from **5:30 AM IST**.

### 📈 LONG STRATEGY RULES
1. **Impulse Phase**: Look for at least **3 consecutive GREEN candles**.
   - Condition: Each green candle must break the previous candle's HIGH.
2. **Retracement Phase**: Immediately after the impulse, look for at least **2 consecutive RED candles**.
3. **Trade Setup**:
   - **ENTRY**: Buy Stop at the **Swing High** (Highest price of the 3+ Green candles).
   - **STOP LOSS (SL)**: The **Swing Low** (Lowest price of the 2+ Red retracement candles).
   - **TAKE PROFIT (TP)**: 1:2 Risk/Reward Ratio.

### 📉 SHORT STRATEGY RULES
1. **Impulse Phase**: Look for at least **3 consecutive RED candles**.
   - Condition: Each red candle must break the previous candle's LOW.
2. **Retracement Phase**: Immediately after the impulse, look for at least **2 consecutive GREEN candles**.
3. **Trade Setup**:
   - **ENTRY**: Sell Stop at the **Swing Low** (Lowest price of the 3+ Red candles).
   - **STOP LOSS (SL)**: The **Swing High** (Highest price of the 2+ Green retracement candles).
   - **TAKE PROFIT (TP)**: 1:2 Risk/Reward Ratio.

### 📝 OUTPUT FORMAT (STRICT)
If a valid pattern is found in the recent data:
#[COIN] #[DIRECTION]
**Pattern:** [3 Green + 2 Red] OR [3 Red + 2 Green]

Entry: [Swing High/Low Price]

SL: [Retracement High/Low Price]

TP: [Calculated 1:2 Target]

#SMITH_IMPULSE

--------------------------------
If pattern is NOT found, output ONLY: 
"❌ No Impulse Pattern (3+ Trend / 2+ Retrace) found."
"""

# --- 4. ROBUST AI CALLER ---
def ask_ai_smartly(full_prompt):
    models_to_try = get_working_model()
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(full_prompt)
            return response.text, model_name
        except Exception:
            continue
    return "❌ AI Error: All models busy.", "None"

# --- 5. APP INTERFACE ---
st.title("🚀 Impulse Strategy Bot (5:30 AM IST)")
st.caption("Strategy: 3+ Impulse Candles -> 2+ Retracement Candles -> Entry at Breakout")

col1, col2 = st.columns(2)
with col1:
    symbol = st.text_input("Symbol", "BTC")
with col2:
    # Fixed to 15m as per your strategy
    st.info("Timeframe: **15 min** (Fixed)") 
    timeframe = "15m"

if st.button(f"⚡ Scan {symbol}"):
    with st.spinner(f"Scanning {symbol} for 3-Green/2-Red pattern..."):
        
        # 1. Get Data
        data_text, clean_symbol, price = fetch_data(symbol, timeframe)
        
        if data_text:
            st.success(f"Current Price: **{price} USDT**")
            
            # Show Data (Optional)
            with st.expander("Check Candle Data"):
                st.code(data_text)
            
            # 2. Analyze
            with st.spinner("Counting candles..."):
                full_prompt = f"{system_prompt}\n\nMARKET DATA (IST Time):\n{data_text}"
                result, used_model = ask_ai_smartly(full_prompt)
                st.code(result, language="markdown")
        else:
            st.error(f"❌ Could not find data for {symbol}.")
