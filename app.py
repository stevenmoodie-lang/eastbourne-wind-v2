import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
from datetime import timedelta
import pytz
import numpy as np

# --- PAGE CONFIG & CSS ---
st.set_page_config(page_title="Eastbourne Wind & Tide", layout="wide")

st.markdown("""
    <style>
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { padding-top: 1.5rem; padding-bottom: 0rem; }
        h1 { font-size: 1.8rem !important; margin-bottom: 0px !important; color: #ffffff !important; }
        .subtitle { font-size: 0.9rem; color: #d1d9e0; margin-bottom: 10px; }
        .stButton button { 
            margin-top: 8px; padding: 2px 10px; 
            background-color: #4e6a82; color: white; border: 1px solid #7f8c8d; 
        }
        section[data-testid="stSidebar"] { background-color: #2c3e50; }
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

@st.cache_data(ttl=3600)
def get_tide_data(days):
    start_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    times = pd.date_range(start=start_time, periods=days*24*12, freq='5min')
    tide_heights = [1.0 + 0.6 * np.sin((t.timestamp() / 22357) * np.pi) for t in times]
    return pd.DataFrame({'time': times, 'height': tide_heights})

selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
forecast_range = st.sidebar.radio("Range", ["7 Days", "3 Days"], index=0)
days_to_fetch = 7 if forecast_range == "7 Days" else 3

coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"], days_to_fetch)
tide_df = get_tide_data(days_to_fetch)

nz_tz = pytz.timezone('Pacific/Auckland')
now_nz = datetime.datetime.now(nz_tz).replace(tzinfo=None)

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

    idx_now = (df['time'] - now_nz).abs().idxmin()
    col1, col2 = st.columns([6, 1]) 
    with col1:
        st.markdown(f"<h1>Eastbourne Wind: {round(df.loc[idx_now, 'wind'])} kn</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtitle'>Monitoring at <b>{selection}</b> — Currently <b>{get_direction_label(df.loc[idx_now, 'dir'])}</b></div>", unsafe_allow_html=True)
    with col2:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

    # --- 1. TOP SUMMARY HEATSTRIP ---
    day_df = df[~df['is_night']].copy()
    daily_summary = day_df.groupby('date_only').agg({'wind': 'mean', 'dir': lambda x: x.mode()[0]}).reset_index()
    
    fig_top = go.Figure()
    fig_top.add_trace(go.Bar(
        x=daily_summary['date_only'].astype(str), y=[1]*len(daily_summary), 
        marker_color=[get_color(w) for w in daily_summary['wind']], 
        showlegend=False, hoverinfo='none'
    ))

    for i, row in daily_summary.iterrows():
        date_label = pd.to_datetime(row['date_only']).strftime('%a')
        fig_top.add_annotation(x=str(row['date_only']), y=1.22, text=f"<b>{date_label}</b>", showarrow=False, font=dict(size=11, color="white"))
        fig_top.add_annotation(x=str(row['date_only']), y=0.6, text=f"<b>{round(row['wind'])} kn</b>", showarrow=False, font=dict(size=13, color="white"))
        fig_top.add_annotation(x=str(row['date_only']), y=0.2, text="➤", textangle=row['dir']-90, showarrow=False, font=dict(size=12, color="rgba(255,255,255,0.8)"))

    fig_top.update_layout(
        height=100, margin=dict(t=30, b=0, l=5, r=5), 
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        bargap=0.05, xaxis=dict(showticklabels=False, showgrid=False, zeroline=False), 
        yaxis=dict(showticklabels=False, range=[0, 1.4], showgrid=False, zeroline=False)
    )
    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})

    # --- 2. DETAILED GRAPHS (MAX COMPRESSION) ---
    fig_bot = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
        row_heights=[0.05, 0.50, 0.35] # Flattened wind (row 2) and tide (row 3)
    )
    
    # 3-segment Heatblocks (Row 1)
    heat_blocks = []
    for i in range(len(sun_data)):
        day_start, day_end = sun_data.iloc[i]['sunrise'], sun_data.iloc[i]['sunset']
        day_step = (day_end - day_start) / 3
        for s in range(3):
            t0, t1 = day_start + s*day_step, day_start + (s+1)*day_step
            mask = (df['time'] >= t0) & (df['time'] < t1)
            if not df[mask].empty:
                heat_blocks.append({'time': t0, 'end': t1, 'wind': df[mask]['wind'].mean(), 'dir': df[mask]['dir'].mean(), 'is_night': False})
        if i < len(sun_data) - 1:
            night_start, night_end = day_end, sun_data.iloc[i+1]['sunrise']
            night_step = (night_end - night_start) / 3
            for s in range(3):
                t0, t1 = night_start + s*night_step, night_start + (s+1)*night_step
                mask = (df['time'] >= t0) & (df['time'] < t1)
                if not df[mask].empty:
                    heat_blocks.append({'time': t0, 'end': t1, 'wind': df[mask]['wind'].mean(), 'dir': df[mask]['dir'].mean(), 'is_night': True})

    for b in heat_blocks:
        block_color = "#2c3e50" if b['is_night'] else get_color(b['wind'])
        mid_point = b['time'] + (b['end'] - b['time']) / 2
        fig_bot.add_trace(go.Bar(
            x=[mid_point], y=[1], width=(b['end'] - b['time']).total_seconds() * 1000, 
            marker_color=block_color, showlegend=False, hoverinfo='none'
        ), row=1, col=1)
        fig_bot.add_annotation(x=mid_point, y=0.5, yref="y1", text="➤", textangle=b['dir']-90, showarrow=False, font=dict(size=9, color="white" if not b['is_night'] else "rgba(255,255,255,0.1)"), row=1, col=1)

    # Wind Line (Row 2)
    for i in range(len(df)-1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        op = 0.2 if (p1['is_night'] and p2['is_night']) else 1.0
        fig_bot.add_trace(go.Scatter(
            x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']], 
            mode='lines', line=dict(color=get_color(p1['wind'], opacity=op), width=2), 
            showlegend=False, hoverinfo='none'
        ), row=2, col=1)

    # Balanced Labels (Optimized for flat graph)
    for d_date in df['date_only'].unique():
        day_block = df[(df['date_only'] == d_date) & (~df['is_night'])]
        if not day_block.empty:
            peak = day_block.loc[day_block['wind'].idxmax()]
            fig_bot.add_annotation(
                x=peak['time'], y=peak['wind'], text=f"<b>{round(peak['wind'])}</b>", 
                showarrow=False, yshift=10, xshift=-7, font=dict(size=10, color="white"), row=2, col=1
            )
            fig_bot.add_annotation(
                x=peak['time'], y=peak['wind'], text="➤", textangle=peak['dir']-90, 
                showarrow=False, yshift=10, xshift=7, font=dict(size=8, color="white"), row=2, col=1
            )
            valley = day_block.loc[day_block['wind'].idxmin()]
            fig_bot.add_annotation(
                x=valley['time'], y=valley['wind'], text=f"<b>{round(valley['wind'])}</b>", 
                showarrow=False, yshift=-10, xshift=-7, font=dict(size=10, color="#d1d9e0"), row=2, col=1
            )
            fig_bot.add_annotation(
                x=valley['time'], y=valley['wind'], text="➤", textangle=valley['dir']-90, 
                showarrow=False, yshift=-10, xshift=7, font=dict(size=8, color="#d1d9e0"), row=2, col=1
            )

    # Tide Silhouette (Row 3)
    fig_bot.add_trace(go.Scatter(
        x=tide_df['time'], y=tide_df['height'], fill='tozeroy', mode='lines',
        line=dict(color='#5dade2', width=1.2), fillcolor='rgba(93, 173, 226, 0.15)',
        showlegend=False, hoverinfo='none'
    ), row=3, col=1)

    tide_vals = tide_df['height'].values
    for i in range(1, len(tide_vals) - 1):
        if tide_vals[i] > tide_vals[i-1] and tide_vals[i] > tide_vals[i+1]:
            fig_bot.add_annotation(x=tide_df.iloc[i]['time'], y=tide_vals[i], text=tide_df.iloc[i]['time'].strftime('%H:%M'), showarrow=False, yshift=6, font=dict(size=8, color="#5dade2"), row=3, col=1)
        if tide_vals[i] < tide_vals[i-1] and tide_vals[i] < tide_vals[i+1]:
            fig_bot.add_annotation(x=tide_df.iloc[i]['time'], y=tide_vals[i], text=tide_df.iloc[i]['time'].strftime('%H:%M'), showarrow=False, yshift=-6, font=dict(size=8, color="#d1d9e0"), row=3, col=1)

    for i in range(len(sun_data)-1):
        fig_bot.add_vrect(x0=sun_data['sunset'].iloc[i], x1=sun_data['sunrise'].iloc[i+1], fillcolor="#2c3e50", opacity=0.35, line_width=0, row="all")

    tick_vals = [pd.to_datetime(d) + timedelta(hours=12) for d in df['date_only'].unique()]
    tick_text = [f"<b>{pd.to_datetime(d).strftime('%a')}</b>" for d in df['date_only'].unique()]

    fig_bot.update_layout(
        height=420, # Ultra-compact height for mobile
        margin=dict(t=5, b=5, l=5, r=5), template="plotly_dark", 
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis1=dict(showticklabels=False, range=[0, 1], showgrid=False, zeroline=False),
        yaxis2=dict(showticklabels=False, showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        yaxis3=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 2]),
        xaxis1=dict(showticklabels=False),
        xaxis2=dict(showticklabels=True, tickmode='array', tickvals=tick_vals, ticktext=tick_text, showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickfont=dict(size=11, color="white")),
        xaxis3=dict(showticklabels=False, showgrid=False)
    )

    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Error loading data")
