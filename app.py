import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

# --- CSS: MOBILE OPTIMIZATION ---
st.markdown("""
    <style>
        [data-testid="stHeader"], header { visibility: hidden; height: 0; }
        .stAppViewContainer { top: -30px !important; } 
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { 
            padding-top: 1.8rem !important; 
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .custom-title {
            text-align: center;
            font-size: 1.3rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.3rem;
            white-space: nowrap;
        }
    </style>
    <div class="custom-title">Eastbourne Wind</div>
""", unsafe_allow_html=True)

# --- SETTINGS: DATA FROM BARING HEAD ---
LAT, LON = -41.405, 174.867

def get_color(knots, alpha=1.0):
    # Vibrant Pastel Palette: Softer than neon, but punchier than "dusty"
    if knots <= 6: return f"rgba(149, 159, 239, {alpha})"    # Nova Blue
    if knots <= 11: return f"rgba(113, 174, 242, {alpha})"   # Sky Drift
    if knots <= 15: return f"rgba(150, 212, 112, {alpha})"   # Green Shimmer (Fresh & Punchy)
    if knots <= 19: return f"rgba(242, 238, 143, {alpha})"   # Warm Yellow
    if knots <= 28: return f"rgba(241, 163, 187, {alpha})"   # Cecilia Pink/Red
    return f"rgba(172, 104, 215, {alpha})"                   # Lilac Purple

@st.cache_data(ttl=600)
def get_weather_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT, "longitude": LON,
        "hourly": ["wind_speed_10m", "wind_direction_10m"],
        "daily": ["sunrise", "sunset"],
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kn", "forecast_days": 7
    }
    r = requests.get(url, params=params).json()
    df = pd.DataFrame({
        "time": pd.to_datetime(r["hourly"]["time"]),
        "speed": r["hourly"]["wind_speed_10m"],
        "dir": r["hourly"]["wind_direction_10m"]
    })
    sun = pd.DataFrame({
        "date": pd.to_datetime(r["daily"]["time"]).date,
        "sunrise": pd.to_datetime(r["daily"]["sunrise"]),
        "sunset": pd.to_datetime(r["daily"]["sunset"])
    })
    tide_times = pd.date_range(start=df['time'].min(), end=df['time'].max(), freq='15min')
    tide_heights = [1.0 + 0.6 * np.sin(2 * np.pi * (t.hour + t.minute/60) / 12.4) for t in tide_times]
    df_tide = pd.DataFrame({"time": tide_times, "height": tide_heights})
    return df, sun, df_tide

