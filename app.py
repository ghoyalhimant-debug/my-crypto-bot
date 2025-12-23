import streamlit as st
import google.generativeai as genai
import ccxt
import pandas as pd
import time
import pytz

# --- PAGE SETUP ---
st.set_page_config(page_title="Multi-Coin Impulse Scanner", layout="wide")

# --- 1. SETUP AI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"⚠️ API Key Error: {e}")

def get_working_model():
    return ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']

# --- 2. DATA FETCHER ---
def fetch_data(symbol, timeframe="15m"):
    try:
        exchange = ccxt.kraken()
        clean_symbol = symbol.strip().upper().replace("-", "/")
        if "/" not in clean_symbol:
            clean_symbol += "/USDT"
            
        ohlcv = exchange.fetch_ohlcv(clean_symbol, timeframe, limit=30)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # IST Time Conversion
        ist = pytz.timezone('Asia/Kolkata')
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(ist)
        
        return df.tail(15).to_string(index=False), clean_symbol, df['close'].iloc[-1]
    except:
        return None, symbol, 0

# --- 3. STRATEGY (3 Green / 2 Red) ---
system_prompt = """
You are an Algorithmic Trading Bot.
Analyze the data for the "3-Impulse + 2-Retracement" Strategy.

RULES:
1. **LONG**: 3+ Green Candles (Higher Highs) followed by 2+ Red Candles (Retracement).
   - ENTRY: Swing High. SL: Swing Low. TP: 1:2.
2. **SHORT**: 3+ Red Candles (Lower Lows) followed by 2+ Green Candles (Retracement).
   - ENTRY: Swing Low. SL: Swing High. TP: 1:2.

OUTPUT FORMAT (STRICT):
If Pattern Found:
#[COIN] #[DIRECTION]
**Pattern:** [3 Green+2 Red] or [3 Red+2 Green]
Entry: [Price]
SL: [Price]
TP: [Price]
#SMITH_IMPULSE

If NOT Found:
"NO_TRADE"
"""

# --- 4. AI CALLER ---
def ask_ai_smartly(full_prompt):
    for model_name in get_working_model():
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(full_prompt)
            return response.text
        except:
            continue
    return "Error: AI Busy"

# --- 5. APP INTERFACE ---
st.title("🚀 Multi-Coin Impulse Scanner")
st.markdown("**Strategy:** 3 Impulse Candles + 2 Retracement Candles (15m Timeframe)")

# INPUT: Comma separated list
default_coins = "BTC, ETH, SOL, DOGE, XRP, PEPE, WIF, SUI"
user_input = st.text_area("Enter Coins to Scan (comma separated):", default_coins, height=70)
timeframe = "15m"

if st.button("⚡ START BULK SCAN"):
    # Split string into a list: ['BTC', 'ETH', 'SOL'...]
    coin_list = [x.strip() for x in user_input.split(',')]
    
    st.write(f"🔍 Scanning **{len(coin_list)}** coins...")
    progress_bar = st.progress(0)
    
    # Create a container for results
    results_container = st.container()
    
    for i, coin in enumerate(coin_list):
        # Update Progress
        progress_bar.progress((i + 1) / len(coin_list))
        
        # 1. Fetch Data
        data_text, clean_symbol, price = fetch_data(coin, timeframe)
        
        if data_text:
            # 2. Analyze
            full_prompt = f"{system_prompt}\n\nDATA FOR {clean_symbol}:\n{data_text}"
            result = ask_ai_smartly(full_prompt)
            
            # 3. Display ONLY if a trade is found (Ignore "NO_TRADE")
            if "NO_TRADE" not in result:
                with results_container:
                    st.success(f"✅ **Signal Found: {clean_symbol}** (@ {price})")
                    st.code(result, language="markdown")
            else:
                # Optional: Show small grey text for no trade
                with st.expander(f"❌ {clean_symbol} - No Setup"):
                    st.write("Market structure does not match strategy.")
        
        # Small delay to prevent rate limits
        time.sleep(1)

    st.success("🏁 Scan Complete!")
