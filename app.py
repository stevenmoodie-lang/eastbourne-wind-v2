import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

# --- CSS: CLEAN UI ---
st.markdown("""
    <style>
        [data-testid="stHeader"], header { visibility: hidden; height: 0; }
        .stAppViewContainer { top: -30px !important; } 
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { padding: 1.8rem 0.5rem 0.5rem 0.5rem !important; }
        .custom-title { text-align: center; font-size: 1.3rem; font-weight: 700; color: #ffffff; margin-bottom: 0.3rem; }
    </style>
    <div class="custom-title">Eastbourne Wind</div>
""", unsafe_allow_html=True)

# --- TIDE MODEL (Wellington Harbor) ---
def calculate_wellington_tide(times):
    t_ref = pd.Timestamp("2026-05-12 00:10:00") 
    hours = (times - t_ref).total_seconds() / 3600.0
    m2 = 0.45 * np.cos(2 * np.pi * hours / 12.42)
    s2 = 0.15 * np.cos(2 * np.pi * hours / 12.00)
    return 1.1 + m2 + s2 

def get_color(knots):
    if knots <= 6: return "rgba(169, 201, 217, 1.0)"
    if knots <= 11: return "rgba(92, 169, 204, 1.0)"
    if knots <= 15: return "rgba(122, 214, 134, 1.0)"
    if knots <= 19: return "rgba(255, 230, 109, 1.0)"
    if knots <= 28: return "rgba(255, 126, 121, 1.0)"
    return "rgba(188, 108, 167, 1.0)"

@st.cache_data(ttl=600)
def get_clean_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": -41.405, "longitude": 174.867, 
        "hourly": ["wind_speed_10m", "wind_direction_10m"], 
        "daily": ["sunrise", "sunset"], 
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kn", "forecast_days": 7
    }
    r = requests.get(url, params=params).json()
    
    def to_nz(raw): return pd.to_datetime(raw).tz_localize(None)
    
    df_h = pd.DataFrame({
        "time": to_nz(r["hourly"]["time"]), 
        "speed": r["hourly"]["wind_speed_10m"], 
        "dir": r["hourly"]["wind_direction_10m"]
    })
    
    # Simple Date Extraction
    df_s = pd.DataFrame({
        "date": [pd.to_datetime(t).date() for t in r["daily"]["time"]],
        "sunrise": to_nz(r["daily"]["sunrise"]), 
        "sunset": to_nz(r["daily"]["sunset"])
    })
    
    t_range = pd.date_range(start=df_h['time'].min(), end=df_h['time'].max(), freq='15min')
    df_tide = pd.DataFrame({
        "time": t_range, 
        "height": [calculate_wellington_tide(t) for t in t_range]
    })
    return df_h, df_s, df_tide

try:
    df_hourly, df_sun, df_tide = get_clean_data()
    now = pd.Timestamp.now(tz='Pacific/Auckland').tz_localize(None)
    max_wind = df_hourly['speed'].max()
    t_min, t_max = df_hourly['time'].min(), df_hourly['time'].max()

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
                avg_s = d['speed'].mean()
                fig_ribbon.add_trace(go.Bar(x=[x_id], y=[1], marker=dict(color=get_color(avg_s), line=dict(width=0)), showlegend=False))
                fig_ribbon.add_annotation(x=x_id, y=0.5, text="➤", showarrow=False, textangle=((d['dir'].mean()+180)%360)-90, font=dict(size=8, color="white"))
                fig_ribbon.add_annotation(x=x_id, y=-0.3, text=f"<b>{round(avg_s)}</b>", showarrow=False, font=dict(size=7, color="white"))
        fig_ribbon.add_trace(go.Bar(x=[f"{day['date']}_sp"], y=[1], marker=dict(color="rgba(0,0,0,0)"), showlegend=False))

    fig_ribbon.update_layout(height=85, margin=dict(l=5, r=5, t=25, b=10), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', bargap=0, xaxis=dict(showgrid=False, tickmode='array', tickvals=[f"{d}_1" for d in df_sun['date']], ticktext=[f"<b>{pd.to_datetime(d).strftime('%a')}</b>" for d in df_sun['date']], side="top", tickfont=dict(size=9)))
    st.plotly_chart(fig_ribbon, use_container_width=True, config={'displayModeBar': False})

    # --- 2. MAIN CHART ---
    fig_main = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.65, 0.35])

    # Night Shading (Soft 0.1 Opacity)
    for _, row in df_sun.iterrows():
        d_start = pd.Timestamp(row['date'])
        d_end = d_start + pd.Timedelta(days=1)
        fig_main.add_vrect(x0=d_start, x1=row['sunrise'], fillcolor="black", opacity=0.1, layer="below", line_width=0, row="all", col=1)
        fig_main.add_vrect(x0=row['sunset'], x1=d_end, fillcolor="black", opacity=0.1, layer="below", line_width=0, row="all", col=1)

    # Wind Trace
    fig_main.add_trace(go.Scatter(x=df_hourly['time'], y=df_hourly['speed'], line=dict(color="#5ca9cc", width=2), mode='lines', showlegend=False), row=1, col=1)
    
    # Tide Trace
    fig_main.add_trace(go.Scatter(x=df_tide['time'], y=df_tide['height'], line=dict(color="rgba(255,255,255,0.4)", width=1.5), fill='tozeroy', fillcolor="rgba(255,255,255,0.1)", mode='lines', showlegend=False), row=2, col=1)

    # Now Line
    fig_main.add_vline(x=now, line_width=1.5, line_dash="dash", line_color="white", opacity=0.8)

    fig_main.update_layout(
        height=240, margin=dict(l=10, r=10, t=5, b=5),
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False, range=[t_min, t_max]),
        xaxis2=dict(visible=False, range=[t_min, t_max]),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, showticklabels=False, range=[-2, max_wind + 5]),
        yaxis2=dict(visible=False, range=[0, 2.5])
    )
    
    st.plotly_chart(fig_main, use_container_width=True, config={'displayModeBar': False})

except Exception as e:
    st.error(f"Error: {e}")
