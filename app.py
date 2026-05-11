import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="NZ Wind Tracker", layout="wide")

# Get API Key from Streamlit Secrets or default to None
API_KEY = st.secrets.get("NIWA_KEY", None)

def get_wind_data(loc_id):
    # Base URL for the Azure-hosted Weather API
    url = f"https://weather-api-azure.niwa.co.nz/api/location/{loc_id}/forecast"
    
    headers = {}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        st.error(f"Connection Failed: {e}")
        return None

st.title("🌬️ NIWA Wind Tracker")

# Sidebar for known working IDs
st.sidebar.title("Stations")
station_choice = st.sidebar.selectbox("Select Station", [
    ("Wellington Airport", "3445"),
    ("Lower Hutt", "12396"),
    ("Baring Head", "113776245"),
    ("Custom", "manual")
])

if station_choice[0] == "Custom":
    loc_id = st.sidebar.text_input("Enter ID", value="3445")
else:
    loc_id = station_choice[1]

if not API_KEY:
    st.warning("⚠️ No API Key found in Streamlit Secrets. Some requests may fail.")

data = get_wind_data(loc_id)

if data and 'values' in data:
    df = pd.DataFrame(data['values'])
    df['time'] = pd.to_datetime(df['time'])
    
    latest = df.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Wind Speed", f"{latest.get('wind', 'N/A')} km/h")
    c2.metric("Gusts", f"{latest.get('wind_gust', 'N/A')} km/h")
    c3.metric("Direction", f"{latest.get('wind_dir_compass', 'N/A')}")
    
    fig = px.line(df, x='time', y=['wind', 'wind_gust'], title=f"Forecast for {loc_id}")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data returned. Check your API Key and Location ID.")
