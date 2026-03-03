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
        
        # Calculate angle for DMS and for Label Rotation
        raw_angle = np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360
        # Math for label rotation (adjusting to keep text upright)
        rotation = 90 - raw_angle
        if rotation < -90: rotation += 180
        if rotation > 90: rotation -= 180
        
        distances.append(round(dist, 3))
        bearings.append(f"{int(raw_angle)}° {int((raw_angle%1)*60)}'")
        angles.append(rotation)
    return distances, bearings, angles

def transform_coords_johor(e, n):
    # Using EPSG:4390 for Johor Cassini as per PA 143912
    transformer = Transformer.from_crs("epsg:4390", "epsg:4326", always_xy=True)
    lon, lat = transformer.transform(e, n)
    return lat, lon

# --- PAGE SETUP ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- CUSTOM CSS (Bigger White Title) ---
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    .header-box {
        background: #1e293b; padding: 25px; border-radius: 15px;
        border-bottom: 5px solid #38bdf8; margin-bottom: 25px;
        display: flex; align-items: center;
    }
    .main-title { color: #FFFFFF !important; font-size: 52px; font-weight: 900; margin: 0; line-height: 1; }
    .surveyor-tag { color: #38bdf8 !important; font-size: 24px; font-weight: bold; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.markdown('<div class="header-box">', unsafe_allow_html=True)
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo_puo.png"):
        st.image("logo_puo.png", width=180)
with col_title:
    st.markdown('<p class="main-title">POLITEKNIK UNGKU OMAR</p>', unsafe_allow_html=True)
    st.markdown('<p class="surveyor-tag">Surveyor: Tamilkumaran</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 Upload 'point.csv'", type="csv")

if uploaded_file:
    # 1. DATA PROCESSING
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    df['lat'], df['lon'] = transform_coords_johor(df['E'].values, df['N'].values)
    dist, bear, rot = get_survey_math(df)
    df['Distance'], df['Bearing'], df['Rotation'] = dist, bear, rot
    area_m2 = calculate_area(df['E'].values, df['N'].values)

    # 2. SIDEBAR (Only visible after upload)
    with st.sidebar:
        st.header("🎮 Display Settings")
        stn_txt_size = st.slider("STN Text Size", 8, 20, 12)
        dim_txt_size = st.slider("Bearing/Dist Size", 6, 16, 9)
        marker_rad = st.slider("Marker Point Size", 2, 12, 5)
        map_zoom = st.slider("Initial Zoom", 18, 22, 21)

    # 3. MAP LAYOUT
    col_map, col_data = st.columns([3, 1])
    with col_map:
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=map_zoom, max_zoom=22)

        # GOOGLE LAYERS
        folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', 
                         attr='Google', name='Google Satellite', max_zoom=22, max_native_zoom=20).add_to(m)
        folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                         attr='Google', name='Google Hybrid', max_zoom=22, max_native_zoom=20).add_to(m)

        # POLYGON
        poly_pts = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(locations=poly_pts, color="yellow", weight=3, fill=True, fill_opacity=0.15).add_to(m)

        # STATIONS & DYNAMIC LABELS
        for i, row in df.iterrows():
            # Marker with Coordinate Hover (Tooltip)
            folium.CircleMarker(
                location=[row['lat'], row['lon']], 
                radius=marker_rad, color="#ef4444", fill=True,
                tooltip=f"E: {row['E']:.3f}, N: {row['N']:.3f}" # THE HOVER FEATURE
            ).add_to(m)
            
            # STN Number
            folium.Marker([row['lat'], row['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{stn_txt_size}pt; color:white; font-weight:bold; text-shadow:1px 1px black;">{int(row["STN"])}</div>')
            ).add_to(m)
            
            # Aligned Bearing & Distance (Kemas & Allign)
            next_p = df.iloc[(i+1)%len(df)]
            m_lat, m_lon = (row['lat']+next_p['lat'])/2, (row['lon']+next_p['lon'])/2
            folium.Marker([m_lat, m_lon],
                icon=folium.DivIcon(html=f"""
                    <div style="transform: rotate({row['Rotation']}deg); 
                                font-size:{dim_txt_size}pt; color:#38bdf8; font-weight:bold; 
                                background:rgba(0,0,0,0.5); padding:2px; white-space:nowrap; 
                                text-align:center; border-radius:3px;">
                        {row['Bearing']} | {row['Distance']}m
                    </div>""")
            ).add_to(m)

        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        folium_static(m, width=1000, height=650)

    with col_data:
        st.metric("TOTAL AREA", f"{area_m2:.3f} m²")
        st.write("**Location:** Mukim Kesang, Johor")
        st.dataframe(df[['STN', 'Distance', 'Bearing']], hide_index=True)