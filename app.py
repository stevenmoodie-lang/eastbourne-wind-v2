import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
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

    # --- PLOTTING (SINGLE AXIS MODE) ---
    fig = go.Figure()

    # 1. THE HEATSTRIP (Now at the bottom of the graph)
    # We use very tall bars that go from y=-2 to y=0
    for i in range(len(df)):
        is_night = (df.loc[i, 'time'] < df.loc[i, 'sunrise']) or (df.loc[i, 'time'] > df.loc[i, 'sunset'])
        color = "rgb(230, 230, 230)" if is_night else get_color(df.loc[i, 'wind'])
        
        fig.add_trace(go.Bar(
            x=[df.loc[i, 'time']], y=[2.5], # Height of the color bar
            base=-2.5, # Starts below zero
            marker_color=color, marker_line_width=0,
            showlegend=False, hoverinfo='none'
        ))

    # 2. WIND LINE (The main event)
    # Drawing segments for the color line
    for i in range(len(df) - 1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        fig.add_trace(go.Scatter(
            x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']],
            mode='lines', line=dict(color=get_color(p1['wind']), width=3),
            showlegend=False, hoverinfo='none'
        ))

    # Transparent markers for unified hover
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['wind'], mode='markers',
        marker=dict(opacity=0), name="Wind", showlegend=False
    ))

    # 3. NIGHT SHADING & ICONS
    y_max = df['wind'].max() * 1.1
    for i in range(len(sun_data)):
        midday = datetime.combine(sun_data['date'].iloc[i], time(12, 0))
        
        # Day Labels floating at the top
        fig.add_annotation(
            x=midday, y=y_max, text=f"<b>{midday.strftime('%a %d')}</b>",
            showarrow=False, font=dict(size=10), yanchor="top"
        )
        
        if i < len(sun_data) - 1:
            sunset = sun_data['sunset'].iloc[i]
            sunrise_next = sun_data['sunrise'].iloc[i+1]
            
            # Night Shading
            fig.add_vrect(x0=sunset, x1=sunrise_next, fillcolor="gray", opacity=0.1, line_width=0)
            
            # Moon Icon floating in the night area
            fig.add_annotation(
                x=sunset + (sunrise_next - sunset)/2, y=-1.25,
                text="🌙", showarrow=False, font=dict(size=12)
            )

    # NOW line
    idx_now = (df['time'] - now_nz).abs().idxmin()
    fig.add_vline(x=df.loc[idx_now, 'time'], line_width=2, line_dash="dot", line_color="green")

    # --- LAYOUT OPTIMIZATION ---
    fig.update_layout(
        height=400, # Shorter height is better for mobile scrolling
        margin=dict(l=10, r=10, t=30, b=20),
        template="plotly_white",
        hovermode="x unified",
        bargap=0,
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(
            title="Knots",
            range=[-2.5, y_max], # Room at the bottom for the heatstrip
            fixedrange=True      # Prevents accidental zooming on mobile
        ),
        legend=dict(orientation="h")
    )

    st.subheader(f"🌬️ {selection} ({forecast_range})")
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Big Metric for mobile quick-view
    st.metric("Current Wind", f"{df.loc[idx_now, 'wind']:.1f} Knots")

else:
    st.error("Could not load weather data.")
