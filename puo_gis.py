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

def get_bearing(p1, p2):
    """Calculates bearing between two points for the survey table."""
    angle = np.arctan2(p2[0] - p1[0], p2[1] - p1[1])
    bearing = np.degrees(angle) % 360
    return bearing

def transform_johor_coords(e, n):
    transformer = Transformer.from_crs("epsg:3168", "epsg:4326")
    lat, lon = transformer.transform(e, n)
    return lat, lon

# --- PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS | Tamilkumaran", layout="wide")

# --- STYLE ---
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    .header-box {
        background: #1e293b; padding: 30px; border-radius: 15px;
        border-bottom: 5px solid #38bdf8; margin-bottom: 20px;
    }
    .main-title { color: white; font-size: 40px; font-weight: bold; margin: 0; }
    .surveyor-tag { color: #38bdf8; font-size: 22px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🛠️ INTERACTIVE CONTROLS")
show_labels = st.sidebar.checkbox("📍 Show Labels & Coordinates", value=False)
st.sidebar.markdown("---")
st.sidebar.info("Surveyor: Tamilkumaran\nRegion: Mukim Kesang, Johor")

# --- HEADER ---
st.markdown(f"""
    <div class="header-box">
        <p class="main-title">POLITEKNIK UNGKU OMAR</p>
        <p class="surveyor-tag">Surveyor: Tamilkumaran</p>
    </div>
    """, unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 Upload 'point.csv'", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    
    # Transformations
    df['lat'], df['lon'] = transform_johor_coords(df['E'].values, df['N'].values)
    area_m2 = calculate_area(df['E'].values, df['N'].values)

    # Calculate Bearings for the table
    bearings = []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        p2 = (df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N'])
        bearings.append(get_bearing(p1, p2))
    df['Bearing (°)'] = bearings

    # --- OUTPUTS ---
    col_map, col_data = st.columns([2, 1])

    with col_map:
        st.write("### 🛰️ Satellite Survey Overlay")
        # Center map on Johor points 
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19)
        
        # FORCED SATELLITE BACKGROUND 
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', 
            attr='Google', name='Google Satellite', overlay=False
        ).add_to(m)

        # DRAW POLYGON 
        poly_coords = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(
            locations=poly_coords, color="#38bdf8", weight=4, 
            fill=True, fill_color="#38bdf8", fill_opacity=0.3
        ).add_to(m)

        # LABELS ONLY ON WHEN BUTTON IS PRESSED 
        if show_labels:
            for _, row in df.iterrows():
                # Marker with Coordinate Popup
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    popup=f"STN: {int(row['STN'])}<br>E: {row['E']}<br>N: {row['N']}",
                    icon=folium.DivIcon(html=f"""
                        <div style="font-family: sans-serif; color: yellow; font-weight: bold; 
                        text-shadow: 2px 2px black; font-size: 12pt;">
                            STN {int(row['STN'])}
                        </div>""")
                ).add_to(m)

        folium_static(m, width=850, height=550)

    with col_data:
        st.write("### 📊 Survey Results")
        st.metric("Total Area", f"{area_m2:.3f} m²")
        st.write("**Mukim:** Kesang, Johor [cite: 2]")
        st.write("**Lot:** 11462-11487 [cite: 2]")
        st.dataframe(df[['STN', 'E', 'N', 'Bearing (°)']], hide_index=True)
        
        # EXPORT
        geojson = {"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[r['lon'],r['lat']] for _,r in df.iterrows()]]}}]}
        st.download_button("📥 Export GeoJSON", json.dumps(geojson), "Tamilkumaran_Survey.geojson")

else:
    st.warning("Please upload 'point.csv' to view the Satellite Overlay.")