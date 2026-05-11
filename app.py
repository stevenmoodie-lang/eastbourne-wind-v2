import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time
import pytz

# --- PAGE CONFIG ---
st.set_page_config(page_title="Wind Tracker", layout="wide")

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
        "timezone": "Pacific/Auckland",
        "wind_speed_unit": "kmh",
        "forecast_days": days
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# --- SIDEBAR ---
st.sidebar.title("⚙️ Settings")
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
forecast_range = st.sidebar.radio("Forecast Range", ["7 Days", "3 Days"], index=0)
days_to_fetch = 7 if forecast_range == "7 Days" else 3

# --- DATA PROCESSING ---
coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"], days_to_fetch)
nz_tz = pytz.timezone('Pacific/Auckland')
now_nz = datetime.now(nz_tz).replace(tzinfo=None)

if data and 'hourly' in data:
    df = pd.DataFrame({
        'time': pd.Series(pd.to_datetime(data['hourly']['time'])),
        'wind_kmh': data['hourly']['wind_speed_10m']
    })
    df['wind'] = df['wind_kmh'] * 0.539957
    df['date_only'] = df['time'].dt.date

    daily = data['daily']
    sun_data = pd.DataFrame({
        'date': pd.Series(pd.to_datetime(daily['time'])).dt.date, 
        'sunrise': pd.to_datetime(daily['sunrise']),
        'sunset': pd.to_datetime(daily['sunset'])
    })

    df = df.merge(sun_data, left_on='date_only', right_on='date')
    df['is_night'] = (df['time'] < df['sunrise']) | (df['time'] > df['sunset'])

    # --- PLOTTING ---
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.04,
        row_heights=[0.2, 0.8] # Slimmed the top row further
    )

    # 1. HEATSTRIP (Row 1)
    for i in range(len(df)):
        knots = df.loc[i, 'wind']
        is_night = df.loc[i, 'is_night']
        bar_color = "rgb(230, 230, 230)" if is_night else get_color(knots)
        
        fig.add_trace(go.Bar(
            x=[df.loc[i, 'time']], y=[1],
            marker_color=bar_color, marker_line_width=0,
            showlegend=False, hoverinfo='none'
        ), row=1, col=1)

    # 2. LINE GRAPH (Row 2)
    for i in range(len(df) - 1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        fig.add_trace(go.Scatter(
            x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']],
            mode='lines', line=dict(color=get_color(p1['wind']), width=3),
            showlegend=False, hoverinfo='none'
        ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=df['time'], y=df['wind'], mode='markers', marker=dict(opacity=0),
        name="Wind", showlegend=False
    ), row=2, col=1)

    # 3. ANNOTATIONS & SHADING
    for i in range(len(sun_data)):
        midday = datetime.combine(sun_data['date'].iloc[i], time(12, 0))
        label_size = 9 if days_to_fetch == 7 else 11
        
        fig.add_annotation(
            x=midday, y=1.4, yref="y1",
            text=f"<b>{midday.strftime('%a %d')}</b>",
            showarrow=False, font=dict(size=label_size)
        )
        
        if i < len(sun_data) - 1:
            sunset = sun_data['sunset'].iloc[i]
            sunrise_next = sun_data['sunrise'].iloc[i+1]
            mid_night = sunset + (sunrise_next - sunset) / 2
            
            fig.add_annotation(
                x=mid_night, y=0.5, yref="y1",
                text="🌙", showarrow=False, font=dict(size=12)
            )
            
            fig.add_vrect(
                x0=sunset, x1=sunrise_next,
                fillcolor="gray", opacity=0.08, line_width=0, row=2, col=1
            )

    # NOW line
    idx_now = (df['time'] - now_nz).abs().idxmin()
    closest_time = df.loc[idx_now, 'time']
    fig.add_vline(x=closest_time, line_width=2, line_dash="dot", line_color="green")

    fig.update_layout(
        height=380, # Ultra-compact height
        template="plotly_white",
        hovermode="x unified",
        xaxis2=dict(showticklabels=True, title=""),
        yaxis=dict(showticklabels=False, fixedrange=True, range=[0, 1.8], showgrid=False),
        yaxis2=dict(title="kn", rangemode="tozero", fixedrange=True),
        margin=dict(t=30, b=10, l=10, r=10), # Tight margins
        bargap=0
    )

    st.subheader(f"🌬️ {selection}")
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Using columns for the metric to save even more vertical space
    c1, c2 = st.columns([1, 1])
    c1.metric("Now", f"{df.loc[idx_now, 'wind']:.1f} kn")

else:
    st.error("Could not load weather data.")
