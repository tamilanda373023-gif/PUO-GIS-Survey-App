import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import numpy as np
import os
from pyproj import Transformer

# --- 1. SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "area_calculated" not in st.session_state:
    st.session_state.area_calculated = False

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- 3. CSS (Glowing Header & Great Look) ---
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
    .hero-container {
        display: flex; align-items: center; padding: 30px;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 25px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }
    .poli-name-text { 
        color: #FFFFFF !important; font-size: 24px; font-weight: 800; 
        margin-left: 15px; text-transform: uppercase; line-height: 1.1;
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
    .calc-box {
        background: rgba(56, 189, 248, 0.15); padding: 20px;
        border-radius: 15px; border: 1px solid #38bdf8; text-align: center;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. LOGIN GATE ---
if not st.session_state.logged_in:
    cols = st.columns([1, 1.5, 1])
    with cols[1]:
        st.markdown('<div style="background: rgba(30, 41, 59, 0.9); padding: 40px; border-radius: 20px; border: 2px solid #38bdf8; text-align: center; margin-top: 100px;">', unsafe_allow_html=True)
        st.title("🔐 ACCESS PORTAL")
        password = st.text_input("Enter Password", type="password")
        if st.button("Login", use_container_width=True):
            if password == "12345678":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid Key")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. HEADER (LOGO FIX & NAME) ---
logo_file = "logo_puo.png"
logo_html = ""

# Checking if the file exists in your directory
if os.path.exists(logo_file):
    import base64
    with open(logo_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{encoded}" width="90">'
else:
    # Fallback to web link if file is not found
    logo_html = '<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Logo_PUO.png/200px-Logo_PUO.png" width="90">'

st.markdown(f"""
    <div class="hero-container">
        <div style="display: flex; align-items: center; flex: 1.5;">
            {logo_html}
            <div class="poli-name-text">POLITEKNIK<br>UNGKU OMAR</div>
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

# --- 6. DATA FUNCTIONS ---
def get_survey_math(df):
    distances, bearings, angles = [], [], []
    for i in range(len(df)):
        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
        next_idx = (i + 1) % len(df)
        p2 = (df.iloc[next_idx]['E'], df.iloc[next_idx]['N'])
        dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        dz, dn = p2[0] - p1[0], p2[1] - p1[1] 
        angle_deg = np.degrees(np.arctan2(dz, dn)) % 360
        rotation = 90 - angle_deg
        if rotation > 90: rotation -= 180
        if rotation < -90: rotation += 180
        distances.append(round(dist, 3))
        bearings.append(f"{int(angle_deg)}° {int((angle_deg%1)*60)}'")
        angles.append(rotation)
    return distances, bearings, angles

# --- 7. MAIN APP ---
uploaded_file = st.file_uploader("📂 Upload point.csv", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    transformer = Transformer.from_crs("epsg:4390", "epsg:4326", always_xy=True)
    df['lon'], df['lat'] = transformer.transform(df['E'].values, df['N'].values)
    dist, bear, rot = get_survey_math(df)
    df['Distance'], df['Bearing'], df['Rotation'] = dist, bear, rot

    # --- SIDEBAR (RESTORED FONT ADJUSTMENTS) ---
    with st.sidebar:
        st.header("🕹️ DISPLAY CONTROLLER")
        sat_mode = st.toggle("🛰️ Google Satellite", value=True)
        label_mode = st.toggle("📍 Show Labels", value=True)
        st.markdown("---")
        # THESE ARE THE ADJUSTMENT INDICATIONS YOU WANTED:
        stn_size = st.slider("Station ID Size", 8, 30, 15)
        dim_size = st.slider("Bearing/Distance Size", 6, 20, 11)
        marker_rad = st.slider("Marker Point Size", 2, 20, 8)
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # --- CALCULATION BUTTON ---
    if st.button("🚀 CALCULATE LOT AREA", use_container_width=True):
        st.session_state.area_calculated = True

    if st.session_state.area_calculated:
        area_val = 0.5 * np.abs(np.dot(df['E'], np.roll(df['N'], 1)) - np.dot(df['N'], np.roll(df['E'], 1)))
        st.markdown(f'<div class="calc-box"><h2 style="color:#38bdf8;">LOT AREA: {area_val:.3f} m²</h2></div>', unsafe_allow_html=True)

    # --- MAP ---
    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19, tiles=None)
    if sat_mode:
        folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', max_zoom=22).add_to(m)
    else:
        folium.TileLayer('cartodbpositron').add_to(m)

    folium.Polygon(locations=[[r['lat'], r['lon']] for _, r in df.iterrows()], color="#FBFF00", weight=4, fill=True, fill_opacity=0.15).add_to(m)

    for i, row in df.iterrows():
        folium.CircleMarker(location=[row['lat'], row['lon']], radius=marker_rad, color="red", fill=True).add_to(m)
        if label_mode:
            folium.Marker([row['lat'], row['lon']], icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:white; font-weight:bold; text-shadow:2px 2px black;">{int(row["STN"])}</div>')).add_to(m)
            next_p = df.iloc[(i + 1) % len(df)]
            m_lat, m_lon = (row['lat'] + next_p['lat']) / 2, (row['lon'] + next_p['lon']) / 2
            folium.Marker([m_lat, m_lon], icon=folium.DivIcon(html=f"""<div style="transform: rotate({row['Rotation']}deg) translateY(-12px); font-size:{dim_size}pt; color:#38bdf8; font-weight:bold; text-shadow: 1px 1px 2px black; white-space:nowrap; text-align:center;">{row['Bearing']} <br> {row['Distance']}m</div>""")).add_to(m)

    folium_static(m, width=1300, height=650)
    st.dataframe(df[['STN', 'Distance', 'Bearing']], use_container_width=True)

else:
    st.info("System Ready. Please upload your 'point.csv' file.")