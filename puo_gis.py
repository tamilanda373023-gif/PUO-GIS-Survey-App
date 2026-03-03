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
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def get_survey_math(df):
    distances, bearings, angles = [], [], []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        p2 = (df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N'])
        
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        dz = p2[0] - p1[0] 
        dn = p2[1] - p1[1] 
        angle_deg = np.degrees(np.arctan2(dz, dn)) % 360
        
        # Professional PA Alignment logic for "Kemas" look
        rotation = 90 - angle_deg
        if rotation > 90: rotation -= 180
        if rotation < -90: rotation += 180
        
        distances.append(round(dist, 3))
        bearings.append(f"{int(angle_deg)}° {int((angle_deg%1)*60)}'")
        angles.append(rotation)
    return distances, bearings, angles

def transform_coords_johor(e, n):
    # Precise Johor Cassini (EPSG:4390)
    transformer = Transformer.from_crs("epsg:4390", "epsg:4326", always_xy=True)
    lon, lat = transformer.transform(e, n)
    return lat, lon

# --- PAGE SETUP ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    
    .hero-container {
        display: flex;
        align-items: center;
        padding: 40px 40px;
        background: #1e293b; 
        margin-bottom: 30px;
        border-radius: 15px;
        border-bottom: 6px solid #38bdf8;
    }
    
    .left-branding {
        display: flex;
        align-items: center;
        flex: 1.2;
    }

    .center-branding {
        flex: 2;
        text-align: center;
    }

    .poli-name-text { 
        color: #FFFFFF !important; 
        font-size: 26px; 
        font-weight: 800; 
        margin-left: 20px;
        margin-bottom: 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .middle-system-title {
        color: #FFFFFF !important;
        font-size: 55px;
        font-weight: 900;
        letter-spacing: 3px;
        margin: 0;
        text-transform: uppercase;
    }
    
    .surveyor-credit { 
        color: #38bdf8 !important; 
        font-size: 18px; 
        font-weight: 400;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER (LOGO + NAME LEFT | SYSTEM TITLE MIDDLE) ---
st.markdown(f"""
    <div class="hero-container">
        <div class="left-branding">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Logo_PUO.png/600px-Logo_PUO.png" width="90">
            <p class="poli-name-text">POLITEKNIK UNGKU OMAR</p>
        </div>
        <div class="center-branding">
            <p class="middle-system-title">SISTEM SURVEY LOT PUO</p>
            <p class="surveyor-credit">Lead Surveyor: Tamilkumaran</p>
        </div>
        <div style="flex:1;"></div>
    </div>
    """, unsafe_allow_html=True)

# --- FILE UPLOADER (GATEKEEPER) ---
uploaded_file = st.file_uploader("📂 UPLOAD 'point.csv' TO ACTIVATE CONTROLS AND MAP", type="csv")

if uploaded_file:
    # 1. DATA PROCESSING
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    df['lat'], df['lon'] = transform_coords_johor(df['E'].values, df['N'].values)
    dist, bear, rot = get_survey_math(df)
    df['Distance'], df['Bearing'], df['Rotation'] = dist, bear, rot
    area_val = calculate_area(df['E'].values, df['N'].values)

    # 2. SIDEBAR CONTROLLER (Shown only after file insert)
    with st.sidebar:
        st.markdown("## 🕹️ DISPLAY CONTROLLER")
        st.markdown("---")
        sat_mode = st.toggle("🛰️ Google Satellite Mode", value=True)
        label_mode = st.toggle("📍 Show All Map Labels", value=True)
        st.markdown("---")
        stn_size = st.slider("Station ID Size", 8, 30, 15)
        dim_size = st.slider("Bering/Distance Size", 6, 20, 11)
        marker_rad = st.slider("Marker Point Size", 2, 20, 8)
        st.markdown("---")
        if st.button("🚪 Logout System"):
            st.session_state.clear()
            st.rerun()

    # 3. MAP RENDERING
    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=20, max_zoom=22, tiles=None)

    # Satellite Toggle Logic
    if sat_mode:
        folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                         attr='Google', name='Satellite', max_zoom=22, overlay=False).add_to(m)
    else:
        folium.TileLayer('cartodbpositron', name='Clean Map').add_to(m)

    # Drawing Lot Boundary
    poly_pts = [[row['lat'], row['lon']] for _, row in df.iterrows()]
    folium.Polygon(locations=poly_pts, color="#FBFF00", weight=4, fill=True, fill_opacity=0.15).add_to(m)

    # Plotting Points & Aligned Labels
    for i, row in df.iterrows():
        # Hover coordinate feature (STN Mark)
        folium.CircleMarker(location=[row['lat'], row['lon']], radius=marker_rad, color="#FF0000", fill=True,
                            tooltip=f"COORDINATES: E {row['E']:.3f}, N {row['N']:.3f}").add_to(m)
        
        if label_mode:
            # Station Label
            folium.Marker([row['lat'], row['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:white; font-weight:bold; text-shadow:2px 2px black;">{int(row["STN"])}</div>')).add_to(m)
            
            # Kemas Aligned Dimensions (Parallel to Line)
            next_p = df.iloc[(i+1)%len(df)]
            m_lat, m_lon = (row['lat']+next_p['lat'])/2, (row['lon']+next_p['lon'])/2
            folium.Marker([m_lat, m_lon],
                icon=folium.DivIcon(html=f"""
                    <div style="transform: rotate({row['Rotation']}deg) translateY(-12px); 
                                font-size:{dim_size}pt; color:#38bdf8; font-weight:bold; 
                                text-shadow: 1px 1px 2px black; white-space:nowrap; text-align:center;">
                        {row['Bearing']} <br> {row['Distance']}m
                    </div>""")).add_to(m)

    st.subheader("🛰️ Interactive Survey Visualization")
    folium_static(m, width=1200, height=750)
    
    # Bottom Stats
    c1, c2 = st.columns(2)
    c1.metric("LOT AREA", f"{area_val:.3f} m²")
    c2.dataframe(df[['STN', 'Distance', 'Bearing']], hide_index=True, use_container_width=True)

else:
    st.info("System Ready. Please upload 'point.csv' to reveal controls and interactive map.")