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
now_nz = datetime.now(nz_tz).replace(tzinfo=None)

if data and 'hourly' in data:
    df = pd.DataFrame({
        'time': pd.to_datetime(data['hourly']['time']),
        'wind': data['hourly']['wind_speed_10m']
    })

    if unit == "knots":
        df['wind'] *= 0.539957

    daily = data['daily']
    sun_times = pd.Series(pd.to_datetime(daily['time']))
    
    sun_data = pd.DataFrame({
        'date': sun_times.dt.date, 
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

    # 1. Add Wind Line
    fig.add_trace(go.Scatter(
        x=plot_df['time'], y=plot_df['wind'], name=f'Wind ({unit})',
        line=dict(color='#007BFF', width=3),
        mode='lines+markers' if hide_night else 'lines'
    ))

    # 2. Add Night Shading (Normal Mode)
    if not hide_night:
        for i in range(len(sun_data)):
            if i < len(sun_data) - 1:
                fig.add_vrect(
                    x0=sun_data['sunset'].iloc[i], 
                    x1=sun_data['sunrise'].iloc[i+1],
                    fillcolor="gray", opacity=0.15, line_width=0
                )

    # 3. Add Day Separators (Hidden Night Mode) - FIXED TO PREVENT CRASH
    else:
        day_starts = plot_df.groupby('date_only')['time'].first().iloc[1:]
        for start_time in day_starts:
            # Draw the Line
            fig.add_shape(
                type="line", x0=start_time, x1=start_time, y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color="black", width=1.5, dash="solid")
            )
            # Draw the Annotation separately
            fig.add_annotation(
                x=start_time, y=0, yref="paper",
                text=" NEW DAY", showarrow=False, xanchor="left", yanchor="bottom",
                font=dict(color="black", size=10)
            )

    # 4. Add Current Time Line ("NOW")
    if not plot_df.empty:
        idx = (plot_df['time'] - now_nz).abs().idxmin()
        closest_time = plot_df.loc[idx, 'time']
        
        fig.add_shape(
            type="line", x0=closest_time, x1=closest_time, y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="green", width=2, dash="dot")
        )
        fig.add_annotation(
            x=closest_time, y=1.05, yref="paper",
            text="NOW", showarrow=False, xanchor="center", font=dict(color="green", size=14)
        )

    fig.update_layout(
        title=f"Wind Forecast: {selection}",
        template="plotly_white",
        hovermode="x unified",
        xaxis=dict(
            type='category' if hide_night else 'date',
            tickformat="%a %I %p",
            nticks=15,
            title=""
        ),
        yaxis=dict(title=unit, rangemode="tozero"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=80)
    )

    st.title(f"🌬️ {selection} Tracker")
    st.plotly_chart(fig, use_container_width=True)

    # Summary Metrics
    curr_idx = (plot_df['time'] - now_nz).abs().idxmin()
    current_val = plot_df.loc[curr_idx, 'wind']
    st.metric("Forecasted Wind Now", f"{current_val:.1f} {unit}")

else:
    st.error("Could not load weather data.")
