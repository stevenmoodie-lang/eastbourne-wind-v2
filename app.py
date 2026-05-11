import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time
import pytz

# --- PAGE CONFIG & CSS ---
st.set_page_config(page_title="Wind Tracker", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 0rem; }
        h1 { font-size: 1.5rem !important; margin-bottom: 0px !important; }
        .stPlotlyChart { margin-bottom: 5px !important; } 
    </style>
""", unsafe_allow_html=True)

STATIONS = {
    "Baring Head": {"lat": -41.405, "lon": 174.868},
    "Eastbourne Beach": {"lat": -41.291, "lon": 174.894},
    "Wellington Airport": {"lat": -41.327, "lon": 174.805}
}

def get_color(knots, opacity=1.0):
    colors = {
        "lightblue": f"rgba(173, 216, 230, {opacity})",
        "dodgerblue": f"rgba(30, 144, 255, {opacity})",
        "green": f"rgba(0, 128, 0, {opacity})",
        "yellow": f"rgba(255, 255, 0, {opacity})",
        "red": f"rgba(255, 0, 0, {opacity})",
        "darkred": f"rgba(139, 0, 0, {opacity})"
    }
    if knots < 5: return colors["lightblue"]
    if knots <= 10: return colors["dodgerblue"]
    if knots <= 15: return colors["green"]
    if knots <= 19: return colors["yellow"]
    if knots <= 28: return colors["red"]
    return colors["darkred"]

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
    df['is_night'] = (df['time'] < df['sunrise']) | (df['time'] > df['sunset'])

    # --- 1. TOP GRAPH: DAYLIGHT FOCUS ---
    day_df = df[~df['is_night']].copy().reset_index(drop=True)
    day_df['time_str'] = day_df['time'].dt.strftime('%a %H') 

    fig_top = go.Figure()
    fig_top.add_trace(go.Bar(
        x=day_df['time_str'], y=[1] * len(day_df),
        marker_color=[get_color(w) for w in day_df['wind']],
        marker_line_width=0, showlegend=False,
        customdata=day_df['wind'],
        hovertemplate='%{x}:00<br>%{customdata:.1f} kn<extra></extra>'
    ))

    # Center Day Text (Mon 11 format)
    for d_date in day_df['date_only'].unique():
        group = day_df[day_df['date_only'] == d_date]
        center_idx = group.index[len(group)//2]
        # Format date as 'Mon 11' (No leading zero)
        date_label = f"{group.iloc[0]['time'].strftime('%a')} {group.iloc[0]['time'].day}"
        
        fig_top.add_annotation(
            x=center_idx, y=1.15, text=f"<b>{date_label}</b>",
            showarrow=False, font=dict(size=11), xanchor="center"
        )
        # Day Separator
        last_idx = group.index[-1]
        if last_idx < len(day_df) - 1:
            fig_top.add_vline(x=last_idx + 0.5, line_width=8, line_color="white")

    fig_top.update_layout(
        height=120, margin=dict(t=30, b=5, l=5, r=5),
        template="plotly_white", bargap=0,
        xaxis=dict(type='category', showticklabels=False),
        yaxis=dict(showticklabels=False, fixedrange=True, range=[0, 1.4], showgrid=False),
        title=dict(text="<b>Daylight Focus</b>", font=dict(size=11), x=0.01)
    )

    # --- 2. BOTTOM GRAPH: LINE + TIMELINE ---
    fig_bot = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.15, 0.85])
    
    for i in range(len(df)):
        fig_bot.add_trace(go.Bar(x=[df['time'][i]], y=[1], 
                                marker_color="rgb(240,240,240)" if df['is_night'][i] else get_color(df['wind'][i]), 
                                marker_line_width=0, showlegend=False, hoverinfo='none'), row=1, col=1)
    
    for i in range(len(df)-1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        is_segment_night = p1['is_night'] and p2['is_night']
        line_opacity = 0.1 if is_segment_night else 1.0
        line_width = 1.0 if is_segment_night else 2.5
        fig_bot.add_trace(go.Scatter(
            x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']], 
            mode='lines', line=dict(color=get_color(p1['wind'], opacity=line_opacity), width=line_width), 
            showlegend=False, hoverinfo='none'
        ), row=2, col=1)

    for i in range(len(sun_data)):
        midday = datetime.combine(sun_data['date'].iloc[i], time(12, 0))
        # Format date as 'Mon' (No number)
        fig_bot.add_annotation(
            x=midday, y=1.02, yref="y1", 
            text=f"<b>{midday.strftime('%a')}</b>",
            showarrow=False, font=dict(size=9), yanchor="bottom"
        )
        if i < len(sun_data) - 1:
            sunset = sun_data['sunset'].iloc[i]
            sunrise_next = sun_data['sunrise'].iloc[i+1]
            mid_night = sunset + (sunrise_next - sunset) / 2
            fig_bot.add_vrect(x0=sunset, x1=sunrise_next, fillcolor="gray", opacity=0.05, line_width=0, row=2, col=1)
            fig_bot.add_annotation(x=mid_night, y=0.5, yref="y1", text="🌙", showarrow=False, font=dict(size=10))

    idx_now = (df['time'] - now_nz).abs().idxmin()
    fig_bot.add_vline(x=df.loc[idx_now, 'time'], line_width=1.5, line_dash="dot", line_color="green")
    
    fig_bot.update_layout(
        height=280, margin=dict(t=15, b=0, l=5, r=5), 
        template="plotly_white", hovermode="x unified",
        xaxis2=dict(showticklabels=False), 
        yaxis=dict(showticklabels=False, fixedrange=True, range=[0, 1.4], showgrid=False),
        yaxis2=dict(title=None, showticklabels=False, fixedrange=True, showgrid=True), 
        bargap=0
    )

    # --- RENDER ---
    st.title(f"🌬️ {selection}: {df.loc[idx_now, 'wind']:.1f} kn")
    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})
    st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Error loading data")
