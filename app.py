import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pytz

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind Tracker", layout="wide")

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

def get_weather_data(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m",
        "daily": "sunrise,sunset",
        "timezone": "Pacific/Auckland",
        "wind_speed_unit": "kmh", # Using kmh for stability, converting later
        "forecast_days": 3
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.warning(f"API Error: Status {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# --- SIDEBAR ---
st.sidebar.title("⚙️ Settings")
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
hide_night = st.sidebar.toggle("Hide Nighttime Hours", value=False)

# --- DATA PROCESSING ---
coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"])
nz_tz = pytz.timezone('Pacific/Auckland')
now_nz = datetime.now(nz_tz).replace(tzinfo=None)

if data and 'hourly' in data:
    # 1. Prepare Hourly Data
    df = pd.DataFrame({
        'time': pd.Series(pd.to_datetime(data['hourly']['time'])),
        'wind_kmh': data['hourly']['wind_speed_10m']
    })
    # Convert km/h to knots
    df['wind'] = df['wind_kmh'] * 0.539957

    # 2. Prepare Sun Data
    daily = data['daily']
    sun_data = pd.DataFrame({
        'date': pd.Series(pd.to_datetime(daily['time'])).dt.date, 
        'sunrise': pd.to_datetime(daily['sunrise']),
        'sunset': pd.to_datetime(daily['sunset'])
    })

    # 3. Filter Logic
    plot_df = df.copy()
    if hide_night:
        plot_df['date_only'] = plot_df['time'].dt.date
        plot_df = plot_df.merge(sun_data, left_on='date_only', right_on='date')
        plot_df = plot_df[(plot_df['time'] >= plot_df['sunrise']) & (plot_df['time'] <= plot_df['sunset'])]
    
    plot_df = plot_df.reset_index(drop=True)

    # --- PLOTTING ---
    fig = go.Figure()

    # Draw Segments for Colors
    for i in range(len(plot_df) - 1):
        p1, p2 = plot_df.iloc[i], plot_df.iloc[i+1]
        fig.add_trace(go.Scatter(
            x=[p1['time'], p2['time']],
            y=[p1['wind'], p2['wind']],
            mode='lines',
            line=dict(color=get_color(p1['wind']), width=4),
            showlegend=False,
            hoverinfo='none'
        ))

    # Invisible layer for hover data
    fig.add_trace(go.Scatter(
        x=plot_df['time'], y=plot_df['wind'],
        mode='markers', marker=dict(opacity=0),
        name="Wind (Knots)", showlegend=True
    ))

    # Night Shading
    if not hide_night:
        for i in range(len(sun_data)):
            if i < len(sun_data) - 1:
                fig.add_vrect(
                    x0=sun_data['sunset'].iloc[i], x1=sun_data['sunrise'].iloc[i+1],
                    fillcolor="gray", opacity=0.15, line_width=0
                )

    # NOW line
    if not plot_df.empty:
        idx_now = (plot_df['time'] - now_nz).abs().idxmin()
        closest_time = plot_df.loc[idx_now, 'time']
        fig.add_vline(x=closest_time, line_width=2, line_dash="dot", line_color="green")
        fig.add_annotation(x=closest_time, y=1.05, yref="paper", text="NOW", font=dict(color="green"))

    fig.update_layout(
        title=f"Wind Forecast: {selection}",
        template="plotly_white",
        hovermode="x unified",
        xaxis=dict(type='category' if hide_night else 'date', title=""),
        yaxis=dict(title="Knots", rangemode="tozero")
    )

    st.title(f"🌬️ {selection} Tracker")
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Current Forecasted Wind", f"{plot_df.loc[idx_now, 'wind']:.1f} Knots")

else:
    st.error("Could not load weather data. The API might be temporarily down or rate-limited.")
