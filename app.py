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
            text-align: center; font-size: 1.3rem; font-weight: 700; color: #ffffff; margin-bottom: 0.3rem;
        }
    </style>
    <div class="custom-title">Eastbourne Wind</div>
""", unsafe_allow_html=True)

# --- TIDE MODEL (Wellington Harbour) ---
def calculate_wellington_tide(times):
    # Reference high tide for Wellington (approx epoch for 2026)
    t_ref = pd.Timestamp("2026-05-12 00:10:00") 
    hours = (times - t_ref).total_seconds() / 3600.0
    m2 = 0.45 * np.cos(2 * np.pi * hours / 12.42)
    s2 = 0.15 * np.cos(2 * np.pi * hours / 12.00)
    return 1.1 + m2 + s2 

def get_color(knots, alpha=1.0):
    if knots <= 6: return f"rgba(169, 201, 217, {alpha})"
    if knots <= 11: return f"rgba(92, 169, 204, {alpha})"
    if knots <= 15: return f"rgba(122, 214, 134, {alpha})"
    if knots <= 19: return f"rgba(255, 230, 109, {alpha})"
    if knots <= 28: return f"rgba(255, 126, 121, {alpha})"
    return f"rgba(188, 108, 167, {alpha})"

@st.cache_data(ttl=600)
def get_weather_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": -41.405, 
        "longitude": 174.867, 
        "hourly": ["wind_speed_10m", "wind_direction_10m"], 
        "daily": ["sunrise", "sunset"], 
        "timezone": "Pacific/Auckland", 
        "wind_speed_unit": "kn", 
        "forecast_days": 7
    }
    r = requests.get(url, params=params).json()
    
    # Ensure all times are converted to naive local for clean comparison
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
    
    t_range = pd.date_range(start=df['time'].min(), end=df['time'].max(), freq='15min')
    df_tide = pd.DataFrame({"time": t_range, "height": [calculate_wellington_tide(t) for t in t_range]})
    return df, sun, df_tide

try:
    df_hourly, df_sun, df_tide = get_weather_data()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=12))).replace(tzinfo=None)
    max_wind = df_hourly['speed'].max()
    crop_start, crop_end = df_sun['sunrise'].min(), df_sun['sunset'].max()

    # --- 1. TOP RIBBON ---
    fig_ribbon = go.Figure()
    for _, day in df_sun.iterrows():
        sunrise, sunset = day['sunrise'], day['sunset']
        seg_dur = (sunset - sunrise) / 3
        for i in range(3):
            t0, t1 = sunrise + (i*seg_dur), sunrise + ((i+1)*seg_dur)
            d = df_hourly[(df_hourly['time'] >= t0) & (df_hourly['time'] < t1)]
            if not d.empty:
                x_id = f"{day['date']}_{i}"
                fig_ribbon.add_trace(go.Bar(x=[x_id], y=[1], marker=dict(color=get_color(d['speed'].mean()), line=dict(width=0)), showlegend=False))
                fig_ribbon.add_annotation(x=x_id, y=0.5, text="➤", showarrow=False, textangle=((d['dir'].mean()+180)%360)-90, font=dict(size=7, color="white"))
                fig_ribbon.add_annotation(x=x_id, y=-0.3, text=f"<b>{round(d['speed'].mean())}</b>", showarrow=False, font=dict(size=7, color="white"))
        fig_ribbon.add_trace(go.Bar(x=[f"{day['date']}_sp"], y=[1], marker=dict(color="rgba(0,0,0,0)", line=dict(width=0)), showlegend=False))

    fig_ribbon.update_layout(
        height=85, margin=dict(l=5, r=5, t=25, b=10), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', bargap=0, 
        xaxis=dict(showgrid=False, tickmode='array', tickvals=[f"{d}_1" for d in df_sun['date']], ticktext=[f"<b>{d.strftime('%a')}</b>" for d in df_sun['date']], side="top", tickfont=dict(size=9, color="white")), 
        yaxis=dict(visible=False, fixedrange=True)
    )
    st.plotly_chart(fig_ribbon, use_container_width=True, config={'displayModeBar': False})

    # --- 2. MAIN DASHBOARD ---
    fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.6, 0.4])

    # WIND PLOT: Localized Daylight Check
    for i in range(len(df_hourly)-1):
        p1, p2 = df_hourly.iloc[i], df_hourly.iloc[i+1]
        # Get sun info for the specific day p1 falls on
        day_info = df_sun[df_sun['date'] == p1['time'].date()]
        if not day_info.empty:
            sr, ss = day_info.iloc[0]['sunrise'], day_info.iloc[0]['sunset']
            is_night = p1['time'] < sr or p1['time'] >= ss
            fig_main.add_trace(go.Scatter(x=[p1['time'], p2['time']], y=[p1['speed'], p2['speed']], line=dict(color=get_color(p1['speed'], 0.12 if is_night else 1.0), width=1.5), mode='lines', showlegend=False), row=1, col=1)

    # TIDE PLOT: Synchronized Daylight Check
    day_tide_x, day_tide_y = [], []
    night_tide_x, night_tide_y = [], []
    
    for i, row in df_tide.iterrows():
        day_info = df_sun[df_sun['date'] == row['time'].date()]
        if not day_info.empty:
            sr, ss = day_info.iloc[0]['sunrise'], day_info.iloc[0]['sunset']
            if sr <= row['time'] <= ss:
                day_tide_x.append(row['time']); day_tide_y.append(row['height'])
                night_tide_x.append(None); night_tide_y.append(None)
            else:
                night_tide_x.append(row['time']); night_tide_y.append(row['height'])
                day_tide_x.append(None); day_tide_y.append(None)

    fig_main.add_trace(go.Scatter(x=day_tide_x, y=day_tide_y, line=dict(color="white", width=0.8), fill='tozeroy', fillcolor="rgba(255,255,255,0.03)", mode='lines', showlegend=False), row=2, col=1)
    fig_main.add_trace(go.Scatter(x=night_tide_x, y=night_tide_y, line=dict(color="rgba(255,255,255,0.05)", width=0.8), mode='lines', showlegend=False), row=2, col=1)

    # Markers, Mid-day & Night Shading
    for _, day in df_sun.iterrows():
        midday = day['sunrise'] + (day['sunset'] - day['sunrise']) / 2
        fig_main.add_vline(x=midday, line_width=0.5, line_dash="dot", line_color="rgba(255,255,255,0.15)")
        fig_main.add_annotation(x=midday, y=max_wind + 6, text=f"<b>{day['date'].strftime('%a')}</b>", showarrow=False, font=dict(size=9, color="rgba(255,255,255,0.6)"), row=1, col=1)
        fig_main.add_annotation(x=day['sunrise'], y=-2, text=f"☼ {day['sunrise'].strftime('%H:%M')}", showarrow=False, font=dict(size=6, color="rgba(255,255,255,0.25)"), row=1, col=1)
        fig_main.add_annotation(x=day['sunset'], y=-2, text=f"☾ {day['sunset'].strftime('%H:%M')}", showarrow=False, font=dict(size=6, color="rgba(255,255,255,0.25)"), row=1, col=1)

        # Labels
        d_data = df_hourly[(df_hourly['time'] >= day['sunrise']) & (df_hourly['time'] <= day['sunset'])]
        if not d_data.empty:
            for f, off in [(d_data.loc[d_data['speed'].idxmax()], 3.5), (d_data.loc[d_data['speed'].idxmin()], -3.5)]:
                fig_main.add_annotation(x=f['time'], y=f['speed'] + (off/2.5), text="➤", textangle=((f['dir']+180)%360)-90, showarrow=False, font=dict(size=6, color="white"), row=1, col=1)
                fig_main.add_annotation(x=f['time'], y=f['speed'] + off, text=f"<b>{round(f['speed'])}</b>", showarrow=False, font=dict(size=8, color="white"), row=1, col=1)

    # Night Shading (rectangles)
    for i in range(len(df_sun)-1):
        fig_main.add_vrect(x0=df_sun.iloc[i]['sunset'], x1=df_sun.iloc[i+1]['sunrise'], fillcolor="rgba(0,0,0,0.2)", layer="below", line_width=0)
    
    fig_main.add_vline(x=now, line_width=1, line_dash="dash", line_color="white", opacity=0.6)

    fig_main.update_layout(height=200, margin=dict(l=10, r=10, t=5, b=5), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False, range=[crop_start, crop_end]), xaxis2=dict(visible=False, range=[crop_start, crop_end]), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.03)', zeroline=False, showticklabels=False, range=[-5, max_wind + 10]), yaxis2=dict(visible=False, range=[0, 2.2]))
    st.plotly_chart(fig_main, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Sync Error: {e}")
