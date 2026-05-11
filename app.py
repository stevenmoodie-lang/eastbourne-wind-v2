import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIG & STYLING ---
st.set_page_config(page_title="NZ Wind Tracker", layout="wide", page_icon="🌬️")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True) # Changed from unsafe_allow_index to unsafe_allow_html

# --- DATA FETCHING ---
@st.cache_data(ttl=1800)
def get_niwa_wind(location):
    # Base URL for NIWA's Azure-hosted API
    url = f"https://weather-api-azure.niwa.co.nz/api/location/{location}/combined"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error connecting to NIWA: {e}")
        return None

# --- UI SIDEBAR ---
st.sidebar.header("📍 Location Settings")
# Defaulting to Wellington as it's a prime wind testing ground
loc_input = st.sidebar.text_input("Baring Head", value="113776245")
unit_type = st.sidebar.selectbox("Wind Unit", ["km/h", "knots"])

st.sidebar.markdown("---")
st.sidebar.write("💡 **Tip:** Use IDs like `wellington`, `auckland`, or `christchurch`.")

# --- MAIN DASHBOARD ---
st.title("🌬️ NIWA Wind Forecast")
st.write(f"Showing high-resolution data for: **{loc_input.title()}**")

data = get_niwa_wind(loc_input.lower())

if data and 'values' in data:
    # Process Data
    df = pd.DataFrame(data['values'])
    df['time'] = pd.to_datetime(df['time'])
    
    # Unit Conversion if knots selected
    if unit_type == "knots":
        df['wind'] = df['wind'] * 0.539957
        df['wind_gust'] = df['wind_gust'] * 0.539957

    # 1. Current Conditions (Latest available data point)
    current = df.iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Wind", f"{current['wind']:.1f} {unit_type}")
    col2.metric("Peak Gusts", f"{current['wind_gust']:.1f} {unit_type}")
    col3.metric("Direction", f"{current['wind_dir_compass']}")
    
    # Windchill is a unique NIWA combined field
    if 'wind_chill' in current:
        col4.metric("Wind Chill", f"{current['wind_chill']}°C")

    st.markdown("---")

    # 2. Wind Trend Chart (Plotly for Interactivity)
    st.subheader("72-Hour Wind & Gust Forecast")
    
    fig = px.line(df, x='time', y=['wind', 'wind_gust'], 
                  labels={'value': unit_type, 'time': 'Time'},
                  color_discrete_map={"wind": "#1f77b4", "wind_gust": "#ff7f0e"},
                  template="plotly_white")
    
    fig.update_layout(hovermode="x unified", legend_title_text='Legend')
    st.plotly_chart(fig, use_container_container_width=True)

    # 3. Blasting Table (Filter for high wind sessions)
    st.subheader("🚀 Optimal Windows")
    min_wind = 15 if unit_type == "knots" else 28
    
    blasting_df = df[df['wind'] >= min_wind][['time', 'wind', 'wind_gust', 'wind_dir_compass']].copy()
    
    if not blasting_df.empty:
        st.success(f"Found {len(blasting_df)} high-wind periods in the forecast!")
        blasting_df['time'] = blasting_df['time'].dt.strftime('%a %I:%M %p')
        st.dataframe(blasting_df, use_container_width=True, hide_index=True)
    else:
        st.info("No high-wind windows detected in the current forecast.")

else:
    st.warning("No data found. Please check the Location ID and try again.")
