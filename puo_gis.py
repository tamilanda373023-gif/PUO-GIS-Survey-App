import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import numpy as np
import base64
import requests
from pyproj import Transformer

# --- CORE CALCULATIONS ---
def calculate_area(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def get_survey_math(df):
    distances, bearings, angles = [], [], []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        next_idx = (i + 1) % len(df)
        p2 = (df.iloc[next_idx]['E'], df.iloc[next_idx]['N'])
        
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        dz = p2[0] - p1[0] 
        dn = p2[1] - p1[1] 
        angle_deg = np.degrees(np.arctan2(dz, dn)) % 360
        
        rotation = 90 - angle_deg
        if rotation > 90: rotation -= 180
        if rotation < -90: rotation += 180
        
        distances.append(round(dist, 3))
        bearings.append(f"{int(angle_deg)}° {int((angle_deg%1)*60)}'")
        angles.append(rotation)
    return distances, bearings, angles

def transform_coords_johor(e, n):
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
        display: flex; align-items: center; padding: 30px 40px;
        background: #1e293b; margin-bottom: 30px;
        border-radius: 15px; border-bottom: 6px solid #38bdf8;
    }
    .left-branding { display: flex; align-items: center; flex: 1.5; }
    .center-branding { flex: 2; text-align: center; }
    .poli-name-text { 
        color: #FFFFFF !important; font-size: 26px; font-weight: 800; 
        margin-left: 20px; text-transform: uppercase;
    }
    .middle-system-title {
        color: #FFFFFF !important; font-size: 50px; font-weight: 900;
        text-transform: uppercase; margin: 0;
    }
    .surveyor-credit { color: #38bdf8 !important; font-size: 18px; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER WITH ROBUST LOGO LOADING ---
# If the logo is in your local folder, use that. Otherwise, it uses a fallback.
logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Logo_PUO.png/200px-Logo_PUO.png"

st.markdown(f"""
    <div class="hero-container">
        <div class="left-branding">
            <img src="{logo_url}" width="100" onerror="this.src='https://via.placeholder.com/100?text=PUO+LOGO'">
            <p class="poli-name-text">POLITEKNIK UNGKU OMAR</p>
        </div>
        <div class="center-branding">
            <p class="middle-system-title">SISTEM SURVEY LOT PUO</p>
            <p class="surveyor-credit">Lead Surveyor: Tamilkumaran</p>
        </div>
        <div style="flex:1;"></div>
    </div>
    """, unsafe_allow_html=True)

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("📂 UPLOAD 'point.csv' TO ACTIVATE CONTROLS AND MAP", type="csv")

if uploaded_file:
    # Use order from CSV (No sorting to keep lines correct)
    df = pd.read_csv(uploaded_file)
    df['lat'], df['lon'] = transform_coords_johor(df['E'].values, df['N'].values)
    dist, bear, rot = get_survey_math(df)
    df['Distance'], df['Bearing'], df['Rotation'] = dist, bear, rot
    area_val = calculate_area(df['E'].values, df['N'].values)

    with st.sidebar:
        st.markdown("## 🕹️ DISPLAY CONTROLLER")
        sat_mode = st.toggle("🛰️ Google Satellite Mode", value=True)
        label_mode = st.toggle("📍 Show All Map Labels", value=True)
        st.markdown("---")
        stn_size = st.slider("Station ID Size", 8, 30, 15)
        dim_size = st.slider("Bering/Distance Size", 6, 20, 11)
        marker_rad = st.slider("Marker Point Size", 2, 20, 8)

    # MAP
    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=20, max_zoom=22, tiles=None)

    if sat_mode:
        folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                         attr='Google', name='Satellite', max_zoom=22, overlay=False).add_to(m)
    else:
        folium.TileLayer('cartodbpositron', name='Clean Map').add_to(m)

    # Ordered Boundary
    poly_pts = [[row['lat'], row['lon']] for _, row in df.iterrows()]
    folium.Polygon(locations=poly_pts, color="#FBFF00", weight=4, fill=True, fill_opacity=0.15).add_to(m)

    # Labeling in Order
    for i, row in df.iterrows():
        folium.CircleMarker(location=[row['lat'], row['lon']], radius=marker_rad, color="#FF0000", fill=True,
                            tooltip=f"COORDS: E {row['E']:.3f}, N {row['N']:.3f}").add_to(m)
        
        if label_mode:
            # Station Label
            folium.Marker([row['lat'], row['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:white; font-weight:bold; text-shadow:2px 2px black;">{int(row["STN"])}</div>')).add_to(m)
            
            # Distance/Bearing aligned to specific line
            next_idx = (i + 1) % len(df)
            next_p = df.iloc[next_idx]
            m_lat, m_lon = (row['lat'] + next_p['lat']) / 2, (row['lon'] + next_p['lon']) / 2
            
            folium.Marker([m_lat, m_lon],
                icon=folium.DivIcon(html=f"""
                    <div style="transform: rotate({row['Rotation']}deg) translateY(-12px); 
                                font-size:{dim_size}pt; color:#38bdf8; font-weight:bold; 
                                text-shadow: 1px 1px 2px black; white-space:nowrap; text-align:center;">
                        {row['Bearing']} <br> {row['Distance']}m
                    </div>""")).add_to(m)

    st.subheader("🛰️ Interactive Survey Visualization")
    folium_static(m, width=1200, height=750)
    
    c1, c2 = st.columns(2)
    c1.metric("LOT AREA", f"{area_val:.3f} m²")
    c2.dataframe(df[['STN', 'Distance', 'Bearing']], hide_index=True, use_container_width=True)

else:
    st.info("System Ready. Please upload 'point.csv' to reveal controls and map.")