try:
    df_hourly, df_sun, df_tide = get_weather_data()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=12))).replace(tzinfo=None)
    max_wind = df_hourly['speed'].max()
    
    crop_start = df_sun['sunrise'].min()
    crop_end = df_sun['sunset'].max()

    # --- 1. DYNAMIC ARROW RIBBON ---
    segments = []
    for _, day in df_sun.iterrows():
        sunrise, sunset = day['sunrise'], day['sunset']
        seg_dur = (sunset - sunrise) / 3
        for i in range(3):
            t0, t1 = sunrise + (i*seg_dur), sunrise + ((i+1)*seg_dur)
            mask = (df_hourly['time'] >= t0) & (df_hourly['time'] < t1)
            d = df_hourly[mask]
            if not d.empty:
                rads = np.deg2rad(d['dir'])
                avg_dir = np.rad2deg(np.arctan2(np.sin(rads).mean(), np.cos(rads).mean())) % 360
                segments.append({"x_id": f"{day['date']}_{i}", "speed": d['speed'].mean(), "dir": avg_dir})
        segments.append({"x_id": f"{day['date']}_spacer", "spacer": True})

    fig_ribbon = go.Figure()
    for s in segments:
        if "spacer" in s:
            fig_ribbon.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color="rgba(0,0,0,0)", showlegend=False))
            continue
        fig_ribbon.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color=get_color(s['speed']), showlegend=False))
        heading = (s['dir'] + 180) % 360
        y_arrow = 0.5 + (0.3 * np.cos(np.deg2rad(s['dir'])))
        fig_ribbon.add_annotation(x=s['x_id'], y=y_arrow, text="➤", showarrow=False, textangle=heading-90, font=dict(size=7, color="white"))
        fig_ribbon.add_annotation(x=s['x_id'], y=-0.3, text=f"<b>{round(s['speed'])}</b>", showarrow=False, font=dict(size=7, color="white"))

    fig_ribbon.update_layout(
        height=85, margin=dict(l=5, r=5, t=25, b=10), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', bargap=0,
        xaxis=dict(showgrid=False, tickmode='array', tickvals=[f"{d}_1" for d in df_sun['date']], 
                   ticktext=[f"<b>{d.strftime('%a')}</b>" for d in df_sun['date']], side="top", 
                   tickfont=dict(size=9, color="white"), fixedrange=True),
        yaxis=dict(visible=False, range=[-0.6, 1.1], fixedrange=True)
    )
    st.plotly_chart(fig_ribbon, use_container_width=True, config={'displayModeBar': False})

    # --- 2. COMPACT WIND & TIDE DASHBOARD ---
    fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.6, 0.4])

    for i in range(len(df_hourly)-1):
        p1, p2 = df_hourly.iloc[i], df_hourly.iloc[i+1]
        day_info = df_sun[df_sun['date'] == p1['time'].date()].iloc[0]
        sr, ss = day_info['sunrise'], day_info['sunset']
        transition_points = sorted([t for t in [sr, ss] if p1['time'] < t < p2['time']])
        current_times = [p1['time']] + transition_points + [p2['time']]
        for j in range(len(current_times)-1):
            t_start, t_end = current_times[j], current_times[j+1]
            if t_end < crop_start or t_start > crop_end: continue
            frac = (t_start - p1['time']) / (p2['time'] - p1['time']) if p2['time'] != p1['time'] else 0
            interp_speed = p1['speed'] + frac * (p2['speed'] - p1['speed'])
            is_night = t_start < sr or t_start >= ss
            alpha = 0.12 if is_night else 1.0
            fig_main.add_trace(go.Scatter(
                x=[t_start, t_end], y=[interp_speed, interp_speed + (p2['speed']-p1['speed']) * ((t_end-t_start)/(p2['time']-p1['time']))],
                line=dict(color=get_color(interp_speed, alpha), width=2 if not is_night else 1),
                mode='lines', showlegend=False, hoverinfo='skip'
            ), row=1, col=1)

    for _, day_sun in df_sun.iterrows():
        midpoint = day_sun['sunrise'] + (day_sun['sunset'] - day_sun['sunrise']) / 2
        fig_main.add_annotation(x=midpoint, y=max_wind + 6, text=f"<b>{day_sun['date'].strftime('%a')}</b>", showarrow=False, font=dict(size=9, color="rgba(255,255,255,0.6)"), row=1, col=1)
        day_mask = (df_hourly['time'] >= day_sun['sunrise']) & (df_hourly['time'] <= day_sun['sunset'])
        day_data = df_hourly[day_mask]
        if not day_data.empty:
            for func, offset in [(day_data.loc[day_data['speed'].idxmax()], 3.5), (day_data.loc[day_data['speed'].idxmin()], -3.5)]:
                heading = (func['dir'] + 180) % 360
                fig_main.add_annotation(x=func['time'], y=func['speed'] + (offset/2.5), text="➤", textangle=heading-90, showarrow=False, font=dict(size=6, color="white"), row=1, col=1)
                fig_main.add_annotation(x=func['time'], y=func['speed'] + offset, text=f"<b>{round(func['speed'])}</b>", showarrow=False, font=dict(size=8, color="white"), row=1, col=1)

    fig_main.add_trace(go.Scatter(x=df_tide['time'], y=df_tide['height'], fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.05)', line=dict(color='#00d4ff', width=1), showlegend=False, hoverinfo='skip'), row=2, col=1)
    
    for i in range(1, len(df_tide)-1):
        prev, curr, nxt = df_tide.iloc[i-1]['height'], df_tide.iloc[i]['height'], df_tide.iloc[i+1]['height']
        if (curr > prev and curr > nxt) or (curr < prev and curr < nxt):
            t = df_tide.iloc[i]
            if crop_start <= t['time'] <= crop_end:
                fig_main.add_annotation(x=t['time'], y=t['height'], text=t['time'].strftime('%H:%M'), showarrow=False, font=dict(size=7, color="#00d4ff"), yshift=6 if curr > prev else -6, row=2, col=1)

    for i in range(len(df_sun)-1):
        fig_main.add_vrect(x0=df_sun.iloc[i]['sunset'], x1=df_sun.iloc[i+1]['sunrise'], fillcolor="rgba(0,0,0,0.2)", layer="below", line_width=0)
    fig_main.add_vline(x=now, line_width=1, line_dash="dash", line_color="white", opacity=0.6)

    fig_main.update_layout(
        height=200, margin=dict(l=10, r=10, t=5, b=5), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False, fixedrange=False, range=[crop_start, crop_end]), 
        xaxis2=dict(visible=False, fixedrange=False, range=[crop_start, crop_end]),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.03)', zeroline=False, fixedrange=True, showticklabels=False, range=[-5, max_wind + 10]),
        yaxis2=dict(showgrid=False, zeroline=False, fixedrange=True, showticklabels=False, range=[0, 2.2])
    )
    st.plotly_chart(fig_main, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': True})

except Exception as e:
    st.error(f"Layout Error: {e}")
