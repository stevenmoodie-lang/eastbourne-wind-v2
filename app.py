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
nz_tz = pytz.timezone('Pacific/Auckland')
# Get current time in NZ, then make it naive for comparison with Open-Meteo
now_nz = datetime.now(nz_tz).replace(tzinfo=None)

if data and 'hourly' in data:
    df = pd.DataFrame({
        'time': pd.to_datetime(data['hourly']['time']),
        'wind': data['hourly']['wind_speed_10m']
    })

    if unit == "knots":
        df['wind'] *= 0.539957

    # --- THE FIX IS HERE ---
    daily = data['daily']
    sun_data = pd.DataFrame({
        'date': pd.to_datetime(daily['time']).dt.date, # Added .dt here
        'sunrise': pd.to_datetime(daily['sunrise']),
        'sunset': pd.to_datetime(daily['sunset'])
    })

    # Prepare for Plotting
    plot_df = df.copy()
    
    if hide_night:
        plot_df['date_only'] = plot_df['time'].dt.date
        plot_df = plot_df.merge(sun_data, left_on='date_only', right_on='date')
        plot_df = plot_df[(plot_df['time'] >= plot_df['sunrise']) & (plot_df['time'] <= plot_df['sunset'])]

    # --- PLOTTING ---
    fig = go.Figure()

    # 1. Add Night Shading (Only if night is visible)
    if not hide_night:
        for i in range(len(sun_data)):
            if i < len(sun_data) - 1:
                fig.add_vrect(
                    x0=sun_data['sunset'].iloc[i], 
                    x1=sun_data['sunrise'].iloc[i+1],
                    fillcolor="gray", opacity=0.15, line_width=0
                )

    # 2. Add Vertical Day Dividers (Only if night is hidden)
    else:
        day_starts = plot_df.groupby(plot_df['time'].dt.date).first()['time']
        for start_time in day_starts:
            fig.add_vline(x=start_time, line_width=1, line_dash="solid", line_color="rgba(0,0,0,0.3)")

    # 3. Add Current Time Line
    if not plot_df.empty:
        # Finding the closest timestamp in our data to "Now"
        idx = (plot_df['time'] - now_nz).abs().idxmin()
        closest_time = plot_df.loc[idx, 'time']
        
        fig.add_vline(
            x=closest_time, 
            line_width=2, 
            line_dash="dot", 
            line_color="green",
            annotation_text="NOW", 
            annotation_position="top left"
        )

    # 4. Add Wind Line
    fig.add_trace(go.Scatter(
        x=plot_df['time'], y=plot_df['wind'], name=f'Wind ({unit})',
        line=dict(color='#007BFF', width=3),
        mode='lines+markers' if hide_night else 'lines'
    ))

    # Clean up layout
    fig.update_layout(
        title=f"Wind Forecast: {selection}",
        template="plotly_white",
        hovermode="x unified",
        xaxis=dict(
            type='category' if hide_night else 'date',
            tickformat="%a %I:%M %p",
            nticks=12,
            title=""
        ),
        yaxis=dict(title=unit),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.title(f"🌬️ {selection} Tracker")
    st.plotly_chart(fig, use_container_width=True)

    # Summary Metrics
    m1, m2 = st.columns(2)
    # Using the same index we found for the "Now" line
    current_val = plot_df.loc[idx, 'wind']
    m1.metric("Current Wind (Forecast)", f"{current_val:.1f} {unit}")
    m2.metric("Station", selection)

else:
    st.error("Could not load weather data.")
