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
    """Calculates polygon area using the Shoelace formula (m²)."""
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def get_survey_data(df):
    """Calculates Distance and Bearing (DMS) for the survey table."""
    distances, bearings = [], []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        p2 = (df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N'])
        
        # Distance calculation
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        
        # Bearing calculation (Degrees, Minutes)
        angle = np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360
        deg = int(angle)
        minutes = int((angle - deg) * 60)
        
        distances.append(round(dist, 3))
        bearings.append(f"{deg}° {minutes}'")
    return distances, bearings

def transform_johor_coords(e, n):
    """Transforms Johor Cassini (EPSG:3168) to WGS84 for Google Maps."""
    transformer = Transformer.from_crs("epsg:3168", "epsg:4326")
    lat, lon = transformer.transform(e, n)
    return lat, lon

# --- PAGE STYLING ---
st.set_page_config(page_title="PUO Google GIS | Tamilkumaran", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    .header-box {
        background: #1e293b; 
        padding: 30px; 
        border-radius: 15px;
        border-bottom: 5px solid #38bdf8;
        margin-bottom: 25px;
    }
    .main-title { color: white !important; font-size: 40px; font-weight: bold; margin: 0; }
    .surveyor-tag { color: #38bdf8 !important; font-size: 24px; font-weight: bold; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER SECTION ---
st.markdown(f"""
    <div class="header-box">
        <p class="main-title">POLITEKNIK UNGKU OMAR</p>
        <p class="surveyor-tag">Surveyor: Tamilkumaran</p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
st.sidebar.title("🛠️ INTERACTIVE SETTINGS")
show_labels = st.sidebar.checkbox("📍 Show STN Labels & Coordinates", value=True)
st.sidebar.markdown("---")
st.sidebar.write("**Project:** Lot 11462-11487")
st.sidebar.write("**Location:** Mukim Kesang, Johor")

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("📂 Upload 'point.csv' to begin", type="csv")

if uploaded_file:
    # 1. Load and Sort Data
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    
    # 2. Process Coordinates & Survey Math
    df['lat'], df['lon'] = transform_johor_coords(df['E'].values, df['N'].values)
    dist, bear = get_survey_data(df)
    df['Distance (m)'] = dist
    df['Bearing'] = bear
    area_total = calculate_area(df['E'].values, df['N'].values)

    # 3. Layout: Map and Table
    col_map, col_data = st.columns([2, 1])

    with col_map:
        st.subheader("🗺️ Google Maps Interactive View")
        
        # Initialize Map at center of points
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19, control_scale=True)

        # ADD GOOGLE LAYERS (This creates the on/off toggle button)
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google', name='Google Satellite', overlay=False, control=True
        ).add_to(m)

        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='Google', name='Google Streets', overlay=False, control=True
        ).add_to(m)

        # DRAW THE POLYGON (Lot Boundary)
        poly_coords = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(
            locations=poly_coords, 
            color="#22d3ee", 
            weight=4, 
            fill=True, 
            fill_color="#22d3ee", 
            fill_opacity=0.3,
            name="Survey Boundary"
        ).add_to(m)

        # ADD STATION LABELS (Conditional)
        if show_labels:
            for _, row in df.iterrows():
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    popup=f"STN: {int(row['STN'])}<br>E: {row['E']:.3f}<br>N: {row['N']:.3f}",
                    icon=folium.DivIcon(html=f"""
                        <div style="color:yellow; font-weight:bold; text-shadow:2px 2px black; font-size:12pt; width:100px;">
                            STN {int(row['STN'])}
                        </div>""")
                ).add_to(m)

        # ACTIVATE LAYER CONTROL BUTTON (Top Right)
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        
        folium_static(m, width=850, height=550)

    with col_data:
        st.subheader("📊 Lot Analysis Report")
        st.metric("TOTAL CALCULATED AREA", f"{area_total:.3f} m²")
        
        st.write("### 📏 Bearing & Distance")
        st.dataframe(df[['STN', 'Distance (m)', 'Bearing']], hide_index=True, use_container_width=True)
        
        # Download Button for QGIS
        geojson = {"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[r['lon'],r['lat']] for _,r in df.iterrows()]]}}]}
        st.download_button("📥 Export GeoJSON", json.dumps(geojson), "Tamilkumaran_Survey_Report.geojson", use_container_width=True)

else:
    st.info("👋 Welcome! Please upload your 'point.csv' to generate the Google GIS report.")