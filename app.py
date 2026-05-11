import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time
import pytz

# --- PAGE CONFIG & CSS ---
st.set_page_config(page_title="Wind Tracker", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 0rem; }
        h1 { font-size: 1.5rem !important; margin-bottom: 0px !important; }
        /* Add space between the two plotly charts */
        .stPlotlyChart { margin-bottom: 25px !important; } 
    </style>
""", unsafe_allow_html=True)

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
        "timezone": "Pacific/Auckland", "wind_speed_unit": "kmh", "forecast_days": days
    }
    r = requests.get(url, params=params, timeout=10)
    return r.json() if r.status_code == 200 else None

# --- SIDEBAR ---
selection = st.sidebar.selectbox("Location", list(STATIONS.keys()))
forecast_range = st.sidebar.radio("Range", ["7 Days", "3 Days"], index=0)
days_to_fetch = 7 if forecast_range == "7 Days" else 3

# --- DATA ---
coords = STATIONS[selection]
data = get_weather_data(coords["lat"], coords["lon"], days_to_fetch)
nz_tz = pytz.timezone('Pacific/Auckland')
now_nz = datetime.now(nz_tz).replace(tzinfo=None)

if data and 'hourly' in data:
    df = pd.DataFrame({
        'time': pd.to_datetime(data['hourly']['time']),
        'wind': pd.Series(data['hourly']['wind_speed_10m']) * 0.539957
    })
    df['date_only'] = df['time'].dt.date
    sun_data = pd.DataFrame({
        'date': pd.to_datetime(data['daily']['time']).date, 
        'sunrise': pd.to_datetime(data['daily']['sunrise']),
        'sunset': pd.to_datetime(data['daily']['sunset'])
    })
    df = df.merge(sun_data, left_on='date_only', right_on='date')
    df['is_night'] = (df['time'] < df['sunrise']) | (df['time'] > df['sunset'])

    # --- TOP GRAPH: DAYLIGHT FOCUS ---
    day_df = df[~df['is_night']].copy().reset_index(drop=True)
    day_df['time_str'] = day_df['time'].dt.strftime('%a %H') 

    fig_top = go.Figure()
    fig_top.add_trace(go.Bar(
        x=day_df['time_str'], y=[1] * len(day_df),
        marker_color=[get_color(w) for w in day_df['wind']],
        marker_line_width=0, showlegend=False,
        customdata=day_df['wind'],
        hovertemplate='%{x}:00<br>%{customdata:.1f} kn<extra></extra>'
    ))

    prev_date = None
    for i, row in day_df.iterrows():
        current_date = row['time'].date()
        if prev_date is not None and current_date != prev_date:
            fig_top.add_vline(x=i - 0.5, line_width=8, line_color="white")
        if current_date != prev_date:
            fig_top.add_annotation(
                x=i, y=1.15, text=f"<b>{row['time'].strftime('%a')}</b>",
                showarrow=False, font=dict(size=11), xanchor="left"
            )
        prev_date = current_date

    fig_top.update_layout(
        height=140, margin=dict(t=30, b=20, l=5, r=5),
        template="plotly_white", bargap=0,
        xaxis=dict(type='category', tickangle=0, tickfont=dict(size=7), dtick=4),
        yaxis=dict(showticklabels=False, fixedrange=True, range=[0, 1.4]),
        title=dict(text="<b>Daylight Focus</b>", font=dict(size=11), x=0.01)
    )

    # --- BOTTOM GRAPH: FULL TIMELINE ---
    fig_bot = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.15, 0.85])
    
    for i in range(len(df)):
        fig_bot.add_trace(go.Bar(x=[df['time'][i]], y=[1], marker_color="rgb(240,240,240)" if df['is_night'][i] else get_color(df['wind'][i]), marker_line_width=0, showlegend=False, hoverinfo='none'), row=1, col=1)
    
    for i in range(len(df)-1):
        fig_bot.add_trace(go.Scatter(x=[df['time'][i], df['time'][i+1]], y=[df['wind'][i], df['wind'][i+1]], mode='lines', line=dict(color=get_color(df['wind'][i]), width=2.5), showlegend=False, hoverinfo='none'), row=2, col=1)

    # REPOSITION DAY TEXT CLOSER TO HEATSTRIP
    for i in range(len(sun_data)):
        midday = datetime.combine(sun_data['date'].iloc[i], time(12, 0))
        fig_bot.add_annotation(
            x=midday, y=1.05, yref="y1", # Lowered from 1.3 to 1.05
            text=f"<b>{midday.strftime('%a %d')}</b>",
            showarrow=False, font=dict(size=9),
            yanchor="bottom"
        )

    idx_now = (df['time'] - now_nz).abs().idxmin()
    fig_bot.add_vline(x=df.loc[idx_now, 'time'], line_width=1.5, line_dash="dot", line_color="green")
    
    fig_bot.update_layout(
        height=280, margin=dict(t=15, b=0, l=5, r=5), 
        template="plotly_white", hovermode="x unified",
        yaxis=dict(showticklabels=False, fixedrange=True, range=[0, 1.5], showgrid=False), # Tightened range
        yaxis2=dict(title="kn", fixedrange=True), 
        bargap=0
    )

    # Display 
    st.title(f"🌬️ {selection}: {df.loc[idx_now, 'wind']:.1f} kn")
    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})
    
    # Adding a clear divider for more vertical space
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    
    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Error loading data")
