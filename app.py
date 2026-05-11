import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time
import pytz

# --- PAGE CONFIG & CSS ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 0rem; }
        h1 { font-size: 1.8rem !important; margin-bottom: 0px !important; white-space: nowrap; overflow: visible; }
        .subtitle { font-size: 0.9rem; color: #666; margin-bottom: 10px; }
        .stButton button { margin-top: 8px; padding: 2px 10px; }
        .stPlotlyChart { margin-bottom: 5px !important; } 
    </style>
""", unsafe_allow_html=True)

STATIONS = {
    "Baring Head": {"lat": -41.405, "lon": 174.868},
    "Eastbourne Beach": {"lat": -41.291, "lon": 174.894},
    "Wellington Airport": {"lat": -41.327, "lon": 174.805}
}

def get_direction_label(deg):
    labels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    return labels[int((deg + 22.5) % 360 / 45)]

def get_color(knots, opacity=1.0):
    colors = {
        "lightblue": f"rgba(173, 216, 230, {opacity})",
        "dodgerblue": f"rgba(30, 144, 255, {opacity})",
        "green": f"rgba(0, 128, 0, {opacity})",
        "amber": f"rgba(255, 200, 50, {opacity})", 
        "red": f"rgba(255, 0, 0, {opacity})",
        "darkred": f"rgba(139, 0, 0, {opacity})"
    }
    if knots < 5: return colors["lightblue"]
    if knots <= 10: return colors["dodgerblue"]
    if knots <= 15: return colors["green"]
    if knots <= 19: return colors["amber"]
    if knots <= 28: return colors["red"]
    return colors["darkred"]

@st.cache_data(ttl=600)
def get_weather_data(lat, lon, days):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": ["wind_speed_10m", "wind_direction_10m"],
        "daily": "sunrise,sunset",
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kmh", "forecast_days": days
    }
    r = requests.get(url, params=params, timeout=10)
    return r.json() if r.status_code == 200 else None

# --- SIDEBAR & DATA ---
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
forecast_range = st.sidebar.radio("Range", ["7 Days", "3 Days"], index=0)
days_to_fetch = 7 if forecast_range == "7 Days" else 3

coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"], days_to_fetch)
nz_tz = pytz.timezone('Pacific/Auckland')
now_nz = datetime.now(nz_tz).replace(tzinfo=None)

if data and 'hourly' in data:
    df = pd.DataFrame({
        'time': pd.to_datetime(data['hourly']['time']),
        'wind': pd.Series(data['hourly']['wind_speed_10m']) * 0.539957,
        'dir': data['hourly']['wind_direction_10m']
    })
    df['date_only'] = df['time'].dt.date
    sun_data = pd.DataFrame({
        'date': pd.to_datetime(data['daily']['time']).date, 
        'sunrise': pd.to_datetime(data['daily']['sunrise']),
        'sunset': pd.to_datetime(data['daily']['sunset'])
    })
    df = df.merge(sun_data, left_on='date_only', right_on='date')
    df['is_night'] = (df['time'] < df['sunrise']) | (df['time'] > df['sunset'])

    # --- HEADER ---
    idx_now = (df['time'] - now_nz).abs().idxmin()
    col1, col2 = st.columns([6, 1]) 
    with col1:
        st.markdown(f"<h1>Eastbourne Wind: {round(df.loc[idx_now, 'wind'])} kn</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtitle'>Monitoring at <b>{selection}</b> — Currently <b>{get_direction_label(df.loc[idx_now, 'dir'])}</b></div>", unsafe_allow_html=True)
    with col2:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

    # --- 1. TOP GRAPH (SOLID BLOCKS) ---
    day_df = df[~df['is_night']].copy()
    daily_summary = day_df.groupby('date_only').agg({'wind': 'mean', 'dir': lambda x: x.mode()[0]}).reset_index()
    
    fig_top = go.Figure()
    fig_top.add_trace(go.Bar(
        x=daily_summary['date_only'].astype(str), 
        y=[1]*len(daily_summary), 
        marker_color=[get_color(w) for w in daily_summary['wind']], 
        showlegend=False, hoverinfo='none'
    ))

    for i, row in daily_summary.iterrows():
        date_label = pd.to_datetime(row['date_only']).strftime('%a %d')
        fig_top.add_annotation(x=str(row['date_only']), y=1.22, text=f"<b>{date_label}</b>", showarrow=False, font=dict(size=11))
        fig_top.add_annotation(x=str(row['date_only']), y=0.5, text=f"<b>{round(row['wind'])} kn</b>", showarrow=False, font=dict(size=13, color="white"))

    fig_top.update_layout(height=125, margin=dict(t=35, b=5, l=5, r=5), template="plotly_white", bargap=0.05, xaxis=dict(showticklabels=False), yaxis=dict(showticklabels=False, range=[0, 1.4], showgrid=False))

    # --- 2. BOTTOM GRAPH ---
    fig_bot = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.15, 0.85])
    
    # Solid Daily Heatstrip (Fixing the bar width so it's one block per day)
    for i, row in daily_summary.iterrows():
        fig_bot.add_trace(go.Bar(
            x=[pd.to_datetime(row['date_only']) + pd.Timedelta(hours=12)], 
            y=[1], width=1000*3600*24, # One full day in milliseconds
            marker_color=get_color(row['wind']), 
            showlegend=False, hoverinfo='none'
        ), row=1, col=1)
        # Cardinal direction label in the strip
        fig_bot.add_annotation(x=pd.to_datetime(row['date_only']) + pd.Timedelta(hours=12), y=0.5, yref="y1", 
                               text=f"<b>{get_direction_label(row['dir'])}</b>", showarrow=False, font=dict(size=11, color="white"), row=1, col=1)

    # Line Graph (RE-CODED BY SEGMENT FOR COLOR)
    for i in range(len(df)-1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        is_segment_night = p1['is_night'] and p2['is_night']
        fig_bot.add_trace(go.Scatter(
            x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']], 
            mode='lines', 
            line=dict(color=get_color(p1['wind'], opacity=0.15 if is_segment_night else 1.0), width=2.5), 
            showlegend=False, hoverinfo='none'
        ), row=2, col=1)

    # Re-added Direction Arrows (Every 3 hours)
    for i in range(0, len(df), 3):
        row = df.iloc[i]
        fig_bot.add_annotation(x=row['time'], y=row['wind'], text="➤", textangle=row['dir']-90, showarrow=False, 
                               font=dict(size=16, color="black" if not row['is_night'] else "rgba(0,0,0,0.1)"), row=2, col=1)

    # Night Shading & Peak labels
    for d_date in df['date_only'].unique():
        day_block = df[(df['date_only'] == d_date) & (~df['is_night'])]
        if not day_block.empty:
            peak = day_block.loc[day_block['wind'].idxmax()]
            fig_bot.add_annotation(x=peak['time'], y=peak['wind'], text=f"<b>{round(peak['wind'])}</b>", showarrow=False, yshift=20, font=dict(size=10), row=2, col=1)

    for i in range(len(sun_data)):
        if i < len(sun_data) - 1:
            fig_bot.add_vrect(x0=sun_data['sunset'].iloc[i], x1=sun_data['sunrise'].iloc[i+1], fillcolor="black", opacity=0.12, line_width=0, row=2, col=1)

    fig_bot.update_layout(height=350, margin=dict(t=15, b=0, l=5, r=5), template="plotly_white", xaxis2=dict(showticklabels=True), yaxis=dict(showticklabels=False, range=[0, 1.4]), yaxis2=dict(side="left", showgrid=True))

    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})
    st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})
