import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind Tracker", layout="wide")

STATIONS = {
    "Baring Head": {"lat": -41.405, "lon": 174.868},
    "Eastbourne Beach": {"lat": -41.291, "lon": 174.894},
    "Wellington Airport": {"lat": -41.327, "lon": 174.805}
}

def get_weather_data(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "wind_speed_10m,wind_gusts_10m",
        "daily": "sunrise,sunset",
        "timezone": "Pacific/Auckland",
        "wind_speed_unit": "kmh",
        "forecast_days": 3
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# --- SIDEBAR CONTROLS ---
st.sidebar.title("⚙️ Settings")
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
hide_night = st.sidebar.toggle("Hide Nighttime Hours", value=False)
unit = st.sidebar.radio("Units", ["km/h", "knots"])

# --- DATA PROCESSING ---
coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"])

if data and 'hourly' in data:
    df = pd.DataFrame({
        'time': pd.to_datetime(data['hourly']['time']),
        'wind': data['hourly']['wind_speed_10m'],
        'gust': data['hourly']['wind_gusts_10m']
    })

    if unit == "knots":
        df['wind'] *= 0.539957
        df['gust'] *= 0.539957

    # Get Sunrise/Sunset for shading or filtering
    daily = data['daily']
    sun_data = pd.DataFrame({
        'date': pd.to_datetime(daily['time']).date,
        'sunrise': pd.to_datetime(daily['sunrise']),
        'sunset': pd.to_datetime(daily['sunset'])
    })

    # Filter out night if toggle is ON
    if hide_night:
        # Merge sun data into main df to filter hourly rows
        df['date'] = df['time'].dt.date
        df = df.merge(sun_data, on='date')
        df = df[(df['time'] >= df['sunrise']) & (df['time'] <= df['sunset'])]

    # --- PLOTTING ---
    fig = go.Figure()

    # Add Night Shading (Only if night is visible)
    if not hide_night:
        for i in range(len(sun_data)):
            # Shade from sunset to sunrise next day
            if i < len(sun_data) - 1:
                fig.add_vrect(
                    x0=sun_data['sunset'].iloc[i], 
                    x1=sun_data['sunrise'].iloc[i+1],
                    fillcolor="gray", opacity=0.2, line_width=0
                )

    # Add Wind and Gust Lines
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['wind'], name=f'Wind ({unit})',
        line=dict(color='#007BFF', width=3),
        mode='lines+markers' if hide_night else 'lines'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['gust'], name=f'Gusts ({unit})',
        line=dict(color='#FF4B4B', width=2, dash='dot')
    ))

    # Clean up layout
    fig.update_layout(
        title=f"Wind Forecast: {selection}",
        template="plotly_white",
        hovermode="x unified",
        xaxis=dict(
            # This 'category' type helps prevent big blank gaps when night is hidden
            type='category' if hide_night else 'date',
            tickformat="%a %I:%M %p",
            nticks=10
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.title(f"🌬️ {selection} Tracker")
    st.plotly_chart(fig, use_container_width=True)

    # Summary Metrics
    m1, m2 = st.columns(2)
    latest = df.iloc[0]
    m1.metric("Current Wind", f"{latest['wind']:.1f} {unit}")
    m2.metric("Peak Gust", f"{latest['gust']:.1f} {unit}")

else:
    st.error("Could not load weather data.")
