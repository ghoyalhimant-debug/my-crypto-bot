import streamlit as st
import google.generativeai as genai
from PIL import Image
import os

# 1. SETUP THE AI
# This looks for your secret password (API Key) on the cloud server
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("API Key not found. Please set it in Streamlit Secrets.")

# 2. THE AI INSTRUCTIONS
system_prompt = """
You are an expert Crypto Technical Analyst.
Analyze the chart image provided.
Output format:
1. TREND: Bullish/Bearish/Neutral (and why).
2. KEY LEVELS: Support & Resistance.
3. PATTERNS: Any chart patterns or candles?
4. TRADE SETUP:
   - ENTRY: price area
   - STOP LOSS: price
   - TAKE PROFIT: price
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
