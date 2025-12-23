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
