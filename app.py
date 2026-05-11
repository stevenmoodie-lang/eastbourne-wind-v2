import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time
import pytz

# --- PAGE CONFIG ---
st.set_page_config(page_title="Wind", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
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
    r = requests.get(url, params=params, timeout=10)
    return r.json() if r.status_code == 200 else None

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
    
    # Identify Night
    df['is_night'] = (df['time'] < df['sunrise']) | (df['time'] > df['sunset'])

    # --- GRAPH 1: FULL TIMELINE (HEIGHT: 300px) ---
    fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.2, 0.8])
    for i in range(len(df)):
        fig1.add_trace(go.Bar(x=[df['time'][i]], y=[1], marker_color="rgb(240,240,240)" if df['is_night'][i] else get_color(df['wind'][i]), marker_line_width=0, showlegend=False, hoverinfo='none'), row=1, col=1)
    
    for i in range(len(df)-1):
        fig1.add_trace(go.Scatter(x=[df['time'][i], df['time'][i+1]], y=[df['wind'][i], df['wind'][i+1]], mode='lines', line=dict(color=get_color(df['wind'][i]), width=2), showlegend=False, hoverinfo='none'), row=2, col=1)

    idx_now = (df['time'] - now_nz).abs().idxmin()
    fig1.add_vline(x=df.loc[idx_now, 'time'], line_width=1.5, line_dash="dot", line_color="green")
    fig1.update_layout(height=280, margin=dict(t=20, b=0, l=5, r=5), template="plotly_white", hovermode="x unified",
                      yaxis=dict(showticklabels=False, fixedrange=True, range=[0, 1.6]),
                      yaxis2=dict(title="kn", fixedrange=True), bargap=0)

    # --- GRAPH 2: DAYLIGHT ONLY HEATSTRIP (HEIGHT: 100px) ---
    day_df = df[~df['is_night']].copy()
    day_df['time_str'] = day_df['time'].dt.strftime('%a %H:00') # Convert to string for category axis

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=day_df['time_str'],
        y=[1] * len(day_df),
        marker_color=[get_color(w) for w in day_df['wind']],
        marker_line_width=0,
        showlegend=False,
        customdata=day_df['wind'],
        hovertemplate='%{x}<br>%{customdata:.1f} kn<extra></extra>'
    ))

    fig2.update_layout(
        height=120, margin=dict(t=30, b=20, l=5, r=5),
        template="plotly_white",
        bargap=0,
        xaxis=dict(type='category', tickangle=45, tickfont=dict(size=8), dtick=4 if days_to_fetch==7 else 2),
        yaxis=dict(showticklabels=False, fixedrange=True, showgrid=False, zeroline=False),
        title=dict(text="Daylight Windows Only", font=dict(size=12), x=0.01)
    )

    # Display
    st.write(f"### {selection} **{df.loc[idx_now, 'wind']:.1f} kn**")
    st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
    st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Error loading data")
