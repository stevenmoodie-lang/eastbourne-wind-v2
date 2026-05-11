import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind Tracker", layout="wide", page_icon="🌬️")

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- DATA FETCHING (Public Website Feed) ---
def get_wind_data(location_name):
    # This URL targets the public JSON feed used by niwa.co.nz
    # We use URL encoding to handle spaces (e.g., 'Baring%20Head')
    formatted_name = location_name.replace(" ", "%20")
    url = f"https://weather.niwa.co.nz/api/v1/forecast/{formatted_name}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return None

# --- SIDEBAR ---
st.sidebar.title("📍 Station Select")
# Names must match the NIWA website URL slugs exactly
stations = {
    "Baring Head": "Baring Head",
    "Wellington Airport": "Wellington (Airport)",
    "Lower Hutt": "Lower Hutt",
    "Wellington City": "Wellington"
}

selection = st.sidebar.selectbox("Choose a location:", list(stations.keys()))
loc_name = stations[selection]

# --- MAIN DASHBOARD ---
st.title(f"🌬️ {selection} Wind Report")

with st.spinner('Fetching latest gusts...'):
    data = get_wind_data(loc_name)

if data and 'values' in data:
    df = pd.DataFrame(data['values'])
    df['time'] = pd.to_datetime(df['time'])
    
    # Metrics Row
    latest = df.iloc[0]
    m1, m2, m3 = st.columns(3)
    
    m1.metric("Wind Speed", f"{latest['wind']} km/h")
    m2.metric("Peak Gusts", f"{latest['wind_gust']} km/h")
    m3.metric("Direction", f"{latest.get('wind_dir_compass', 'N/A')}")

    st.divider()

    # Trend Chart
    st.subheader("Forecast Trend")
    fig = px.line(df, x='time', y=['wind', 'wind_gust'],
                  labels={'value': 'km/h', 'time': 'Time'},
                  color_discrete_map={"wind": "#007BFF", "wind_gust": "#FF4B4B"},
                  template="plotly_white")
    
    fig.update_layout(hovermode="x unified", legend_title="Type")
    st.plotly_chart(fig, use_container_width=True)

    # Blasting Windows
    st.subheader("🚀 High Wind Alerts (>30 km/h)")
    high_wind = df[df['wind_gust'] >= 30].copy()
    
    if not high_wind.empty:
        high_wind['time'] = high_wind['time'].dt.strftime('%a %I:%M %p')
        st.dataframe(high_wind[['time', 'wind', 'wind_gust', 'wind_dir_compass']], 
                     use_container_width=True, hide_index=True)
    else:
        st.info("The air is still! No big gusts forecasted today.")

else:
    st.error(f"Could not find data for {selection}.")
    st.info("Try selecting 'Wellington City' in the sidebar—it's the most reliable station.")
