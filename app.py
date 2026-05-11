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
        .stAppViewContainer { top: -45px !important; }
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { 
            padding-top: 3rem !important; 
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .custom-title {
            text-align: center;
            font-size: 1.8rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.8rem;
        }
    </style>
    <div class="custom-title">Eastbourne Wind</div>
""", unsafe_allow_html=True)

# --- SETTINGS & RATINGS ---
LAT, LON = -41.291, 174.894

def get_color(knots):
    if knots <= 6: return "rgba(173, 216, 230, 1.0)"    
    if knots <= 11: return "rgba(135, 206, 250, 1.0)"   
    if knots <= 15: return "rgba(0, 128, 0, 1.0)"       
    if knots <= 19: return "rgba(255, 200, 50, 1.0)"    
    if knots <= 28: return "rgba(255, 0, 0, 1.0)"       
    return "rgba(139, 0, 0, 1.0)"                       

@st.cache_data(ttl=600)
def get_weather_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT, "longitude": LON,
        "hourly": ["wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"],
        "daily": ["sunrise", "sunset"],
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kn", "forecast_days": 7
    }
    r = requests.get(url, params=params).json()
    df = pd.DataFrame({
        "time": pd.to_datetime(r["hourly"]["time"]),
        "speed": r["hourly"]["wind_speed_10m"],
        "gust": r["hourly"]["wind_gusts_10m"],
        "dir": r["hourly"]["wind_direction_10m"]
    })
    sun = pd.DataFrame({
        "date": pd.to_datetime(r["daily"]["time"]).date,
        "sunrise": pd.to_datetime(r["daily"]["sunrise"]),
        "sunset": pd.to_datetime(r["daily"]["sunset"])
    })
    
    tide_times = pd.date_range(start=df['time'].min(), periods=24*7, freq='h')
    tide_heights = [1.0 + 0.6 * np.sin(2 * np.pi * (t.hour + t.minute/60) / 12.4) for t in tide_times]
    df_tide = pd.DataFrame({"time": tide_times, "height": tide_heights})
    
    return df, sun, df_tide

try:
    df_hourly, df_sun, df_tide = get_weather_data()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=12))).replace(tzinfo=None)

    # --- 1. THE TOP ARROW RIBBON (The New Section) ---
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
            fig_ribbon.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color="rgba(0,0,0,0)", showlegend=False, hoverinfo='skip'))
            continue
        fig_ribbon.add_trace(go.Bar(x=[s['x_id']], y=[1], marker_color=get_color(s['speed']), showlegend=False, hoverinfo='none'))
        heading = (s['dir'] + 180) % 360
        y_pos = 0.5 if (75 < s['dir'] < 105 or 255 < s['dir'] < 285) else (0.35 if 105 <= s['dir'] <= 255 else 0.75)
        fig_ribbon.add_annotation(x=s['x_id'], y=y_pos, text="➤", showarrow=False, textangle=heading-90, font=dict(size=14, color="white"))
        fig_ribbon.add_annotation(x=s['x_id'], y=-0.35, text=f"<b>{round(s['speed'])}</b>", showarrow=False, font=dict(size=11, color="white"))

    fig_ribbon.update_layout(
        height=180, margin=dict(l=5, r=5, t=30, b=10), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', bargap=0,
        xaxis=dict(showgrid=False, tickmode='array', tickvals=[f"{d}_1" for d in df_sun['date']], 
                   ticktext=[f"<b>{d.strftime('%a')}</b>" for d in df_sun['date']], side="top", 
                   tickfont=dict(size=12, color="white"), fixedrange=True),
        yaxis=dict(visible=False, range=[-0.7, 1], fixedrange=True)
    )
    st.plotly_chart(fig_ribbon, use_container_width=True, config={'displayModeBar': False})

    # --- 2. YESTERDAY'S DASHBOARD (Line + Tide Subplots) ---
    fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.20, 0.10])

    # Wind lines
    fig_main.add_trace(go.Scatter(x=df_hourly['time'], y=df_hourly['gust'], fill='tonexty', fillcolor='rgba(255,255,255,0.05)', line=dict(width=0), showlegend=False), row=1, col=1)
    fig_main.add_trace(go.Scatter(x=df_hourly['time'], y=df_hourly['speed'], line=dict(color='white', width=2), showlegend=False), row=1, col=1)

    # Tide silhouette
    fig_main.add_trace(go.Scatter(x=df_tide['time'], y=df_tide['height'], fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.2)', line=dict(color='#00d4ff', width=2), showlegend=False), row=2, col=1)

    # Night Shading & Now Line
    for i in range(len(df_sun)-1):
        fig_main.add_vrect(x0=df_sun.iloc[i]['sunset'], x1=df_sun.iloc[i+1]['sunrise'], fillcolor="rgba(0,0,0,0.3)", layer="below", line_width=0)
    fig_main.add_vline(x=now, line_width=1.5, line_dash="dash", line_color="white", opacity=0.8)

    fig_main.update_layout(
        height=350, margin=dict(l=10, r=10, t=10, b=20), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False, fixedrange=True),
        xaxis2=dict(showgrid=False, tickformat="%a", dtick=86400000.0, tickfont=dict(size=10, color="white"), fixedrange=True),
        yaxis=dict(title=dict(text="Knots", font=dict(size=10, color="white")), showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, fixedrange=True),
        yaxis2=dict(visible=False, fixedrange=True)
    )
    st.plotly_chart(fig_main, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Layout Error: {e}")
