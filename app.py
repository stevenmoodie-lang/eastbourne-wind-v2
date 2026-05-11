import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Eastbourne Wind Tracker", layout="wide", page_icon="🌬️")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- DATA FETCHING (The "No-Key" Stealth Mode) ---
def get_niwa_data(location_name):
    # This URL is the one used by niwa.co.nz directly
    # Use names like 'Wellington' or 'Baring Head' (case sensitive)
    url = f"https://weather.niwa.co.nz/api/v1/forecast/{location_name}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Public API error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return None

# --- SIDEBAR ---
st.sidebar.title("🌬️ Station Select")
# These are the "Slugs" which are most likely to work with the Azure API
station_map = {
    "Baring Head": "Baring Head",
    "Wellington": "Wellington",
    "Lower Hutt": "Lower Hutt",
    "Wellington Airport": "Wellington Airport"
}
selection = st.sidebar.selectbox("Choose a location:", list(station_map.keys()))
loc_name = station_map[selection]

unit = st.sidebar.radio("Units", ["km/h", "knots"])

# --- MAIN DASHBOARD ---
st.title(f"Wind Outlook: {selection}")

data = get_niwa_wind(loc_id)

if data and 'values' in data:
    df = pd.DataFrame(data['values'])
    df['time'] = pd.to_datetime(df['time'])
    
    # Conversion logic
    if unit == "knots":
        df['wind'] = df['wind'] * 0.539957
        df['wind_gust'] = df['wind_gust'] * 0.539957

    # 1. Metrics Row
    latest = df.iloc[0]
    m1, m2, m3 = st.columns(3)
    
    m1.metric("Wind Speed", f"{latest['wind']:.1f} {unit}")
    m2.metric("Peak Gusts", f"{latest['wind_gust']:.1f} {unit}")
    m3.metric("Direction", f"{latest.get('wind_dir_compass', 'N/A')}")

    st.divider()

    # 2. Plotly Chart
    st.subheader("7-Day Wind Trend")
    fig = px.line(df, x='time', y=['wind', 'wind_gust'],
                  labels={'value': unit, 'time': 'Date/Time'},
                  color_discrete_map={"wind": "#007BFF", "wind_gust": "#FF4B4B"},
                  template="plotly_white")
    
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # 3. Blasting Table
    st.subheader("🚀 Kite/Windsurf Windows")
    threshold = 18 if unit == "knots" else 33
    blasting = df[df['wind'] >= threshold].copy()
    
    if not blasting.empty:
        blasting['time'] = blasting['time'].dt.strftime('%a %I:%M %p')
        st.success(f"Found {len(blasting)} windy sessions!")
        st.dataframe(blasting[['time', 'wind', 'wind_gust', 'wind_dir_compass']], 
                     use_container_width=True, hide_index=True)
    else:
        st.info("No high wind windows in the current forecast.")

else:
    st.error(f"Could not fetch data for '{loc_id}'.")
    st.warning("The NIWA Azure Gateway might be down or requiring an API key. Try 'Wellington City' or check back in a few minutes.")
