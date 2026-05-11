import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time, timedelta
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
        "latitude": lat, "longitude": lon,
        "hourly": "wind_speed_10m",
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

# --- SIDEBAR ---
st.sidebar.title("⚙️ Settings")
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))

# --- DATA PROCESSING ---
coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"])
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

    # --- PLOTTING WITH 3 ROWS ---
    # Row 1: Day Labels (Transparent)
    # Row 2: Heatstrip
    # Row 3: Line Graph
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.01,
        row_heights=[0.1, 0.15, 0.75]
    )

    # 1. ADD HEATSTRIP (ROW 2)
    for i in range(len(df)):
        knots = df.loc[i, 'wind']
        is_night = df.loc[i, 'is_night']
        bar_color = "rgb(220, 220, 220)" if is_night else get_color(knots)
        
        fig.add_trace(go.Bar(
            x=[df.loc[i, 'time']], y=[1],
            marker_color=bar_color, marker_line_width=0,
            showlegend=False, hoverinfo='none'
        ), row=2, col=1)

    # 2. ADD LINE GRAPH (ROW 3)
    for i in range(len(df) - 1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        fig.add_trace(go.Scatter(
            x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']],
            mode='lines', line=dict(color=get_color(p1['wind']), width=4),
            showlegend=False, hoverinfo='none'
        ), row=3, col=1)

    # Invisible hover trace
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['wind'], mode='markers', marker=dict(opacity=0),
        name="Wind", showlegend=False
    ), row=3, col=1)

    # 3. NIGHT SHADING & MOON ICONS
    for i in range(len(sun_data)):
        # Shading for the line graph
        if i < len(sun_data) - 1:
            start_night = sun_data['sunset'].iloc[i]
            end_night = sun_data['sunrise'].iloc[i+1]
            
            fig.add_vrect(
                x0=start_night, x1=end_night,
                fillcolor="gray", opacity=0.1, line_width=0, row=3, col=1
            )
            
            # Place Moon Icon in the middle of the night period in the Heatstrip row
            mid_night = start_night + (end_night - start_night) / 2
            fig.add_annotation(
                x=mid_night, y=0.5, yref="y2", # y2 corresponds to Row 2
                text="🌙", showarrow=False, font=dict(size=16)
            )

    # 4. DAY LABELS (Top Row & Bottom Axis)
    tickvals = [datetime.combine(d, time(12, 0)) for d in sun_data['date']]
    ticktext = [t.strftime("%a %d %b") for t in tickvals]

    # Add text labels to Row 1 (Top)
    for tv, tt in zip(tickvals, ticktext):
        fig.add_annotation(
            x=tv, y=0.5, yref="y1", # y1 corresponds to Row 1
            text=f"<b>{tt}</b>", showarrow=False, font=dict(size=14, color="black")
        )

    # NOW line
    idx_now = (df['time'] - now_nz).abs().idxmin()
    closest_time = df.loc[idx_now, 'time']
    fig.add_vline(x=closest_time, line_width=2, line_dash="dot", line_color="green")

    fig.update_layout(
        height=600,
        template="plotly_white",
        hovermode="x unified",
        xaxis3=dict(tickvals=tickvals, ticktext=ticktext, title=""),
        yaxis1=dict(showticklabels=False, fixedrange=True, showgrid=False, zeroline=False), # Day Headers
        yaxis2=dict(showticklabels=False, fixedrange=True, range=[0, 1], showgrid=False), # Heatstrip
        yaxis3=dict(title="Knots", rangemode="tozero"), # Line Graph
        margin=dict(t=10, b=40, l=10, r=10),
        bargap=0
    )

    st.title(f"🌬️ {selection} Tracker")
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Current Forecasted Wind", f"{df.loc[idx_now, 'wind']:.1f} Knots")

else:
    st.error("Could not load weather data.")
