import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Eastbourne Wind Tracker", layout="wide")

STATIONS = {
    "Baring Head": {"lat": -41.405, "lon": 174.868},
    "Eastbourne Beach": {"lat": -41.291, "lon": 174.894},
    "Wellington Airport": {"lat": -41.327, "lon": 174.805}
}

def get_weather_data(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
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

st.title("🌬️ Eastbourne Wind Outlook")

selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"])

if data and 'hourly' in data:
    # 1. Prepare Hourly Data
    df = pd.DataFrame({
        'time': pd.to_datetime(data['hourly']['time']),
        'wind': data['hourly']['wind_speed_10m'],
        'gust': data['hourly']['wind_gusts_10m']
    })

    # 2. Add "Gaps" for each day
    # We insert a row with None values at midnight to break the line graph
    days = df['time'].dt.date.unique()
    gap_rows = []
    for day in days:
        # Create a timestamp at the very end of the day to force a break
        gap_time = pd.Timestamp(day).replace(hour=23, minute=59, second=59)
        gap_rows.append({'time': gap_time, 'wind': None, 'gust': None})
    
    df = pd.concat([df, pd.DataFrame(gap_rows)]).sort_values('time')

    # 3. Create the Base Figure
    fig = go.Figure()

    # Add Night Shading using Daily Sunrise/Sunset
    daily = data['daily']
    for i in range(len(daily['time'])):
        # Shade from previous sunset to today's sunrise
        if i > 0:
            prev_sunset = pd.to_datetime(daily['sunset'][i-1])
            curr_sunrise = pd.to_datetime(daily['sunrise'][i])
            fig.add_vrect(x0=prev_sunset, x1=curr_sunrise, 
                          fillcolor="gray", opacity=0.2, line_width=0)
        
        # Shade from today's sunset to end of forecast/midnight
        last_sunset = pd.to_datetime(daily['sunset'][i])
        next_midnight = last_sunset.replace(hour=23, minute=59)
        fig.add_vrect(x0=last_sunset, x1=next_midnight, 
                      fillcolor="gray", opacity=0.2, line_width=0)

    # Add Wind and Gust Lines
    fig.add_trace(go.Scatter(x=df['time'], y=df['wind'], name='Wind Speed',
                             line=dict(color='#007BFF', width=3), connectgaps=False))
    fig.add_trace(go.Scatter(x=df['time'], y=df['gust'], name='Gusts',
                             line=dict(color='#FF4B4B', width=2, dash='dot'), connectgaps=False))

    fig.update_layout(
        title=f"Wind Forecast for {selection} (Grey = Night)",
        xaxis_title="Time",
        yaxis_title="km/h",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)
    
    st.info("💡 The graph breaks at midnight to show each day clearly. Shaded areas represent night time.")
else:
    st.error("Unable to load weather data.")
