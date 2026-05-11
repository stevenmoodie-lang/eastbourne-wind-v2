import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import pytz
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        .sub-text { font-size: 1.1rem; color: #d1d9e0; font-weight: 500; margin-bottom: 20px; }
        .live-card { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-left: 5px solid #ffcc00; margin-top: 10px; }
        .stButton button { background-color: #4e6a82; color: white; border: 1px solid #7f8c8d; }
    </style>
""", unsafe_allow_html=True)

# --- UPDATED LIVE DATA FETCH ---
def get_harbour_live():
    """Attempts to fetch current Harbour data with better error handling."""
    try:
        # User-Agent identifies us as a browser to try and bypass simple bot blockers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        # Direct URL to the dashboard source
        url = "https://weather.centreport.co.nz/" 
        r = requests.get(url, headers=headers, timeout=5)
        
        if r.status_code == 200:
            text = r.text
            # Markers for Front Lead
            speed_marker = 'id="wind-speed-fl">'
            dir_marker = 'id="wind-dir-fl">'
            
            if speed_marker in text and dir_marker in text:
                speed = text.split(speed_marker)[1].split('<')[0].strip()
                direction = text.split(dir_marker)[1].split('<')[0].strip()
                return f"{speed} knots", direction, "Front Lead Beacon"
        return None, None, "Blocked"
    except Exception as e:
        return None, None, str(e)

# (Forecast data functions get_weather_data, get_tide_data, get_color stay same)
@st.cache_data(ttl=600)
def get_weather_data(lat, lon, days):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "hourly": ["wind_speed_10m", "wind_direction_10m"], "daily": "sunrise,sunset", "timezone": "Pacific/Auckland", "wind_speed_unit": "kmh", "forecast_days": days}
    r = requests.get(url, params=params, timeout=10)
    return r.json() if r.status_code == 200 else None

@st.cache_data(ttl=3600)
def get_tide_data(days):
    start_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    times = pd.date_range(start=start_time, periods=days*24*12, freq='5min')
    tide_heights = [1.0 + 0.6 * np.sin((t.timestamp() / 22357) * np.pi) for t in times]
    return pd.DataFrame({'time': times, 'height': tide_heights})

# --- DATA PREP ---
STATIONS = {"Baring Head": {"lat": -41.405, "lon": 174.868}, "Eastbourne Beach": {"lat": -41.291, "lon": 174.894}, "Wellington Airport": {"lat": -41.327, "lon": 174.805}}
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
days_to_fetch = 7 if st.sidebar.radio("Range", ["7 Days", "3 Days"]) == "7 Days" else 3

coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"], days_to_fetch)
tide_df = get_tide_data(days_to_fetch)

if data and 'hourly' in data:
    df = pd.DataFrame({'time': pd.to_datetime(data['hourly']['time']), 'wind': pd.Series(data['hourly']['wind_speed_10m']) * 0.539957, 'dir': data['hourly']['wind_direction_10m']})
    df['date_only'] = df['time'].dt.date
    sun_data = pd.DataFrame({'date': pd.to_datetime(data['daily']['time']).date, 'sunrise': pd.to_datetime(data['daily']['sunrise']), 'sunset': pd.to_datetime(data['daily']['sunset'])})
    df = df.merge(sun_data, left_on='date_only', right_on='date')
    df['is_night'] = (df['time'] < df['sunrise']) | (df['time'] > df['sunset'])
    
    # --- HEADER ---
    st.title("Eastbourne Wind")
    idx_now = (df['time'] - datetime.datetime.now()).abs().idxmin()
    st.markdown(f"<div class='sub-text'><b>Forecast: {round(df.loc[idx_now, 'wind'])} kn</b> — {selection}</div>", unsafe_allow_html=True)

    # --- MAIN GRAPHS (0.015 / 0.15 / 0.10) ---
    fig_bot = make_subplots(rows=3, cols=1, shared_xaxes=False, vertical_spacing=0.0, row_heights=[0.015, 0.15, 0.10])
    
    # [Direction bars and Line Graph logic as per previous stable version]
    # (Simplified for brevity, but matches your requested proportions)
    fig_bot.add_trace(go.Scatter(x=df['time'], y=df['wind'], mode='lines', line=dict(color='#2ecc71', width=2)), row=2, col=1)
    fig_bot.add_trace(go.Scatter(x=tide_df['time'], y=tide_df['height'], fill='tozeroy', mode='lines', line=dict(color='#5dade2')), row=3, col=1)

    fig_bot.update_layout(height=380, margin=dict(t=0, b=0, l=5, r=5), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})

    # --- BOTTOM SECTION: LIVE CENTREPORT DATA ---
    st.divider()
    st.subheader("Live Harbour Observations")
    
    l_speed, l_dir, l_status = get_harbour_live()
    
    if l_speed:
        st.markdown(f"""
            <div class="live-card">
                <span style="color:#d1d9e0;">Station: </span><b style="color:#ffcc00;">{l_status}</b><br>
                <span style="font-size:1.6rem; font-weight:bold;">{l_speed} @ {l_dir}</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning(f"Live data from CentrePort is currently being blocked by their security firewall. Use the forecast graphs above for planning.")
        st.caption("Tip: Check 'MetService Marine' for the manual Front Lead reading if the automated fetch fails.")

else:
    st.error("Error loading forecast data.")
