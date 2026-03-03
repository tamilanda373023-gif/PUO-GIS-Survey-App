import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import numpy as np
import json
import os

# --- CORE FUNCTIONS ---
def calculate_area(x, y):
    """Calculates polygon area using the Shoelace formula."""
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS - Integrated Overlay", layout="wide")

# --- CLASSY STYLING (Task 1) ---
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: white; }
    .header-container {
        background-color: #1e293b; 
        padding: 40px; 
        border-radius: 0px 0px 20px 20px; 
        margin-bottom: 30px;
        border-bottom: 5px solid #38bdf8;
    }
    .header-title { color: #ffffff !important; font-size: 48px; font-weight: bold; margin: 0; }
    .report-title { color: #22d3ee !important; text-align: center; font-weight: bold; font-size: 35px; }
    
    div.stButton > button {
        background-color: #38bdf8;
        color: #0f172a;
        font-weight: bold;
        height: 3.5em;
        width: 100%;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (Task 1-4 Persistent Controls) ---
st.sidebar.title("⚙️ Map Settings")
show_satellite = st.sidebar.checkbox("🛰️ Open Satellite Layer (On/Off)", value=True)
st.sidebar.markdown("---")
st.sidebar.title("🏷️ Label Settings")
show_stn_labels = st.sidebar.checkbox("Display Station Labels (STN)", value=True)
show_area_label = st.sidebar.checkbox("Display Area Label", value=True)

# --- TASK 1: BRANDING ---
st.markdown('<div class="header-container">', unsafe_allow_html=True)
col_logo, col_title = st.columns([2.5, 3])
with col_logo:
    if os.path.exists("logo_puo.png"):
        st.image("logo_puo.png", width=450) # Extra-Large Logo
with col_title:
    st.write("##") 
    st.markdown('<p class="header-title">POLITEKNIK UNGKU OMAR</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8; font-size: 20px;">Civil Engineering GIS Dashboard</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("📂 Upload Survey Data (point.csv)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    
    # State management to keep results visible
    if 'active' not in st.session_state:
        st.session_state.active = False

    if st.button("🚀 GENERATE INTEGRATED ANALYSIS"):
        st.session_state.active = True

    if st.session_state.active:
        x, y = df['E'].values, df['N'].values
        area_val = calculate_area(x, y)
        
        # --- TASK 4: BRIGHT REPORT TITLE ---
        st.divider()
        st.markdown('<p class="report-title">📊 INTEGRATED SURVEY ANALYSIS REPORT</p>', unsafe_allow_html=True)
        
        col_res, col_tab = st.columns([1, 2])
        with col_res:
            st.metric("CALCULATED AREA", f"{area_val:.3f} m²")
            # TASK 2: EXPORT
            coords_geo = [[float(row['E']), float(row['N'])] for _, row in df.iterrows()]
            coords_geo.append(coords_geo[0])
            geojson = {"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[coords_geo]}}]}
            st.download_button("📥 Download GeoJSON for QGIS", json.dumps(geojson), "puo_survey.geojson")

        with col_tab:
            st.write("### 📋 Coordinate Table")
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()

        # --- TASK 3 & 4: OVERLAY SATELLITE MAP ---
        st.subheader("🛰️ Integrated Satellite Overlay")
        
        # Use simple mean for centering (assuming Lat/Lon data in point.csv)
        m = folium.Map(location=[df['N'].mean(), df['E'].mean()], zoom_start=18)
        
        if show_satellite:
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', 
                attr='Google', 
                name='Google Satellite'
            ).add_to(m)

        # Draw the Polygon directly on the map
        poly_points = [[row['N'], row['E']] for _, row in df.iterrows()]
        folium.Polygon(
            locations=poly_points,
            color="#22d3ee",
            weight=4,
            fill=True,
            fill_color="#22d3ee",
            fill_opacity=0.4
        ).add_to(m)

        # Station Labels Overlay
        if show_stn_labels:
            for _, row in df.iterrows():
                folium.Marker(
                    location=[row['N'], row['E']],
                    icon=folium.DivIcon(html=f"""
                        <div style="font-family: sans-serif; color: white; font-weight: bold; 
                        background-color: rgba(0,0,0,0.5); padding: 2px 5px; border-radius: 3px;
                        border: 1px solid white; white-space: nowrap;">
                            STN {int(row['STN'])}
                        </div>
                    """)
                ).add_to(m)

        # Area Label Overlay in the center
        if show_area_label:
            folium.Marker(
                location=[df['N'].mean(), df['E'].mean()],
                icon=folium.DivIcon(html=f"""
                    <div style="background: white; border: 3px solid black; padding: 10px; 
                    font-weight: bold; color: black; width: 180px; text-align: center; 
                    border-radius: 5px; font-size: 14px;">
                        AREA:<br>{area_val:.3f} m²
                    </div>
                """)
            ).add_to(m)

        folium_static(m, width=1200, height=600)

else:
    st.info("👋 Welcome! Please upload your 'point.csv' file to begin.")