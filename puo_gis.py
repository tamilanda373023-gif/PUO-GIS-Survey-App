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
        
        # Calculate angle for rotation to make it "Kemas"
        raw_angle = np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360
        rotation = 90 - raw_angle
        if rotation < -90: rotation += 180
        if rotation > 90: rotation -= 180
        
        distances.append(round(dist, 3))
        bearings.append(f"{int(raw_angle)}° {int((raw_angle%1)*60)}'")
        angles.append(rotation)
    return distances, bearings, angles

def transform_coords_johor(e, n):
    # Precise Johor Cassini Transformation (EPSG:4390)
    transformer = Transformer.from_crs("epsg:4390", "epsg:4326", always_xy=True)
    lon, lat = transformer.transform(e, n)
    return lat, lon

# --- PAGE SETUP ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- CUSTOM CSS (Massive Clean Header) ---
st.markdown("""
    <style>
    .stApp { background-color: #0b172a; color: white; }
    .main-header {
        text-align: center;
        padding: 50px 20px;
        background: linear-gradient(180deg, #1e293b 0%, #0b172a 100%);
        border-bottom: 8px solid #38bdf8;
        margin-bottom: 40px;
        border-radius: 0 0 30px 30px;
    }
    .poli-title { 
        color: #FFFFFF !important; 
        font-size: 85px; 
        font-weight: 900; 
        margin: 0; 
        letter-spacing: -3px;
        text-transform: uppercase;
    }
    .surveyor-sub { 
        color: #38bdf8 !important; 
        font-size: 32px; 
        font-weight: 400; 
        margin-top: 10px;
        letter-spacing: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MASSIVE MAIN PAGE HEADER ---
st.markdown(f"""
    <div class="main-header">
        <p class="poli-title">POLITEKNIK UNGKU OMAR</p>
        <p class="surveyor-sub">Lead Surveyor: Tamilkumaran</p>
    </div>
    """, unsafe_allow_html=True)

# --- SIDEBAR (Controls Only) ---
with st.sidebar:
    if os.path.exists("logo_puo.png"):
        st.image("logo_puo.png", use_container_width=True)
    st.title("🕹️ Display Controls")
    show_labels = st.toggle("Show Station & Line Labels", value=True)
    st.markdown("---")
    stn_size = st.slider("Station Text Size", 8, 30, 14)
    dim_size = st.slider("Dimension Text Size", 6, 20, 10)
    marker_rad = st.slider("Marker Point Radius", 2, 20, 7)
    st.markdown("---")
    if st.button("🚪 Logout System"):
        st.session_state.clear()
        st.rerun()

uploaded_file = st.file_uploader("📂 Drag and Drop 'point.csv' here", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    df['lat'], df['lon'] = transform_coords_johor(df['E'].values, df['N'].values)
    dist, bear, rot = get_survey_math(df)
    df['Distance'], df['Bearing'], df['Rotation'] = dist, bear, rot
    area_val = calculate_area(df['E'].values, df['N'].values)

    # MAP DISPLAY
    st.subheader("🛰️ Interactive Google Satellite Overlay")
    
    m = folium.Map(
        location=[df['lat'].mean(), df['lon'].mean()], 
        zoom_start=20, 
        max_zoom=22,
        control_scale=True
    )

    # ADD GOOGLE MAP LAYER ELEMENT (THE BUTTON)
    google_sat = folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
        attr='Google', name='Google Hybrid (Satellite)', max_zoom=22, overlay=False
    ).add_to(m)

    google_terrain = folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}', 
        attr='Google', name='Google Terrain', max_zoom=22, overlay=False
    ).add_to(m)

    # Boundary
    poly_pts = [[row['lat'], row['lon']] for _, row in df.iterrows()]
    folium.Polygon(locations=poly_pts, color="#FBFF00", weight=4, fill=True, fill_opacity=0.15).add_to(m)

    # Station Marks & Labels
    for i, row in df.iterrows():
        # Hover coordinate feature
        folium.CircleMarker(
            location=[row['lat'], row['lon']], 
            radius=marker_rad, color="#FF0000", fill=True, fill_color="#FF0000",
            tooltip=f"Coordinate: E {row['E']:.3f}, N {row['N']:.3f}"
        ).add_to(m)
        
        if show_labels:
            # Station Number
            folium.Marker([row['lat'], row['lon']],
                icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:white; font-weight:bold; text-shadow:3px 3px black; width:100px;">{int(row["STN"])}</div>')
            ).add_to(m)
            
            # Kemas Aligned Dimensions
            next_p = df.iloc[(i+1)%len(df)]
            m_lat, m_lon = (row['lat']+next_p['lat'])/2, (row['lon']+next_p['lon'])/2
            folium.Marker([m_lat, m_lon],
                icon=folium.DivIcon(html=f"""
                    <div style="transform: rotate({row['Rotation']}deg); 
                                font-size:{dim_size}pt; color:#38bdf8; font-weight:bold; 
                                background:rgba(0,0,0,0.8); padding:5px; border-radius:5px;
                                white-space:nowrap; border: 1px solid #38bdf8; text-align:center;">
                        {row['Bearing']} | {row['Distance']}m
                    </div>""")
            ).add_to(m)

    # ADD LAYER CONTROL ELEMENT TO MAP
    folium.LayerControl(position='topright', collapsed=False).add_to(m)

    folium_static(m, width=1200, height=700)
    
    # DATA SUMMARY
    c1, c2 = st.columns([1, 1])
    c1.metric("LOT AREA", f"{area_val:.3f} m²")
    c2.dataframe(df[['STN', 'Distance', 'Bearing']], hide_index=True, use_container_width=True)

else:
    st.info("Awaiting Survey Data... Please upload your point.csv file.")