import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import datetime
import numpy as np
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- PAGE CONFIG ---
st.set_page_config(page_title="Wellington Harbour Wind (Kts)", layout="wide")

# ... (Keep your existing CSS here) ...

# --- SETTINGS ---
LAT, LON = -41.319, 174.839
KMH_TO_KNOTS = 0.539957

# --- LIVE SCRAPER ---
# ... (Keep your get_front_lead_live function exactly as it is) ...

# --- HELPER FUNCTIONS ---
def get_color(val, alpha=1.0):
    if val <= 10: return f"rgba(169, 201, 217, {alpha})"
    if val <= 15: return f"rgba(92, 169, 204, {alpha})"
    if val <= 20: return f"rgba(122, 214, 134, {alpha})"
    if val <= 25: return f"rgba(255, 230, 109, {alpha})"
    if val <= 30: return f"rgba(255, 126, 121, {alpha})"
    if val <= 35: return f"rgba(224, 49, 49, {alpha})"
    return f"rgba(153, 5, 5, {alpha})"

@st.cache_data(ttl=600)
def get_weather_data():
    # 1. Fetch NIWA (First 7 days)
    niwa_url = "https://weather-api-azure.niwa.co.nz/api/grid/combined"
    r_niwa = requests.get(niwa_url, params={"lat": LAT, "long": LON}, timeout=15).json()
    
    records = []
    for f in r_niwa.get("forecast", []):
        t = pd.to_datetime(f["datetime"])
        if t.tzinfo is not None:
            t = t.tz_convert("Pacific/Auckland").tz_localize(None)
        records.append({"time": t, "speed": f.get("wind_speed_mean", f.get("wind_speed", 0)) * KMH_TO_KNOTS, "dir": f.get("wind_direction", 0)})
    df_niwa = pd.DataFrame(records)

    # 2. Fetch Open-Meteo (Days 8-14)
    # Using Open-Meteo for the extended period to ensure consistency
    om_url = "https://api.open-meteo.com/v1/forecast"
    om_params = {
        "latitude": LAT, "longitude": LON,
        "hourly": ["wind_speed_10m", "wind_direction_10m"],
        "daily": ["sunrise", "sunset"],
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kn", "forecast_days": 14
    }
    r_om = requests.get(om_url, params=om_params).json()
    
    df_om = pd.DataFrame({
        "time": pd.to_datetime(r_om["hourly"]["time"]),
        "speed": r_om["hourly"]["wind_speed_10m"],
        "dir": r_om["hourly"]["wind_direction_10m"]
    })
    
    sun = pd.DataFrame({
        "date": pd.to_datetime(r_om["daily"]["time"]).date,
        "sunrise": pd.to_datetime(r_om["daily"]["sunrise"]),
        "sunset": pd.to_datetime(r_om["daily"]["sunset"])
    })
    
    return df_niwa, df_om, sun

# --- RENDER FUNCTION ---
# ... (Keep your existing render_forecast_block function as it is) ...

# --- EXECUTION ---
live_data = get_front_lead_live()

# ... (Keep your live reporting HTML code here) ...

try:
    df_niwa, df_om, sun_all = get_weather_data()
    now_nz = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=12))).replace(tzinfo=None)

    # Week 1 (NIWA)
    s1 = sun_all.iloc[:7]
    label_1 = f"{s1.iloc[0]['date'].strftime('%b %d')} - {s1.iloc[-1]['date'].strftime('%d')}"
    st.markdown(f'<div class="section-label">{label_1}</div>', unsafe_allow_html=True)
    mask1 = (df_niwa['time'] >= pd.Timestamp(s1.iloc[0]['date'])) & (df_niwa['time'] < pd.Timestamp(s1.iloc[-1]['date']) + pd.Timedelta(days=1))
    render_forecast_block(df_niwa[mask1], s1, show_now_line=True, now_ts=now_nz)

    st.markdown("<hr style='border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 1rem 0;'>", unsafe_allow_html=True)

    # Week 2 (Open-Meteo)
    s2 = sun_all.iloc[7:14]
    if not s2.empty:
        label_2 = f"{s2.iloc[0]['date'].strftime('%b %d')} - {s2.iloc[-1]['date'].strftime('%d')}"
        st.markdown(f'<div class="section-label">{label_2} (Open-Meteo)</div>', unsafe_allow_html=True)
        mask2 = (df_om['time'] >= pd.Timestamp(s2.iloc[0]['date'])) & (df_om['time'] < pd.Timestamp(s2.iloc[-1]['date']) + pd.Timedelta(days=1))
        render_forecast_block(df_om[mask2], s2)

except Exception as e:
    st.error(f"Error loading forecast: {e}")
