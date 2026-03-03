import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from folium.plugins import LayerControl
import numpy as np
import json
import os
from pyproj import Transformer

# --- CORE FUNCTIONS ---
def calculate_area(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def get_survey_data(df):
    """Calculates Distance and Bearing between stations."""
    distances = []
    bearings = []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        p2 = (df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N'])
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        angle = np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360
        distances.append(round(dist, 3))
        bearings.append(f"{int(angle)}° {int((angle%1)*60)}'")
    return distances, bearings

def transform_johor_coords(e, n):
    # Using Johor Cassini Projection from PA 143912 [cite: 2, 34]
    transformer = Transformer.from_crs("epsg:3168", "epsg:4326")
    lat, lon = transformer.transform(e, n)
    return lat, lon

# --- PAGE STYLE ---
st.set_page_config(page_title="PUO Google GIS", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    .header-box {
        background: #1e293b; padding: 25px; border-radius: 15px;
        border-bottom: 5px solid #38bdf8; margin-bottom: 20px;
    }
    .main-title { color: white; font-size: 38px; font-weight: bold; margin: 0; }
    .surveyor-tag { color: #38bdf8; font-size: 22px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
    <div class="header-box">
        <p class="main-title">POLITEKNIK UNGKU OMAR</p>
        <p class="surveyor-tag">Surveyor: Tamilkumaran</p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🛠️ LAYER OPTIONS")
show_labels = st.sidebar.checkbox("📍 Show Coordinates & STN Labels", value=True)
st.sidebar.markdown("---")
st.sidebar.write("**Location:** Mukim Kesang, Johor [cite: 5, 2]")
st.sidebar.write("**Lot:** 11462-11487 [cite: 6]")

uploaded_file = st.file_uploader("📂 Upload 'point.csv'", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    df['lat'], df['lon'] = transform_johor_coords(df['E'].values, df['N'].values)
    
    # Calculate Survey Metrics
    dist, bear = get_survey_data(df)
    df['Distance (m)'] = dist
    df['Bearing'] = bear
    area_m2 = calculate_area(df['E'].values, df['N'].values)

    col_map, col_data = st.columns([2, 1])

    with col_map:
        st.subheader("🗺️ Google Maps Interactive Layers")
        
        # Center on Johor Survey Site [cite: 135]
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19)

        # --- EXACT GOOGLE MAP LAYERS ---
        google_satellite = folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite', name='Google Satellite', overlay=False
        ).add_to(m)

        google_terrain = folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
            attr='Google Terrain', name='Google Terrain', overlay=False
        ).add_to(m)

        google_streets = folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='Google Streets', name='Google Streets', overlay=False
        ).add_to(m)

        # Draw Polygon [cite: 1]
        poly_coords = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(
            locations=poly_coords, color="yellow", weight=3, 
            fill=True, fill_color="cyan", fill_opacity=0.3
        ).add_to(m)

        # Labels & Coordinates (Conditional)
        if show_labels:
            for _, row in df.iterrows():
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    popup=f"STN: {int(row['STN'])}<br>E: {row['E']}<br>N: {row['N']}",
                    icon=folium.DivIcon(html=f'<div style="color:white; font-weight:bold; text-shadow:1px 1px black;">STN {int(row["STN"])}</div>')
                ).add_to(m)

        # Add the Layer Control (The button you want)
        folium.LayerControl().add_to(m)
        
        folium_static(m, width=850, height=550)

    with col_data:
        st.subheader("📊 Lot Analysis")
        st.metric("Total Area", f"{area_m2:.3f} m²")
        st.dataframe(df[['STN', 'Distance (m)', 'Bearing']], hide_index=True)
        
        # QGIS Export [cite: 1]
        geojson = {"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[r['lon'],r['lat']] for _,r in df.iterrows()]]}}]}
        st.download_button("📥 Export GeoJSON", json.dumps(geojson), "Tamilkumaran_Johor.geojson")

else:
    st.info("Upload 'point.csv' to activate Google Maps Layers.")