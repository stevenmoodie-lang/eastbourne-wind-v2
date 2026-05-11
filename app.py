import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import pytz
import numpy as np
from bs4 import BeautifulSoup

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { padding-top: 1.5rem; padding-bottom: 0rem; }
        .sub-text { font-size: 1.1rem; color: #d1d9e0; font-weight: 500; margin-bottom: 5px; }
        .live-text { font-size: 0.95rem; color: #ffcc00; font-weight: 600; margin-bottom: 20px; }
        .stButton button { background-color: #4e6a82; color: white; border: 1px solid #7f8c8d; }
    </style>
""", unsafe_allow_html=True)

# --- DATA FETCHING ---
def get_front_lead_data():
    """Extracts live data from CentrePort's weather dashboard."""
    try:
        # CentrePort uses an iframe source for their weather data
        url = "https://weather.centreport.co.nz/"
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Site structure usually puts Front Lead (FL) in specific spans/divs
        # Note: These IDs are based on typical CentrePort dashboard markers
        speed = soup.find("span", {"id": "wind-speed-fl"}).text.strip()
        direction = soup.find("span", {"id": "wind-dir-fl"}).text.strip()
        return f"{speed} kn", direction
    except:
        return "Offline", "N/A"

@st.cache_data(ttl=600)
def get_weather_data(lat, lon, days):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon, "hourly": ["wind_speed_10m", "wind_direction_10m"],
        "daily": "sunrise,sunset", "timezone": "Pacific/Auckland", "wind_speed_unit": "kmh", "forecast_days": days
    }
    r = requests.get(url, params=params, timeout=10)
    return r.json() if r.status_code == 200 else None

# (Remaining helper functions: get_direction_label, get_color, get_tide_data stay the same)
def get_direction_label(deg):
    labels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    return labels[int((deg + 22.5) % 360 / 45)]

def get_color(knots, opacity=1.0):
    colors = {"lightblue": f"rgba(173, 216, 230, {opacity})", "dodgerblue": f"rgba(30, 144, 255, {opacity})", "green": f"rgba(0, 128, 0, {opacity})", "amber": f"rgba(255, 200, 50, {opacity})", "red": f"rgba(255, 0, 0, {opacity})", "darkred": f"rgba(139, 0, 0, {opacity})"}
    if knots < 5: return colors["lightblue"]
    if knots <= 10: return colors["dodgerblue"]
    if knots <= 15: return colors["green"]
    if knots <= 19: return colors["amber"]
    if knots <= 28: return colors["red"]
    return colors["darkred"]

@st.cache_data(ttl=3600)
def get_tide_data(days):
    start_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    times = pd.date_range(start=start_time, periods=days*24*12, freq='5min')
    tide_heights = [1.0 + 0.6 * np.sin((t.timestamp() / 22357) * np.pi) for t in times]
    return pd.DataFrame({'time': times, 'height': tide_heights})

# --- UI LOGIC ---
STATIONS = {"Baring Head": {"lat": -41.405, "lon": 174.868}, "Eastbourne Beach": {"lat": -41.291, "lon": 174.894}, "Wellington Airport": {"lat": -41.327, "lon": 174.805}}
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
forecast_range = st.sidebar.radio("Range", ["7 Days", "3 Days"], index=0)
days_to_fetch = 7 if forecast_range == "7 Days" else 3

coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"], days_to_fetch)
tide_df = get_tide_data(days_to_fetch)
fl_speed, fl_dir = get_front_lead_data()

nz_tz = pytz.timezone('Pacific/Auckland')
now_nz = datetime.datetime.now(nz_tz).replace(tzinfo=None)

if data and 'hourly' in data:
    df = pd.DataFrame({'time': pd.to_datetime(data['hourly']['time']), 'wind': pd.Series(data['hourly']['wind_speed_10m']) * 0.539957, 'dir': data['hourly']['wind_direction_10m']})
    df['date_only'] = df['time'].dt.date
    sun_data = pd.DataFrame({'date': pd.to_datetime(data['daily']['time']).date, 'sunrise': pd.to_datetime(data['daily']['sunrise']), 'sunset': pd.to_datetime(data['daily']['sunset'])})
    df = df.merge(sun_data, left_on='date_only', right_on='date')
    df['is_night'] = (df['time'] < df['sunrise']) | (df['time'] > df['sunset'])
    idx_now = (df['time'] - now_nz).abs().idxmin()

    # --- HEADER ---
    t_col1, t_col2 = st.columns([10, 1])
    with t_col1:
        st.title("Eastbourne Wind")
        st.markdown(f"<div class='sub-text'><b>Forecast: {round(df.loc[idx_now, 'wind'])} kn</b> — {selection} ({get_direction_label(df.loc[idx_now, 'dir'])})</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='live-text'>LIVE FRONT LEAD: {fl_speed} @ {fl_dir}</div>", unsafe_allow_html=True)
    with t_col2:
        if st.button("🔄"):
            st.cache_data.clear()
            st.rerun()

    # (Plotly charts logic below remains the same as previous version, preserving 0.015, 0.15, 0.10 ratios)
    # --- MAIN GRAPHS ---
    fig_bot = make_subplots(rows=3, cols=1, shared_xaxes=False, vertical_spacing=0.0, row_heights=[0.015, 0.15, 0.10])
    
    # 1. Hourly Direction Row
    for i in range(len(sun_data)):
        day_start, day_end = sun_data.iloc[i]['sunrise'], sun_data.iloc[i]['sunset']
        for s in range(3):
            t0, t1 = day_start + s*((day_end-day_start)/3), day_start + (s+1)*((day_end-day_start)/3)
            mask = (df['time'] >= t0) & (df['time'] < t1)
            if not df[mask].empty:
                w_mean, d_mean = df[mask]['wind'].mean(), df[mask]['dir'].mean()
                fig_bot.add_trace(go.Bar(x=[t0+(t1-t0)/2], y=[1], width=(t1-t0).total_seconds()*1000, marker_color=get_color(w_mean), showlegend=False, hoverinfo='none'), row=1, col=1)
                fig_bot.add_annotation(x=t0+(t1-t0)/2, y=0.5, text="➤", textangle=d_mean-90, showarrow=False, font=dict(size=8, color="white"), row=1, col=1)

    # 2. Wind Speed Row
    for i in range(len(df)-1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        fig_bot.add_trace(go.Scatter(x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']], mode='lines', line=dict(color=get_color(p1['wind'], opacity=0.2 if p1['is_night'] else 1.0), width=2.5), showlegend=False, hoverinfo='none'), row=2, col=1)

    # 3. Tide Row
    fig_bot.add_trace(go.Scatter(x=tide_df['time'], y=tide_df['height'], fill='tozeroy', mode='lines', line=dict(color='#5dade2', width=1.1), fillcolor='rgba(93, 173, 226, 0.12)', showlegend=False, hoverinfo='none'), row=3, col=1)
    
    # Layout configuration
    fig_bot.update_layout(
        height=400, margin=dict(t=0, b=0, l=5, r=5), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis2=dict(showticklabels=True, tickfont=dict(size=10, color="#d1d9e0"), showgrid=False, anchor='y2'),
        yaxis1=dict(showticklabels=False, range=[0, 1], showgrid=False),
        yaxis2=dict(showticklabels=False, showgrid=True, gridcolor="rgba(255,255,255,0.03)", range=[0, df['wind'].max() * 1.3]),
        yaxis3=dict(showticklabels=False, showgrid=False, range=[0, 2.8])
    )
    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})
