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
        
        # Calculate angle for rotation
        raw_angle = np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360
        rotation = 90 - raw_angle
        if rotation < -90: rotation += 180
        if rotation > 90: rotation -= 180
        
        distances.append(round(dist, 3))
        bearings.append(f"{int(raw_angle)}° {int((raw_angle%1)*60)}'")
        angles.append(rotation)
    return distances, bearings, angles

def transform_coords_johor(e, n):
    # Using Johor Cassini Grid
    transformer = Transformer.from_crs("epsg:4390", "epsg:4326", always_xy=True)
    lon, lat = transformer.transform(e, n)
    return lat, lon

# --- PAGE SETUP ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- CUSTOM CSS (Massive White Title) ---
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    .header-box {
        background: rgba(30, 41, 59, 0.8); padding: 40px; border-radius: 20px;
        border-left: 10px solid #38bdf8; margin-bottom: 30px;
    }
    .main-title { color: #FFFFFF !important; font-size: 64px; font-weight: 900; margin: 0; letter-spacing: -2px; }
    .surveyor-tag { color: #38bdf8 !important; font-size: 28px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
    <div class="header-box">
        <p class="main-title">POLITEKNIK UNGKU OMAR</p>
        <p class="surveyor-tag">Surveyor: Tamilkumaran</p>
    </div>
    """, unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 Upload 'point.csv'", type="csv")

if uploaded_file:
    # 1. DATA PREP
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    df['lat'], df['lon'] = transform_coords_johor(df['E'].values, df['N'].values)
    dist, bear, rot = get_survey_math(df)
    df['Distance'], df['Bearing'], df['Rotation'] = dist, bear, rot
    area_val = calculate_area(df['E'].values, df['N'].values)

    # 2. LEFT SIDE CONTROL PANEL
    with st.sidebar:
        if os.path.exists("logo_puo.png"):
            st.image("logo_puo.png", width=220)
        
        st.title("🛠️ Display Controls")
        show_sat = st.toggle("Enable Google Satellite", value=True)
        show_labels = st.toggle("Show Map Labels", value=True)
        
        st.markdown("---")
        st.subheader("📏 Size Adjustments")
        stn_size = st.slider("STN Text", 8, 24, 14)
        dim_size = st.slider("Bearing/Distance Text", 6, 20, 10)
        marker_rad = st.slider("Point Radius", 2, 15, 6)
        
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    # 3. INTERACTIVE MAP
    m = folium.Map(
        location=[df['lat'].mean(), df['lon'].mean()], 
        zoom_start=20, 
        max_zoom=22,
        tiles=None # Start with blank to apply toggle
    )

    # Apply Satellite Toggle from Sidebar
    if show_sat:
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
            attr='Google', name='Google Hybrid', max_zoom=22, overlay=False
        ).add_to(m)
    else:
        folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)

    # Draw Boundary
    poly_pts = [[row['lat'], row['lon']] for _, row in df.iterrows()]
    folium.Polygon(locations=poly_pts, color="yellow", weight=4, fill=True, fill_opacity=0.1).add_to(m)

    # Station Marks & Labels
    for i, row in df.iterrows():
        # Hover coordinate feature
        folium.CircleMarker(
            location=[row['lat'], row['lon']], 
            radius=marker_rad, color="#ef4444", fill=True,
            tooltip=f"Coordinate: E {row['E']:.3f}, N {row['N']:.3f}"
        ).add_to(m)
        
        if show_labels:
            # Clean STN Label
            folium.Marker([row['lat'], row['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:white; font-weight:bold; text-shadow:2px 2px black;">{int(row["STN"])}</div>')
            ).add_to(m)
            
            # Aligned Dimensions
            next_p = df.iloc[(i+1)%len(df)]
            m_lat, m_lon = (row['lat']+next_p['lat'])/2, (row['lon']+next_p['lon'])/2
            folium.Marker([m_lat, m_lon],
                icon=folium.DivIcon(html=f"""
                    <div style="transform: rotate({row['Rotation']}deg); 
                                font-size:{dim_size}pt; color:#38bdf8; font-weight:bold; 
                                background:rgba(0,0,0,0.7); padding:4px; border-radius:5px;
                                white-space:nowrap; border: 1px solid #38bdf8;">
                        {row['Bearing']} | {row['Distance']}m
                    </div>""")
            ).add_to(m)

    # Display Map and Data
    st.subheader("🛰️ Live Survey Visualization")
    folium_static(m, width=1100, height=650)
    
    col1, col2 = st.columns([1, 1])
    col1.metric("TOTAL LOT AREA", f"{area_val:.3f} m²")
    col2.dataframe(df[['STN', 'Distance', 'Bearing']], hide_index=True, use_container_width=True)

else:
    st.info("👋 Welcome! Please upload your 'point.csv' to view the Professional GIS Layout.")