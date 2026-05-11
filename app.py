import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="NZ Wind Tracker", layout="wide", page_icon="🌬️")

# Custom CSS for better look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# --- API FUNCTIONS ---
BASE_URL = "https://weather-api-azure.niwa.co.nz/api"

@st.cache_data(ttl=3600)
def fetch_locations():
    """Fetch the list of all available locations to find IDs."""
    try:
        response = requests.get(f"{BASE_URL}/location", timeout=10)
        return response.json()
    except:
        return []

def get_wind_data(loc_id):
    """Try Combined endpoint first, fall back to Forecast."""
    endpoints = ["combined", "forecast"]
    for ep in endpoints:
        url = f"{BASE_URL}/location/{loc_id}/{ep}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if 'values' in data and len(data['values']) > 0:
                    return data, ep
        except:
            continue
    return None, None

# --- SIDEBAR: STATION DISCOVERY ---
st.sidebar.title("📍 Station Finder")
all_locs = fetch_locations()

if all_locs:
    search_query = st.sidebar.text_input("Search for a place (e.g. Baring or Hutt)", "")
    if search_query:
        matches = [l for l in all_locs if search_query.lower() in l['name'].lower()]
        if matches:
            st.sidebar.write("Found stations:")
            for m in matches[:5]: # Show top 5
                if st.sidebar.button(f"Select {m['name']} (ID: {m['id']})"):
                    st.session_state.loc_id = str(m['id'])
        else:
            st.sidebar.warning("No matches found.")

# Default ID (Wellington Airport is 3445 or 17600 usually)
if 'loc_id' not in st.session_state:
    st.session_state.loc_id = "113776245" # Your Baring Head ID

final_loc = st.sidebar.text_input("Active Location ID", value=st.session_state.loc_id)

# --- MAIN UI ---
st.title("🌬️ NIWA Wind Tracker")
st.info(f"Currently viewing Station ID: **{final_loc}**")

data, source_type = get_wind_data(final_loc)

if data:
    df = pd.DataFrame(data['values'])
    df['time'] = pd.to_datetime(df['time'])
    
    # Header Metrics
    latest = df.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    
    # Function to safe-get values
    def val(k): return latest.get(k, "N/A")

    c1.metric("Wind Speed", f"{val('wind')} km/h")
    c2.metric("Gusts", f"{val('wind_gust')} km/h")
    c3.metric("Direction", f"{val('wind_dir_compass')}")
    c4.metric("Data Source", source_type.title())

    st.divider()

    # Charting
    st.subheader("Wind Forecast Trend")
    fig = px.line(df, x='time', y=['wind', 'wind_gust'], 
                  labels={'value': 'km/h', 'time': 'Time'},
                  color_discrete_map={"wind": "#007BFF", "wind_gust": "#FF4B4B"})
    
    fig.update_layout(hovermode="x unified", legend_title="Type")
    st.plotly_chart(fig, use_container_width=True)

    # Blasting Table
    st.subheader("🚀 High Wind Windows")
    high_wind = df[df['wind'] >= 25].copy()
    if not high_wind.empty:
        high_wind['time'] = high_wind['time'].dt.strftime('%a %H:%M')
        st.dataframe(high_wind[['time', 'wind', 'wind_gust', 'wind_dir_compass']], use_container_width=True)
    else:
        st.write("No 'blasting' winds (25+ km/h) expected soon.")

else:
    st.error(f"Could not find data for ID: {final_loc}")
    st.write("Suggestions:")
    st.write("1. Use the **Station Finder** in the sidebar.")
    st.write("2. Try the ID for Wellington Airport: `3445`.")
