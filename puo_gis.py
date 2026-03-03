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

def transform_johor_coords(e, n):
    """Transforms Johor Cassini (EPSG:3168) to WGS84."""
    transformer = Transformer.from_crs("epsg:3168", "epsg:4326")
    lat, lon = transformer.transform(e, n)
    return lat, lon

# --- PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS | Tamilkumaran", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS (The "Cool" Factor) ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    .header-box {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        padding: 35px;
        border-radius: 15px;
        border-left: 10px solid #38bdf8;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
        margin-bottom: 25px;
    }
    .main-title { color: #ffffff; font-size: 42px; font-weight: 800; margin: 0; text-transform: uppercase; letter-spacing: 2px; }
    .surveyor-tag { color: #38bdf8; font-size: 24px; font-weight: 600; margin-top: 5px; text-shadow: 0 0 10px rgba(56, 189, 248, 0.5); }
    .metric-card { background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: INTERACTIVE CONTROLS ---
with st.sidebar:
    st.header("🛠️ Map Controls")
    map_type = st.radio("Select Base Map", ["Modern Street Map", "Satellite Imagery"])
    st.divider()
    st.header("🏷️ Overlays")
    show_labels = st.checkbox("Show Station IDs", value=True)
    show_area_box = st.checkbox("Show Professional Info Box", value=True)
    st.info("Location: Mukim Kesang, Johor ")

# --- TASK 1: THE COOL HEADER ---
st.markdown(f"""
    <div class="header-box">
        <p class="main-title">Politeknik Ungku Omar</p>
        <p class="surveyor-tag">Surveyor: Tamilkumaran</p>
    </div>
    """, unsafe_allow_html=True)

# --- DATA INPUT ---
uploaded_file = st.file_uploader("📂 Drop your 'point.csv' here", type="csv")

if uploaded_file:
    # Read the provided survey data [cite: 1]
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    
    # Run Calculations & Transformations 
    e_vals, n_vals = df['E'].values, df['N'].values
    area_m2 = calculate_area(e_vals, n_vals)
    df['lat'], df['lon'] = transform_johor_coords(df['E'].values, df['N'].values)

    # --- THE INTERACTIVE DASHBOARD ---
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Survey Area", f"{area_m2:.3f} m²")
        st.write(f"**Lots:** 11462 - 11487 ")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.write("### 📥 Task 2: Data Export")
        geojson_data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"Surveyor": "Tamilkumaran", "Area": area_m2},
                "geometry": {"type": "Polygon", "coordinates": [[[r['lon'], r['lat']] for _, r in df.iterrows()] + [[df.iloc[0]['lon'], df.iloc[0]['lat']]]]}
            }]
        }
        st.download_button("Download GeoJSON", json.dumps(geojson_data), "tamilkumaran_survey.geojson", use_container_width=True)

    with col2:
        st.write("### 📋 Surveyor's Log (Cassini to WGS84)")
        st.dataframe(df[['STN', 'E', 'N', 'lat', 'lon']], hide_index=True, use_container_width=True)

    st.divider()

    # --- TASK 3 & 4: THE INTERACTIVE OVERLAY MAP ---
    st.write("### 🗺️ Live Interactive Geospatial View")
    
    # Initialize Map
    center_lat, center_lon = df['lat'].mean(), df['lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=19, tiles=None)

    # Map Type Switcher
    if map_type == "Satellite Imagery":
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', 
            attr='Google', name='Google Satellite', overlay=False, control=True
        ).add_to(m)
    else:
        folium.TileLayer('cartodbpositron', name='Street Map').add_to(m)

    # The Interactive Polygon Overlay
    poly_coords = [[row['lat'], row['lon']] for _, row in df.iterrows()]
    folium.Polygon(
        locations=poly_coords,
        color="#38bdf8", weight=5, fill=True, fill_color="#38bdf8", fill_opacity=0.4,
        tooltip=f"Lot Area: {area_m2:.3f} m²"
    ).add_to(m)

    # Station Markers
    if show_labels:
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=6, color="#ffffff", fill=True, fill_color="#ef4444", fill_opacity=1,
                popup=f"STN {int(row['STN'])}<br>E: {row['E']}<br>N: {row['N']}"
            ).add_to(m)

    # Floating Info Box (The "Cool" Letterbox)
    if show_area_box:
        info_html = f"""
        <div style="position: fixed; bottom: 50px; left: 50px; width: 250px; z-index:9999; 
        background: white; padding: 15px; border-radius: 10px; border: 3px solid #0f172a; 
        box-shadow: 5px 5px 15px rgba(0,0,0,0.3); font-family: Arial;">
            <b style="color:#0f172a; font-size:14px;">MUKIM KESANG, JOHOR </b><br>
            <span style="color:#64748b;">Surveyor: Tamilkumaran</span><br>
            <hr style="margin: 5px 0;">
            <span style="font-size:16px; font-weight:bold; color:#0f172a;">AREA: {area_m2:.3f} m²</span>
        </div>
        """
        st.markdown(info_html, unsafe_allow_html=True)

    folium_static(m, width=1300, height=650)
else:
    st.info("👋 Welcome back, Tamilkumaran. Please upload your survey data (point.csv) to activate the dashboard.")