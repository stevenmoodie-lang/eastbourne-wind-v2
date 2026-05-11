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
    # We add this first so the x-axis "categories" are defined
    fig.add_trace(go.Scatter(
        x=plot_df['time'], y=plot_df['wind'], name=f'Wind ({unit})',
        line=dict(color='#007BFF', width=3),
        mode='lines+markers' if hide_night else 'lines'
    ))

    # 2. Add Night Shading
    if not hide_night:
        for i in range(len(sun_data)):
            if i < len(sun_data) - 1:
                fig.add_vrect(
                    x0=sun_data['sunset'].iloc[i], 
                    x1=sun_data['sunrise'].iloc[i+1],
                    fillcolor="gray", opacity=0.15, line_width=0
                )

    # 3. Add Vertical Day Dividers
    else:
        day_starts = plot_df.groupby(plot_df['time'].dt.date).first()['time']
        for start_time in day_starts:
            # We use the raw timestamp. Plotly handles vline better with raw data 
            # if we don't force annotations inside the function.
            fig.add_vline(x=start_time, line_width=1, line_dash="solid", line_color="rgba(0,0,0,0.3)")

    # 4. Add Current Time Line (THE FIX FOR THE ERROR)
    if not plot_df.empty:
        idx = (plot_df['time'] - now_nz).abs().idxmin()
        closest_time = plot_df.loc[idx, 'time']
        
        # FIX: We pass the position as a dictionary to avoid the mean() calculation bug
        fig.add_shape(
            type="line",
            x0=closest_time, x1=closest_time, y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="green", width=2, dash="dot")
        )
        # Separate annotation to avoid the error
        fig.add_annotation(
            x=closest_time, y=1, yref="paper",
            text="NOW", showarrow=False, xanchor="left", font=dict(color="green")
        )

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
    curr_idx = (plot_df['time'] - now_nz).abs().idxmin()
    current_val = plot_df.loc[curr_idx, 'wind']
    m1.metric("Forecasted Wind Now", f"{current_val:.1f} {unit}")
    m2.metric("Station", selection)

else:
    st.error("Could not load weather data.")
