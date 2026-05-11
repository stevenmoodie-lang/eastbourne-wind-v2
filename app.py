import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time
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

    daily = data['daily']
    sun_data = pd.DataFrame({
        'date': pd.Series(pd.to_datetime(daily['time'])).dt.date, 
        'sunrise': pd.to_datetime(daily['sunrise']),
        'sunset': pd.to_datetime(daily['sunset'])
    })

    # --- PLOTTING WITH SUBPLOTS ---
    # Row 1 is the thick color bar (15% height), Row 2 is the line graph (85% height)
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03,
        row_heights=[0.15, 0.85]
    )

    # 1. ADD COLOR BAR (TOP)
    for i in range(len(df)):
        knots = df.loc[i, 'wind']
        fig.add_trace(go.Bar(
            x=[df.loc[i, 'time']],
            y=[1], # Constant height to make it a solid block
            marker_color=get_color(knots),
            marker_line_width=0,
            showlegend=False,
            hoverinfo='none'
        ), row=1, col=1)

    # 2. ADD LINE SEGMENTS (BOTTOM)
    for i in range(len(df) - 1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        fig.add_trace(go.Scatter(
            x=[p1['time'], p2['time']],
            y=[p1['wind'], p2['wind']],
            mode='lines',
            line=dict(color=get_color(p1['wind']), width=4),
            showlegend=False,
            hoverinfo='none'
        ), row=2, col=1)

    # Invisible hover trace
    fig.add_trace(go.Scatter(
        x=df['time'], y=df['wind'],
        mode='markers', marker=dict(opacity=0),
        name="Wind", showlegend=False
    ), row=2, col=1)

    # Night Shading
    for i in range(len(sun_data)):
        if i < len(sun_data) - 1:
            fig.add_vrect(
                x0=sun_data['sunset'].iloc[i], x1=sun_data['sunrise'].iloc[i+1],
                fillcolor="gray", opacity=0.1, line_width=0
            )

    # NOW line
    idx_now = (df['time'] - now_nz).abs().idxmin()
    closest_time = df.loc[idx_now, 'time']
    fig.add_vline(x=closest_time, line_width=2, line_dash="dot", line_color="green")

    # X-Axis Day Labels (at Midday)
    tickvals = [datetime.combine(d, time(12, 0)) for d in sun_data['date']]
    ticktext = [t.strftime("%a %d %b") for t in tickvals]

    fig.update_layout(
        height=500,
        template="plotly_white",
        hovermode="x unified",
        xaxis2=dict(
            tickvals=tickvals,
            ticktext=ticktext,
            title=""
        ),
        yaxis=dict(showticklabels=False, fixedrange=True, range=[0, 1]), # Bar chart Y-axis
        yaxis2=dict(title="Knots", rangemode="tozero"), # Line chart Y-axis
        margin=dict(t=20, b=40, l=10, r=10),
        bargap=0 # Makes the top bar look like one solid thick line
    )

    st.title(f"🌬️ {selection} Tracker")
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Current Forecasted Wind", f"{df.loc[idx_now, 'wind']:.1f} Knots")

else:
    st.error("Could not load weather data.")
