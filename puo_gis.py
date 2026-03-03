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
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def get_survey_math(df):
    distances, bearings = [], []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        p2 = (df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N'])
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        angle = np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360
        distances.append(round(dist, 3))
        # Bearing as Degrees and Minutes
        bearings.append(f"{int(angle)}° {int((angle%1)*60)}'")
    return distances, bearings

def transform_coords_johor(e, n):
    """
    Revised Transformation: Using Johor Cassini (EPSG:4390) 
    Specifically for Tangkak/Ledang region.
    """
    # EPSG:4390 is the precise transformation for Johor Cassini to WGS84
    transformer = Transformer.from_crs("epsg:4390", "epsg:4326", always_xy=True)
    lon, lat = transformer.transform(e, n)
    return lat, lon

# --- PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    .header-box {
        background: white; padding: 15px; border-radius: 10px;
        border-bottom: 5px solid #38bdf8; margin-bottom: 20px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .main-title { color: #0b172a !important; font-size: 32px; font-weight: bold; margin: 0; }
    .surveyor-tag { color: #38bdf8 !important; font-size: 20px; font-weight: bold; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (Controls appear only after login) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = True

if not st.session_state.logged_in:
    st.info("You have logged out.")
    st.stop()

# --- HEADER WITH LOGO ---
header_col1, header_col2 = st.columns([1, 4])
with st.container():
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    col_l, col_r = st.columns([1, 3])
    with col_l:
        if os.path.exists("logo_puo.png"):
            st.image("logo_puo.png", width=150)
        else:
            st.write("PUO LOGO")
    with col_r:
        st.markdown('<p class="main-title">POLITEKNIK UNGKU OMAR</p>', unsafe_allow_html=True)
        st.markdown('<p class="surveyor-tag">Surveyor: Tamilkumaran</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("📂 Insert 'point.csv' to Activate Google Map Overlay", type="csv")

if uploaded_file:
    # 1. SIDEBAR INTERACTIVE CONTROLS
    with st.sidebar:
        st.header("⚙️ Display Controls")
        stn_size = st.slider("Station ID Size", 8, 20, 11)
        label_size = st.slider("Bearing/Jarak Size", 6, 16, 9)
        marker_radius = st.slider("Marker Point Size", 2, 10, 4)
        map_zoom = st.slider("Google Zoom Level", 16, 22, 19)
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # 2. DATA PROCESSING
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    df['lat'], df['lon'] = transform_coords_johor(df['E'].values, df['N'].values)
    dist, bear = get_survey_math(df)
    df['Distance'], df['Bearing'] = dist, bear
    area = calculate_area(df['E'].values, df['N'].values)

    # 3. INTERACTIVE GOOGLE MAP
    col_map, col_table = st.columns([2.5, 1])
    
    with col_map:
        st.subheader("🛰️ Google Maps Satellite Interactive")
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=map_zoom)

        # GOOGLE LAYERS
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite', name='Google Satellite', overlay=False
        ).add_to(m)
        
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='Google Hybrid', name='Google Hybrid (Streets + Satellite)', overlay=False
        ).add_to(m)

        # POLYGON
        poly_points = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(
            locations=poly_points, color="yellow", weight=3, 
            fill=True, fill_opacity=0.2, name="Lot Boundary"
        ).add_to(m)

        # STN & DIMENSION LABELS
        for i, row in df.iterrows():
            # Point Marker
            folium.CircleMarker([row['lat'], row['lon']], radius=marker_radius, color="red", fill=True).add_to(m)
            # STN Number
            folium.Marker([row['lat'], row['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:white; font-weight:bold; text-shadow:1px 1px black;">{int(row["STN"])}</div>')
            ).add_to(m)
            # Mid-point Labeling for Bearing/Jarak
            next_p = df.iloc[(i+1)%len(df)]
            m_lat, m_lon = (row['lat']+next_p['lat'])/2, (row['lon']+next_p['lon'])/2
            folium.Marker([m_lat, m_lon],
                icon=folium.DivIcon(html=f'<div style="font-size:{label_size}pt; color:#38bdf8; font-weight:bold; background:rgba(0,0,0,0.6); padding:2px; white-space:nowrap; border-radius:3px;">{row["Bearing"]} | {row["Distance"]}m</div>')
            ).add_to(m)

        # LAYER TOGGLE BUTTON
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        folium_static(m, width=950, height=600)

    with col_table:
        st.subheader("📊 Lot Summary")
        st.metric("Total Area", f"{area:.3f} m²")
        st.dataframe(df[['STN', 'Distance', 'Bearing']], hide_index=True)
        st.download_button("📥 Export GeoJSON", json.dumps({"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[r['lon'],r['lat']] for _,r in df.iterrows()]]}}]}), "Tamilkumaran_GIS.geojson")