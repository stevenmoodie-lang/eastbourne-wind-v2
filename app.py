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
    # Lighter goldenrod (rgb 238, 195, 82) for better visibility.
    colors = {
        "lightblue": f"rgba(173, 216, 230, {opacity})",
        "dodgerblue": f"rgba(30, 144, 255, {opacity})",
        "green": f"rgba(0, 128, 0, {opacity})",
        "goldenrod_light": f"rgba(238, 195, 82, {opacity})", # Lightened up by ~15%
        "red": f"rgba(255, 0, 0, {opacity})",
        "darkred": f"rgba(139, 0, 0, {opacity})"
    }
    if knots < 5: return colors["lightblue"]
    if knots <= 10: return colors["dodgerblue"]
    if knots <= 15: return colors["green"]
    if knots <= 19: return colors["goldenrod_light"]
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

    # --- 1. TOP GRAPH: DAYLIGHT FOCUS (With Rounded Squares) ---
    day_df = df[~df['is_night']].copy().reset_index(drop=True)
    
    fig_top = go.Figure()
    
    # Calculate unique x positions and dynamic marker size
    num_bars = len(day_df)
    unique_dates = day_df['date_only'].unique()
    
    for d_date in unique_dates:
        group = day_df[day_df['date_only'] == d_date]
        
        # Draw daylight squares with rounded corners
        fig_top.add_trace(go.Scatter(
            x=group['time'],
            y=[1] * len(group),
            mode='markers+text',
            name=str(d_date),
            marker=dict(
                color=[get_color(w) for w in group['wind']],
                symbol='square', # Base shape
                size=26,        # Adjust size to fill the width (calculated for 7 days)
                cornerradius=8, # FIXED: Add rounded corners
                line=dict(color='white', width=2) # Add white space between blocks
            ),
            text=[f"<b>{round(w)}</b>" for w in group['wind']],
            textposition='middle center',
            textfont=dict(size=12, color='white'), # Match previous style
            showlegend=False,
            hoverinfo='none', # Turn off standard hover as we have text/vlines
        ))

        # Add Day Header
        center_time = group['time'].iloc[len(group)//2]
        date_label = f"{group.iloc[0]['time'].strftime('%a')} {group.iloc[0]['time'].day}"
        
        fig_top.add_annotation(x=center_time, y=1.28, text=f"<b>{date_label}</b>", showarrow=False, font=dict(size=11), xanchor="center")
        
        # Day Separator (Wide white line)
        last_time = group['time'].iloc[-1]
        # Calculate separation (1 hour)
        sep_time = last_time + pd.Timedelta(hours=1)
        if sep_time < day_df['time'].iloc[-1]:
            fig_top.add_vline(x=last_time + pd.Timedelta(minutes=30), line_width=12, line_color="white", opacity=1)

    fig_top.update_layout(
        height=125, 
        margin=dict(t=35, b=0, l=5, r=5), 
        template="plotly_white", 
        xaxis=dict(
            showticklabels=False, 
            type='date', 
            showgrid=False,
            # Force dtick to 1 hour to align marks with separation vlines
            dtick=3600000, 
            # Expand slightly to fit standard markers on first/last day
            range=[day_df['time'].min() - pd.Timedelta(minutes=30), day_df['time'].max() + pd.Timedelta(minutes=30)]
        ), 
        yaxis=dict(showticklabels=False, fixedrange=True, range=[0.4, 1.4], showgrid=False), # Center the squares
        bargap=0
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

    # REFINED PEAKS AND VALLEYS 
    for d_date in df['date_only'].unique():
        day_block = df[(df['date_only'] == d_date) & (~df['is_night'])]
        if not day_block.empty:
            peak = day_block.loc[day_block['wind'].idxmax()]
            valley = day_block.loc[day_block['wind'].idxmin()]
            
            fig_bot.add_annotation(x=peak['time'], y=peak['wind'], text=f"<b>{round(peak['wind'])}</b>", 
                                   showarrow=False, yshift=12, font=dict(size=10, color="black"), row=2, col=1)
            if peak['time'] != valley['time']:
                fig_bot.add_annotation(x=valley['time'], y=valley['wind'], text=f"<b>{round(valley['wind'])}</b>", 
                                       showarrow=False, yshift=-12, font=dict(size=10, color="gray"), row=2, col=1)

    for i in range(len(sun_data)):
        midday = datetime.combine(sun_data['date'].iloc[i], time(12, 0))
        fig_bot.add_annotation(x=midday, y=1.02, yref="y1", text=f"<b>{midday.strftime('%a')}</b>", showarrow=False, font=dict(size=9), yanchor="bottom")
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
        yaxis2=dict(showticklabels=True, side="left", tickfont=dict(size=8, color="gray"), showgrid=True, dtick=10, fixedrange=True, layer="below traces"), 
        bargap=0
    )

    # --- RENDER ---
    st.title(f"🌬️ {selection}: {round(df.loc[idx_now, 'wind'])} kn")
    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})
    st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Error loading data")
