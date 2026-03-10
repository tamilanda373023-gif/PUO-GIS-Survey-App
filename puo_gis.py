import streamlit as st
import pandas as pd
import folium
from folium.plugins import MiniMap, MeasureControl
from streamlit_folium import folium_static
import numpy as np
import os
import base64
import json
from pyproj import Transformer

# --- 1. SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "area_calculated" not in st.session_state:
    st.session_state.area_calculated = False

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- 3. UI CSS (Precision UI) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(-45deg, #0f172a, #1e293b, #0b1120, #1e1b4b);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: white;
    }
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .login-card {
        background: rgba(255, 255, 255, 0.07);
        backdrop-filter: blur(20px);
        padding: 40px;
        border-radius: 30px;
        border: 2px solid rgba(56, 189, 248, 0.3);
        text-align: center;
        width: 100%;
        max-width: 600px;
        margin: 50px auto;
        display: block;
    }

    .login-card img {
        max-width: 100% !important;
        height: auto !important;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    
    .hero-container {
        display: flex; align-items: center; padding: 30px;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 25px;
    }
    .middle-system-title {
        color: #FFFFFF !important; font-size: 50px; font-weight: 900;
        text-transform: uppercase; margin: 0;
        text-shadow: 0 0 15px rgba(56, 189, 248, 0.7);
    }
    .surveyor-name { 
        color: #38bdf8 !important; font-size: 22px; font-weight: 600; 
        background: rgba(56, 189, 248, 0.1); padding: 5px 15px; border-radius: 10px;
    }
    .leaflet-tooltip {
        background-color: white !important;
        color: black !important;
        font-weight: bold !important;
        border: 1px solid black !important;
        transform: rotate(0deg) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. LOGO LOGIC ---
logo_file = "logo_puo.png"
if os.path.exists(logo_file):
    with open(logo_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
        logo_data = f'data:image/png;base64,{encoded}'
else:
    logo_data = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Logo_PUO.png/600px-Logo_PUO.png"

# --- 5. LOGIN GATE ---
if not st.session_state.logged_in:
    _, center_col, _ = st.columns([0.2, 1, 0.2])
    with center_col:
        st.markdown(f'''
            <div class="login-card">
                <img src="{logo_data}">
                <h1 style="color:#38bdf8; font-size:40px; margin-top:20px;">CORE GEOMATIK SYSTEM</h1>
                <p style="color:#94a3b8; font-size:18px;">Authorized Admin Access Only</p>
            </div>
        ''', unsafe_allow_html=True)
        
        user_input = st.text_input("Username", placeholder="Admin")
        pass_input = st.text_input("Security Key", type="password", placeholder="12345678")
        
        if st.button("🚀 INITIATE SYSTEM", use_container_width=True):
            if user_input == "Admin" and pass_input == "12345678":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid Credentials")
    st.stop()

# --- 6. MAIN HEADER ---
st.markdown(f"""
    <div class="hero-container">
        <div style="display: flex; align-items: center; flex: 1.5;">
            <img src="{logo_data}" width="100">
            <div style="color:white; font-size:24px; font-weight:800; margin-left:15px; text-transform:uppercase; line-height:1.1;">POLITEKNIK<br>UNGKU OMAR</div>
        </div>
        <div style="flex: 2; text-align: center;">
            <p class="middle-system-title">SISTEM SURVEY LOT PUO</p>
            <p style="margin-top: 10px;"><span class="surveyor-name">Lead Surveyor: Tamilkumaran</span></p>
        </div>
        <div style="flex: 1; text-align: right;">
            <p style="color: #94a3b8; font-size: 14px;">UNIT GEOMATIK<br>JABATAN KEJURUTERAAN AWAM</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 7. DASHBOARD CORE ---
def get_survey_math_dms(df):
    distances, bearings = [], []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        next_idx = (i + 1) % len(df)
        p2 = (df.iloc[next_idx]['E'], df.iloc[next_idx]['N'])
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        angle_deg = np.degrees(np.arctan2(p2[0]-p1[0], p2[1]-p1[1])) % 360
        deg, min_part = int(angle_deg), (angle_deg - int(angle_deg)) * 60
        minutes, seconds = int(min_part), int((min_part - int(min_part)) * 60)
        distances.append(round(dist, 3))
        bearings.append(f"{deg}° {minutes}' {seconds}\"")
    return distances, bearings

uploaded_file = st.file_uploader("📂 Import Survey Dataset (point.csv)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    transformer = Transformer.from_crs("epsg:4390", "epsg:4326", always_xy=True)
    df['lon'], df['lat'] = transformer.transform(df['E'].values, df['N'].values)
    df['Distance'], df['Bearing'] = get_survey_math_dms(df)
    coords = [[row['lon'], row['lat']] for _, row in df.iterrows()]; coords.append(coords[0])
    geojson_dict = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]}}]}

    with st.sidebar:
        st.markdown("### 📊 Control Center")
        map_type = st.radio("Basemap Layer", ["Satellite Hybrid", "Satellite", "Street Map"])
        label_mode = st.toggle("Show Labels", value=True)
        st.divider()
        st.markdown("### 🔍 Point Lookup")
        selected_stn = st.selectbox("Select Station ID", df['STN'].unique())
        stn_info = df[df['STN'] == selected_stn].iloc[0]
        st.info(f"STN {selected_stn}\n\nE: {stn_info['E']:.3f}\n\nN: {stn_info['N']:.3f}")
        st.divider()
        st.download_button("🌍 Download GeoJSON", data=json.dumps(geojson_dict), file_name="puo_survey.geojson", use_container_width=True)
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

    m1, m2 = st.columns(2)
    with m1: st.metric("Total Stations", len(df))
    with m2: 
        if st.button("📐 CALCULATE AREA", use_container_width=True):
            st.session_state.area_calculated = True

    if st.session_state.area_calculated:
        area_val = 0.5 * np.abs(np.dot(df['E'], np.roll(df['N'], 1)) - np.dot(df['N'], np.roll(df['E'], 1)))
        st.markdown(f'<div style="background:rgba(56,189,248,0.15); padding:20px; border-radius:15px; border:1px solid #38bdf8; text-align:center;"><h2 style="color:#38bdf8; margin:0;">CALCULATED AREA: {area_val:.3f} m²</h2></div>', unsafe_allow_html=True)

    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19, tiles=None)
    if map_type == "Satellite Hybrid": folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', max_zoom=22).add_to(m)
    elif map_type == "Satellite": folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', max_zoom=22).add_to(m)
    else: folium.TileLayer('OpenStreetMap').add_to(m)

    folium.plugins.MiniMap().add_to(m)
    folium.plugins.MeasureControl(position='topleft').add_to(m)
    
    # White Polygon Boundary
    folium.Polygon(locations=[[r['lat'], r['lon']] for _, r in df.iterrows()], color="white", weight=3, fill=True, fill_opacity=0.1).add_to(m)

    for i, row in df.iterrows():
        # PROFESSIONAL HOVER: Displays E and N coordinates
        hover_text = f"STN: {int(row['STN'])} | E: {row['E']:.3f}, N: {row['N']:.3f}"
        folium.CircleMarker(
            location=[row['lat'], row['lon']], 
            radius=6, 
            color="red", 
            fill=True,
            tooltip=folium.Tooltip(hover_text, sticky=True)
        ).add_to(m)

        if label_mode:
            folium.Marker([row['lat'], row['lon']], icon=folium.DivIcon(html=f'<div style="font-size:10pt; color:white; font-weight:bold; text-shadow:1px 1px 2px black;">{int(row["STN"])}</div>')).add_to(m)
            next_p = df.iloc[(i + 1) % len(df)]
            mid_lat, mid_lon = (row['lat'] + next_p['lat']) / 2, (row['lon'] + next_p['lon']) / 2
            folium.Marker([mid_lat, mid_lon], icon=folium.DivIcon(html='<div style="width:1px; height:1px;"></div>')).add_child(folium.Tooltip(
                f"{row['Bearing']}<br>{row['Distance']}m", permanent=True, direction='center',
                style="font-size: 8pt; background-color: white; color: black; border: 1px solid black; font-weight: bold; border-radius: 4px;"
            )).add_to(m)

    m.fit_bounds([[df['lat'].min(), df['lon'].min()], [df['lat'].max(), df['lon'].max()]])
    folium_static(m, width=1300, height=650)
    st.dataframe(df[['STN', 'E', 'N', 'Distance', 'Bearing']], use_container_width=True)
else:
    st.info("System Ready. Please upload your survey points.")