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
        
        # Distance
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        
        # Bearing Calculation (Azimuth)
        dz = p2[0] - p1[0] # Delta Easting
        dn = p2[1] - p1[1] # Delta Northing
        angle_deg = np.degrees(np.arctan2(dz, dn)) % 360
        
        # --- ALIGNMENT LOGIC (For PA Look) ---
        # We calculate the mathematical rotation for the CSS transform
        # We subtract 90 to align text along the vector
        rotation = 90 - angle_deg
        
        # Normalize rotation so text is never upside down (Kemas)
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

# --- CUSTOM CSS (Clean, Spacious, Massive) ---
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    
    .hero-container {
        text-align: center;
        padding: 70px 20px;
        background: #ffffff; 
        margin-bottom: 40px;
        border-radius: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    .poli-title { 
        color: #0b172a !important; 
        font-size: 110px; 
        font-weight: 900; 
        margin: 15px 0; 
        letter-spacing: 15px;
        line-height: 1;
        text-transform: uppercase;
    }
    
    .surveyor-sub { 
        color: #38bdf8 !important; 
        font-size: 38px; 
        font-weight: 600; 
        letter-spacing: 8px;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MAIN PAGE HEADER ---
st.markdown('<div class="hero-container">', unsafe_allow_html=True)
if os.path.exists("logo_puo.png"):
    st.image("logo_puo.png", width=250)
st.markdown(f"""
        <p class="poli-title">POLITEKNIK UNGKU OMAR</p>
        <p class="surveyor-sub">Lead Surveyor: Tamilkumaran</p>
    </div>
    """, unsafe_allow_html=True)

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("📂 UPLOAD 'point.csv' TO ACTIVATE GIS CONTROLS", type="csv")

if uploaded_file:
    # 1. DATA PREP
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    df['lat'], df['lon'] = transform_coords_johor(df['E'].values, df['N'].values)
    dist, bear, rot = get_survey_math(df)
    df['Distance'], df['Bearing'], df['Rotation'] = dist, bear, rot
    area_val = calculate_area(df['E'].values, df['N'].values)

    # 2. SIDEBAR (Hidden until file is uploaded)
    with st.sidebar:
        st.header("🕹️ DISPLAY CONTROLLER")
        sat_mode = st.toggle("🛰️ Google Satellite", value=True)
        label_mode = st.toggle("📍 Show All Labels", value=True)
        st.markdown("---")
        stn_size = st.slider("Station ID Size", 8, 30, 14)
        dim_size = st.slider("Label Text Size", 6, 20, 10)
        marker_rad = st.slider("Marker Point Size", 2, 20, 7)
        st.markdown("---")
        if st.button("Logout System"):
            st.session_state.clear()
            st.rerun()

    # 3. MAP GENERATION
    m = folium.Map(
        location=[df['lat'].mean(), df['lon'].mean()], 
        zoom_start=20, 
        max_zoom=22,
        tiles=None 
    )

    # SATELLITE TOGGLE
    if sat_mode:
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
            attr='Google', name='Satellite', max_zoom=22, overlay=False
        ).add_to(m)
    else:
        folium.TileLayer('cartodbpositron', name='Clean Map').add_to(m)

    # Lot Boundary
    poly_pts = [[row['lat'], row['lon']] for _, row in df.iterrows()]
    folium.Polygon(locations=poly_pts, color="#FBFF00", weight=4, fill=True, fill_opacity=0.1).add_to(m)

    # PA-STYLE LABELLING
    for i, row in df.iterrows():
        # Coordinate Hover
        folium.CircleMarker(
            location=[row['lat'], row['lon']], 
            radius=marker_rad, color="#FF0000", fill=True,
            tooltip=f"COORDS: E {row['E']:.3f}, N {row['N']:.3f}"
        ).add_to(m)
        
        if label_mode:
            # Station Label
            folium.Marker([row['lat'], row['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:white; font-weight:bold; text-shadow:2px 2px black;">{int(row["STN"])}</div>')
            ).add_to(m)
            
            # --- ALIGNED TEXT (PERPENDICULAR TO LINE) ---
            next_p = df.iloc[(i+1)%len(df)]
            m_lat, m_lon = (row['lat']+next_p['lat'])/2, (row['lon']+next_p['lon'])/2
            
            folium.Marker([m_lat, m_lon],
                icon=folium.DivIcon(html=f"""
                    <div style="
                        transform: rotate({row['Rotation']}deg) translateY(-10px); 
                        font-size:{dim_size}pt; 
                        color:#38bdf8; 
                        font-weight:bold; 
                        text-shadow: 1px 1px 2px black;
                        white-space:nowrap;
                        text-align:center;">
                        {row['Bearing']} <br> {row['Distance']}m
                    </div>""")
            ).add_to(m)

    st.subheader("🛰️ Interactive Survey Visualization")
    folium_static(m, width=1200, height=750)
    
    # Bottom Stats
    c1, c2 = st.columns(2)
    c1.metric("LOT AREA", f"{area_val:.3f} m²")
    c2.dataframe(df[['STN', 'Distance', 'Bearing']], hide_index=True, use_container_width=True)

else:
    st.info("👋 Welcome Tamilkumaran. Please upload your 'point.csv' to reveal the Professional GIS Layout.")