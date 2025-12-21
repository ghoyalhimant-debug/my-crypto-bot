import streamlit as st
import google.generativeai as genai
from PIL import Image
import os

# 1. SETUP THE AI
# This looks for your secret password (API Key) on the cloud server
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("API Key not found. Please set it in Streamlit Secrets.")

# 2. THE AI INSTRUCTIONS
system_prompt = """
You are a strict algorithmic trading assistant.
Analyze the chart image based on the user's specific BREAKOUT STRATEGY.

### 1. STRATEGY RULES (The Signal)
1. Identify the **Daily Low Candle** (lowest candle after 12:00 AM).
2. Mark that candle's **HIGH**.
3. Look for a breakout candle that closes ABOVE that High.
4. **Validation**: The next candle's LOW must NOT touch the 'Daily Low Candle's High'.
5. **Entry**: Limit Order at the 'Daily Low Candle's High'.
6. **Stop Loss (SL)**: Just below the 'Daily Low Candle's Low'.

### 2. MONEY MANAGEMENT (Crucial)
- **Leverage Rule**: Suggest leverage between **2x and 10x**.
- **Max Loss Rule**: The calculated loss at SL must not exceed **25% of margin** after leverage.
  - *Formula:* (Distance from Entry to SL in %) * Leverage must be <= 25%.
  - *Example:* If the natural SL distance is 5%, suggested leverage cannot exceed 5x (5% * 5x = 25%).
- **Take Profits (TP)**:
  - TP1: 1:1 Risk/Reward Ratio
  - TP2: 1:2 Risk/Reward Ratio
  - TP3: 1:3 Risk/Reward Ratio

### 3. OUTPUT FORMAT
If the strategy criteria are NOT met, output: "❌ NO TRADE: Setup not found."

If the criteria ARE met, output purely this data card:

**✅ VALID TRADE SETUP**
---
**💎 ENTRY:** [Specific Price]
**🛑 STOP LOSS:** [Specific Price]
**⚡ LEVERAGE:** [2x - 10x]
---
**🎯 TP 1 (1:1):** [Specific Price]
**🎯 TP 2 (1:2):** [Specific Price]
**🎯 TP 3 (1:3):** [Specific Price]
---
*(Note: SL Risk is approx [X]% on equity)*
"""

# 3. THE WEBSITE LAYOUT
st.title("🚀 AI Crypto Analyst")
st.write("Upload your chart image below.")

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Uploaded Chart', use_column_width=True)
    
    if st.button("Generate Analysis"):
        if 'model' in locals():
            with st.spinner("Analyzing candles..."):
                try:
                    response = model.generate_content([system_prompt, image])
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.error("AI Model not loaded. Check API Key.")


