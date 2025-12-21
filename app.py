import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Crypto Signal Bot", layout="centered")

# --- 1. SETUP THE AI ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # Check your model version (gemini-1.5-flash or gemini-2.5-flash)
    model = genai.GenerativeModel('gemini-2.5-flash') 
except Exception as e:
    st.error("⚠️ API Key Error. Check Streamlit Secrets.")

# --- 2. THE SIGNAL GENERATOR BRAIN ---
system_prompt = """
You are a Crypto Signal Generator. 
Analyze the chart image based on the "Daily Low Breakout" strategy.

### 1. STRATEGY RULES
1. **Identify Daily Low**: Lowest candle after 12:00 AM.
2. **Setup**: Look for a breakout candle closing ABOVE the Daily Low's High.
3. **Confirmation**: Next candle's LOW must NOT touch the Daily Low's High.
4. **Direction**: This is a LONG strategy. (If you see the exact reverse scenario for a Short, you may output SHORT).

### 2. CALCULATION RULES
- **Entry**: The Daily Low Candle's High.
- **SL**: Just below the Daily Low Candle's Low.
- **Leverage**: Calculate so max risk is 25%. (Range 2X - 10X).
- **TPs**: Calculate 4 targets.
  - TP1 (1:1), TP2 (1:2), TP3 (1:3), TP4 (1:4).

### 3. OUTPUT FORMAT (STRICT)
If valid, output EXACTLY this format (no other text). 
Replace [COIN] with the coin name visible on chart (e.g., BTCUSDT).

#[COIN] #[DIRECTION]

Entry: [Entry Price]

Leverage: [Leverage]X

TP: [TP1]  [TP2]  [TP3]  [TP4]

SL: [SL Price]

#SMITH

--------------------------------
If NO valid trade is found, just output: "No Trade Setup Found."
"""

# --- 3. APP INTERFACE ---
st.title("📲 Auto-Signal Generator")
st.write("Upload chart -> Get #SMITH Signal")

uploaded_file = st.file_uploader("Upload Chart", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Chart Preview', use_column_width=True)
    
    if st.button("Generate Signal"):
        if 'model' in locals():
            with st.spinner("Calculating trade levels..."):
                try:
                    response = model.generate_content([system_prompt, image])
                    
                    # Display the result in a copy-paste friendly code block
                    st.code(response.text, language="markdown")
                    
                except Exception as e:
                    st.error(f"Error: {e}")
