import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time
import pytz

# --- PAGE CONFIG & CSS ---
st.set_page_config(page_title="Wind", layout="wide")

# This CSS strips the massive default padding at the top of Streamlit apps
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        .stMetric { margin-top: -50px; }
    </style>
""", unsafe_allow_html=True)

STATIONS = {
    "Baring Head": {"lat": -41.405, "lon": 174.868},
    "Eastbourne Beach": {"lat": -41.291, "lon": 174.894},
    "Wellington Airport": {"lat": -41.327, "lon": 174.805}
}

def get_color(knots):
    if knots < 5: return "lightblue"
    if knots <= 10: return "blue"
    if knots <= 15: return "green"
    if knots <= 19: return "yellow"
    if knots <= 28: return "red"
    return "darkred"

def get_weather_data(lat, lon, days):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "wind_speed_10m",
        "daily": "sunrise,sunset",
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kmh", "forecast_days": days
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json() if r.status_code == 200 else None
    except: return None

# --- SIDEBAR ---
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
forecast_range = st.sidebar.radio("Range", ["7 Days", "3 Days"], index=0)
days_to_fetch = 7 if forecast_range == "7 Days" else 3

# --- DATA ---
coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"], days_to_fetch)
nz_tz = pytz.timezone('Pacific/Auckland')
now_nz = datetime.now(nz_tz).replace(tzinfo=None)

if data and 'hourly' in data:
    df = pd.DataFrame({
        'time': pd.to_datetime(data['hourly']['time']),
        'wind': pd.Series(data['hourly']['wind_speed_10m']) * 0.539957
    })
    df['date_only'] = df['time'].dt.date
    sun_data = pd.DataFrame({
        'date': pd.to_datetime(data['daily']['time']).date, 
        'sunrise': pd.to_datetime(data['daily']['sunrise']),
        'sunset': pd.to_datetime(data['daily']['sunset'])
    })
    df = df.merge(sun_data, left_on='date_only', right_on='date')

    # --- PLOT (HEIGHT: 300px) ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.2, 0.8])

    for i in range(len(df)):
        is_night = (df.loc[i, 'time'] < df.loc[i, 'sunrise']) or (df.loc[i, 'time'] > df.loc[i, 'sunset'])
        fig.add_trace(go.Bar(x=[df.loc[i, 'time']], y=[1], marker_color="rgb(240,240,240)" if is_night else get_color(df.loc[i, 'wind']), marker_line_width=0, showlegend=False, hoverinfo='none'), row=1, col=1)

    for i in range(len(df) - 1):
        fig.add_trace(go.Scatter(x=[df['time'][i], df['time'][i+1]], y=[df['wind'][i], df['wind'][i+1]], mode='lines', line=dict(color=get_color(df['wind'][i]), width=2), showlegend=False, hoverinfo='none'), row=2, col=1)

    # Annotations
    for i in range(len(sun_data)):
        midday = datetime.combine(sun_data['date'].iloc[i], time(12, 0))
        fig.add_annotation(x=midday, y=1.5, yref="y1", text=f"<b>{midday.strftime('%a')}</b>", showarrow=False, font=dict(size=9))
        if i < len(sun_data) - 1:
            sunset, sunrise_next = sun_data['sunset'].iloc[i], sun_data['sunrise'].iloc[i+1]
            fig.add_annotation(x=sunset + (sunrise_next - sunset)/2, y=0.5, yref="y1", text="🌙", showarrow=False, font=dict(size=10))
            fig.add_vrect(x0=sunset, x1=sunrise_next, fillcolor="gray", opacity=0.05, line_width=0, row=2, col=1)

    # NOW line
    idx_now = (df['time'] - now_nz).abs().idxmin()
    fig.add_vline(x=df.loc[idx_now, 'time'], line_width=1.5, line_dash="dot", line_color="green")

    fig.update_layout(
        height=300, margin=dict(t=20, b=0, l=5, r=5),
        template="plotly_white", hovermode="x unified",
        yaxis=dict(showticklabels=False, fixedrange=True, range=[0, 2], showgrid=False),
        yaxis2=dict(title="kn", title_font=dict(size=10), tickfont=dict(size=9), fixedrange=True),
        bargap=0
    )

    # Display metric and title in one tight block
    st.write(f"### {selection} **{df.loc[idx_now, 'wind']:.1f} kn**")
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Error loading data")
