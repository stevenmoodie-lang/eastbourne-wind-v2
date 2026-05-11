import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pytz

# --- PAGE CONFIG & CSS ---
st.set_page_config(page_title="Eastbourne Wind", layout="wide")

# Custom CSS for "Lighter Again" Cloudy Slate Theme
st.markdown("""
    <style>
        .stApp {
            background-color: #3d5a73;
            color: #f8f9fa;
        }
        .block-container { padding-top: 1.5rem; padding-bottom: 0rem; }
        h1 { font-size: 1.8rem !important; margin-bottom: 0px !important; color: #ffffff !important; }
        .subtitle { font-size: 0.9rem; color: #d1d9e0; margin-bottom: 10px; }
        .stButton button { 
            margin-top: 8px; 
            padding: 2px 10px; 
            background-color: #4e6a82; 
            color: white; 
            border: 1px solid #7f8c8d; 
        }
        .stPlotlyChart { margin-bottom: 5px !important; } 
        section[data-testid="stSidebar"] {
            background-color: #2c3e50;
        }
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

# --- DATA PROCESSING ---
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

    # --- 1. TOP SUMMARY ---
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
        fig_top.add_annotation(x=str(row['date_only']), y=0.5, text=f"<b>{round(row['wind'])} kn</b>", showarrow=False, font=dict(size=13, color="white"))

    fig_top.update_layout(
        height=110, margin=dict(t=35, b=0, l=5, r=5), 
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        bargap=0.05, xaxis=dict(showticklabels=False), yaxis=dict(showticklabels=False, range=[0, 1.4])
    )
    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})

    # --- 2. BOTTOM GRAPH ---
    fig_bot = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.12, 0.88])
    
    # ROW 1: 4-Hourly Heatstrip with Arrows
    df_4h = df.resample('4h', on='time', origin='start_day').agg({'wind': 'mean', 'dir': 'mean'}).reset_index()
    for _, row in df_4h.iterrows():
        fig_bot.add_trace(go.Bar(
            x=[row['time'] + timedelta(hours=2)], y=[1], width=1000*3600*4,
            marker_color=get_color(row['wind']), showlegend=False, hoverinfo='none'
        ), row=1, col=1)
        fig_bot.add_annotation(
            x=row['time'] + timedelta(hours=2), y=0.5, yref="y1",
            text="➤", textangle=row['dir']-90,
            showarrow=False, font=dict(size=14, color="white"), row=1, col=1
        )

    # ROW 2: Wind Speed Line (Colored Segments)
    for i in range(len(df)-1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        opacity = 0.2 if (p1['is_night'] and p2['is_night']) else 1.0
        fig_bot.add_trace(go.Scatter(
            x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']], 
            mode='lines', line=dict(color=get_color(p1['wind'], opacity=opacity), width=2.5), 
            showlegend=False, hoverinfo='none'
        ), row=2, col=1)

    # Night Shading
    for i in range(len(sun_data)-1):
        fig_bot.add_vrect(x0=sun_data['sunset'].iloc[i], x1=sun_data['sunrise'].iloc[i+1], fillcolor="#2c3e50", opacity=0.4, line_width=0, row="all")
    
    # PEAK & VALLEY ANNOTATIONS
    for d_date in df['date_only'].unique():
        day_block = df[df['date_only'] == d_date]
        if not day_block.empty:
            # Peak
            peak = day_block.loc[day_block['wind'].idxmax()]
            fig_bot.add_annotation(x=peak['time'], y=peak['wind'], text=f"<b>{round(peak['wind'])}</b>", 
                                   showarrow=False, yshift=15, font=dict(size=10, color="white"), row=2, col=1)
            # Valley
            valley = day_block.loc[day_block['wind'].idxmin()]
            fig_bot.add_annotation(x=valley['time'], y=valley['wind'], text=f"<b>{round(valley['wind'])}</b>", 
                                   showarrow=False, yshift=-15, font=dict(size=10, color="#bdc3c7"), row=2, col=1)

    # X-Axis Day Labels
    tick_vals = [pd.to_datetime(d) + timedelta(hours=12) for d in df['date_only'].unique()]
    tick_text = [pd.to_datetime(d).strftime('%a') for d in df['date_only'].unique()]

    fig_bot.update_layout(
        height=380, margin=dict(t=10, b=0, l=5, r=5), 
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis1=dict(showticklabels=False, range=[0, 1], showgrid=False),
        yaxis2=dict(showticklabels=False, title=None, side="left", showgrid=True, gridcolor="rgba(255,255,255,0.08)"),
        xaxis2=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_text, showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickfont=dict(size=11, color="white", family="Arial Black"))
    )

    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Error loading data")
