import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import numpy as np
import json
import os
from pyproj import Transformer

# --- CORE CALCULATIONS ---
def calculate_area(x, y):
    """Calculates polygon area using the Shoelace formula."""
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def get_survey_math(df):
    """Calculates Distance and Bearing (DMS) for lines."""
    distances, bearings = [], []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        p2 = (df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N'])
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        angle = np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360
        distances.append(round(dist, 3))
        # Format: Degrees and Minutes
        bearings.append(f"{int(angle)}° {int((angle%1)*60)}'")
    return distances, bearings

def transform_coords_johor(e, n):
    """Refined Johor Cassini transformation to ensure correct overlay."""
    # EPSG:4390 ensures the lot lands in Tangkak/Kesang, Johor
    transformer = Transformer.from_crs("epsg:4390", "epsg:4326", always_xy=True)
    lon, lat = transformer.transform(e, n)
    return lat, lon

# --- SESSION & LOGOUT ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = True
if not st.session_state.logged_in:
    st.info("You have successfully logged out.")
    st.stop()

# --- PAGE SETUP ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- CUSTOM CSS (COOL DARK THEME) ---
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    .header-box {
        background: #ffffff; padding: 20px; border-radius: 12px;
        border-bottom: 6px solid #38bdf8; margin-bottom: 25px;
        display: flex; align-items: center; box-shadow: 0 10px 20px rgba(0,0,0,0.3);
    }
    .main-title { color: #1e293b !important; font-size: 36px; font-weight: 800; margin: 0; }
    .surveyor-tag { color: #38bdf8 !important; font-size: 22px; font-weight: 600; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER WITH LOGO ---
st.markdown('<div class="header-box">', unsafe_allow_html=True)
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo_puo.png"):
        st.image("logo_puo.png", width=180)
    else:
        st.write("### PUO")
with col_title:
    st.markdown('<p class="main-title">POLITEKNIK UNGKU OMAR</p>', unsafe_allow_html=True)
    st.markdown('<p class="surveyor-tag">Surveyor: Tamilkumaran</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("📂 Upload 'point.csv' to unlock interactive map", type="csv")

if uploaded_file:
    # 1. PROCESS DATA
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    df['lat'], df['lon'] = transform_coords_johor(df['E'].values, df['N'].values)
    dist, bear = get_survey_math(df)
    df['Distance (m)'], df['Bearing'] = dist, bear
    area_m2 = calculate_area(df['E'].values, df['N'].values)

    # 2. INTERACTIVE SIDEBAR CONTROLS
    with st.sidebar:
        st.header("🎮 Display Settings")
        stn_size = st.slider("Station ID Text Size", 8, 20, 12)
        label_size = st.slider("Bearing & Distance Text Size", 6, 16, 9)
        marker_rad = st.slider("Marker Point Size", 2, 12, 4)
        map_zoom = st.slider("Initial Zoom Level", 18, 22, 21)
        st.markdown("---")
        if st.button("🚪 Logout User"):
            st.session_state.logged_in = False
            st.rerun()

    # 3. DASHBOARD LAYOUT
    col_map, col_data = st.columns([2.5, 1])

    with col_map:
        st.subheader("🗺️ High-Resolution Google Satellite Overlay")
        
        # Initialize map with MAX ZOOM support (level 22)
        m = folium.Map(
            location=[df['lat'].mean(), df['lon'].mean()], 
            zoom_start=map_zoom, 
            max_zoom=22,
            control_scale=True
        )

        # GOOGLE LAYERS (WITH MAX ZOOM ENABLED)
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite', name='Google Satellite', overlay=False,
            max_zoom=22, max_native_zoom=20
        ).add_to(m)

        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='Google Hybrid', name='Google Hybrid', overlay=False,
            max_zoom=22, max_native_zoom=20
        ).add_to(m)

        # POLYGON OVERLAY
        poly_points = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(
            locations=poly_points, color="#FFFF00", weight=3, 
            fill=True, fill_opacity=0.2, name="Survey Lot"
        ).add_to(m)

        # STATION & LINE LABELS
        for i, row in df.iterrows():
            # Corner Point
            folium.CircleMarker([row['lat'], row['lon']], radius=marker_rad, color="#ef4444", fill=True).add_to(m)
            
            # STN Text
            folium.Marker([row['lat'], row['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:white; font-weight:bold; text-shadow:2px 2px black;">{int(row["STN"])}</div>')
            ).add_to(m)
            
            # Line Text (Bearing/Distance at mid-point)
            next_p = df.iloc[(i+1)%len(df)]
            m_lat, m_lon = (row['lat']+next_p['lat'])/2, (row['lon']+next_p['lon'])/2
            folium.Marker([m_lat, m_lon],
                icon=folium.DivIcon(html=f'<div style="font-size:{label_size}pt; color:#22d3ee; font-weight:bold; background:rgba(0,0,0,0.6); padding:2px; border-radius:3px; white-space:nowrap;">{row["Bearing"]} | {row["Distance (m)"]}m</div>')
            ).add_to(m)

        # LAYER CONTROL BOX
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        folium_static(m, width=950, height=600)

    with col_data:
        st.subheader("📊 Survey Analysis")
        st.metric("TOTAL CALCULATED AREA", f"{area_m2:.3f} m²")
        st.write("**Location:** Mukim Kesang, Johor")
        st.write("**Reference:** Lot 11462-11487")
        st.dataframe(df[['STN', 'Distance (m)', 'Bearing']], hide_index=True, use_container_width=True)
        
        # EXPORT DATA
        geojson = {"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[r['lon'],r['lat']] for _,r in df.iterrows()]]}}]}
        st.download_button("📥 Export GeoJSON for QGIS", json.dumps(geojson), "Tamilkumaran_Survey.geojson", use_container_width=True)

else:
    st.info("👋 Hello Tamilkumaran! Please upload your 'point.csv' file to activate the high-zoom satellite map.")