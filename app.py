import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind Tracker", layout="wide", page_icon="🌬️")

# --- COORDINATES ---
# Latitude and Longitude for specific spots
STATIONS = {
    "Baring Head": {"lat": -41.405, "lon": 174.868},
    "Eastbourne Beach": {"lat": -41.291, "lon": 174.894},
    "Wellington Airport": {"lat": -41.327, "lon": 174.805},
    "Lyall Bay": {"lat": -41.332, "lon": 174.796}
}

# --- DATA FETCHING (Open-Meteo) ---
def get_wind_data(lat, lon):
    # Open-Meteo Forecast API
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m",
        "timezone": "Pacific/Auckland",
        "wind_speed_unit": "kmh",
        "forecast_days": 3
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

# --- SIDEBAR ---
st.sidebar.title("📍 Choose Your Spot")
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
coords = STATIONS[selection]

unit = st.sidebar.radio("Units", ["km/h", "knots"])

# --- MAIN DASHBOARD ---
st.title(f"🌬️ {selection} Wind Outlook")

data = get_wind_data(coords["lat"], coords["lon"])

if data and 'hourly' in data:
    # Process Data
    hourly = data['hourly']
    df = pd.DataFrame({
        'time': pd.to_datetime(hourly['time']),
        'wind': hourly['wind_speed_10m'],
        'gust': hourly['wind_gusts_10m'],
        'direction': hourly['wind_direction_10m']
    })
    
    # Conversion to Knots if selected
    if unit == "knots":
        df['wind'] = df['wind'] * 0.539957
        df['gust'] = df['gust'] * 0.539957

    # 1. Latest Metrics
    # Filter for current time or closest to it
    now = pd.Timestamp.now(tz='Pacific/Auckland').replace(tzinfo=None)
    current_row = df.iloc[(df['time'] - now).abs().argsort()[:1]].iloc[0]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Current Wind", f"{current_row['wind']:.1f} {unit}")
    m2.metric("Current Gusts", f"{current_row['gust']:.1f} {unit}")
    m3.metric("Direction Angle", f"{current_row['direction']}°")

    st.divider()

    # 2. Wind Chart
    st.subheader("Next 72 Hours")
    fig = px.line(df, x='time', y=['wind', 'gust'],
                  labels={'value': unit, 'time': 'Time'},
                  color_discrete_map={"wind": "#007BFF", "gust": "#FF4B4B"},
                  template="plotly_white")
    
    # Shade the "Blasting" Zone (over 20 knots / 37 km/h)
    threshold = 20 if unit == "knots" else 37
    fig.add_hline(y=threshold, line_dash="dot", line_color="green", annotation_text="Kite/Windsurf Threshold")
    
    st.plotly_chart(fig, use_container_width=True)

    # 3. Forecast Table
    with st.expander("View Raw Hourly Forecast"):
        st.dataframe(df, use_container_width=True)

else:
    st.error("Open-Meteo is currently unreachable. Check your internet connection.")
