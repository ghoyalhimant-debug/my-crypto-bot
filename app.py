import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Deep AI Analyst", layout="centered")

# --- 1. SETUP THE AI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # NOTE: Ensure you use the correct model version available to your key
    model = genai.GenerativeModel('gemini-2.5-flash') 
except Exception as e:
    st.error("⚠️ API Key Error. Check Streamlit Secrets.")

# --- 2. THE MASTER BRAIN (DEEP ANALYSIS) ---
system_prompt = """
You are an Elite Crypto Technical Analyst & Signal Generator.
Analyze the chart image deeply to find the **BEST** available trade setup using ANY of the following strategies.

### 🕵️‍♂️ ANALYSIS PROTOCOL (Look for these)
1. **Candlestick Patterns**: Engulfing, Hammer, Shooting Star, Morning/Evening Star, Doji reversals.
2. **Chart Patterns**: Flags, Pennants, Wedges, Triangles, Head & Shoulders, Double Top/Bottom.
3. **Price Action**:
   - **Support Breakdown**: Price closing BELOW a key support level (SHORT signal).
   - **Resistance Breakout**: Price closing ABOVE a key resistance level (LONG signal).
   - **Trendline Breaks**: Clean break of a diagonal trendline.
4. **Your Special Strategy**: The "Daily Low Breakout" (Break of Daily Low's High + Retest).

### 🧠 DECISION LOGIC
- Scan the chart for ALL above patterns.
- Identify the **Strongest Signal** (Confluence is best).
- Determine Direction: **LONG** or **SHORT**.

### 💰 MONEY MANAGEMENT (Auto-Calc)
- **Leverage**: Calculate specifically to keep risk LOW (between 2x - 10x).
  - *Rule*: If the Stop Loss distance is wide, Lower the leverage. If tight, Higher leverage. Max 25% equity risk.
- **Entry**: Current Price or clear Retest Level.
- **Stop Loss (SL)**: 
  - For LONG: Just below the structure/candle low.
  - For SHORT: Just above the structure/candle high.
- **Take Profits (TP)**:
  - TP1 (1:1), TP2 (1:2), TP3 (1:3), TP4 (1:4).

### 📝 OUTPUT FORMAT (STRICT TELEGRAM STYLE)
If a valid setup is found, output **ONLY** the text block below.
Replace [COIN] with the name seen on chart (e.g., ETHUSDT).
Replace [REASON] with the strategy name (e.g., Bull Flag Breakout).

#[COIN] #[DIRECTION]
([REASON])

Entry: [Entry Price]

Leverage: [Leverage]X

TP: [TP1]  [TP2]  [TP3]  [TP4]

SL: [SL Price]

#SMITH

--------------------------------
**If NO clear trade is visible, output:**
"❌ No High-Probability Trade Found. Market is ranging or unclear."
"""

# --- 3. THE APP INTERFACE ---
st.title("🧠 Deep-Scan AI Trader")
st.markdown("Analyzing: **Patterns, Breakouts, Candles & Price Action**")

uploaded_file = st.file_uploader("Upload Chart Screenshot", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Chart Preview', use_column_width=True)
    
    if st.button("🔍 SCAN MARKET"):
        if 'model' in locals():
            with st.spinner("Analyzing Market Structure, Patterns & Candles..."):
                try:
                    response = model.generate_content([system_prompt, image])
                    st.code(response.text, language="markdown")
                except Exception as e:
                    st.error(f"Analysis Error: {e}")
