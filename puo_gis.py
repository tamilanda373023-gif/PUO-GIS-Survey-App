import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import numpy as np
import json
import os
from pyproj import Transformer

# --- CORE FUNCTIONS ---
def calculate_area(x, y):
    """Calculates polygon area using the Shoelace formula."""
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def get_survey_math(df):
    """Calculates Distance and Bearing (DMS) for professional reporting."""
    distances, bearings = [], []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        p2 = (df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N'])
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        angle = np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360
        distances.append(round(dist, 3))
        # Formatting Bearing to Degrees and Minutes
        bearings.append(f"{int(angle)}° {int((angle%1)*60)}'")
    return distances, bearings

def transform_coords(e, n):
    """Transforms Johor Cassini (EPSG:3168) to WGS84 for Google Maps."""
    transformer = Transformer.from_crs("epsg:3168", "epsg:4326")
    lat, lon = transformer.transform(e, n)
    return lat, lon

# --- SESSION STATE FOR LOGOUT ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = True

if not st.session_state.logged_in:
    st.info("User has successfully logged out.")
    st.stop()

# --- PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- CUSTOM CSS (Cool Dark Theme) ---
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    .header-box {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        padding: 30px; border-radius: 15px;
        border-bottom: 5px solid #38bdf8; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .main-title { color: white !important; font-size: 38px; font-weight: bold; margin: 0; letter-spacing: 1px; }
    .surveyor-tag { color: #38bdf8 !important; font-size: 22px; font-weight: bold; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: INTERACTIVE DISPLAY CONTROLS ---
with st.sidebar:
    if os.path.exists("logo_puo.png"):
        st.image("logo_puo.png", width=220)
    else:
        st.warning("PUO Logo Not Found")
        
    st.title("🎮 Display Controls")
    
    stn_size = st.slider("Station Label Size", 8, 20, 12)
    label_size = st.slider("Bearing/Dist Size", 8, 18, 10)
    marker_size = st.slider("Point Marker Size", 2, 10, 5)
    map_zoom = st.slider("Default Map Zoom", 15, 22, 19)
    
    st.markdown("---")
    if st.button("🚪 Logout User"):
        st.session_state.logged_in = False
        st.rerun()

# --- HEADER ---
st.markdown(f"""
    <div class="header-box">
        <p class="main-title">POLITEKNIK UNGKU OMAR</p>
        <p class="surveyor-tag">Surveyor: Tamilkumaran</p>
    </div>
    """, unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 Upload Survey CSV (point.csv)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    df['lat'], df['lon'] = transform_coords(df['E'].values, df['N'].values)
    dist, bear = get_survey_math(df)
    df['Distance (m)'], df['Bearing'] = dist, bear
    area = calculate_area(df['E'].values, df['N'].values)

    col_map, col_data = st.columns([2.5, 1])

    with col_map:
        st.subheader("🗺️ Interactive Lot Overlay (Google Maps)")
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=map_zoom)

        # GOOGLE MAP LAYERS (Switch Button)
        folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                         attr='Google', name='Google Satellite', overlay=False).add_to(m)
        folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
                         attr='Google', name='Google Streets', overlay=False).add_to(m)

        # LOT POLYGON
        poly_coords = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(locations=poly_coords, color="#22d3ee", weight=3, fill=True, fill_opacity=0.2, name="Lot Boundary").add_to(m)

        # INTERACTIVE LABELS
        for i, row in df.iterrows():
            # Point Marker
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=marker_size, color="#ef4444", fill=True).add_to(m)
            
            # Station Text
            folium.Marker(location=[row['lat'], row['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:yellow; font-weight:bold; text-shadow:2px 2px black; width:100px;">STN {int(row["STN"])}</div>')
            ).add_to(m)
            
            # Dynamic Bearing & Distance Overlay
            next_row = df.iloc[(i+1)%len(df)]
            mid_lat, mid_lon = (row['lat']+next_row['lat'])/2, (row['lon']+next_row['lon'])/2
            folium.Marker(location=[mid_lat, mid_lon],
                icon=folium.DivIcon(html=f'<div style="font-size:{label_size}pt; color:#22d3ee; font-weight:bold; background:rgba(0,0,0,0.6); border-radius:5px; padding:3px; white-space:nowrap; border:1px solid #22d3ee;">{row["Bearing"]} | {row["Distance (m)"]}m</div>')
            ).add_to(m)

        # Layer Control (Top Right Button)
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        folium_static(m, width=950, height=600)

    with col_data:
        st.subheader("📊 Lot Summary")
        st.metric("TOTAL CALCULATED AREA", f"{area:.3f} m²")
        st.write("**Location:** Mukim Kesang, Johor")
        st.write("**Reference:** Lot 11462-11487")
        
        st.write("### 📐 Technical Table")
        st.dataframe(df[['STN', 'Distance (m)', 'Bearing']], hide_index=True, use_container_width=True)
        
        # Professional Export
        geojson = {"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[r['lon'],r['lat']] for _,r in df.iterrows()]]}}]}
        st.download_button("📥 Export GeoJSON", json.dumps(geojson), "Tamilkumaran_Survey_Report.geojson", use_container_width=True)

else:
    st.info("👋 Welcome Tamilkumaran! Please upload your 'point.csv' to generate the professional GIS report.")