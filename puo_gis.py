import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import numpy as np
import base64
from pyproj import Transformer

# --- 1. SESSION STATE FOR LOGIN (Must be at the top) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS PRO | Tamilkumaran", layout="wide")

# --- 3. ADVANCED STYLING (The "Great" Look) ---
st.markdown("""
    <style>
    /* Animated Gradient Background */
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

    /* Glassmorphism Header */
    .hero-container {
        display: flex; align-items: center; 
        padding: 40px;
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 30px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
    }

    .poli-name-text { 
        color: #FFFFFF !important; font-size: 28px; font-weight: 800; 
        margin-left: 20px; text-transform: uppercase; letter-spacing: 2px;
    }

    /* Glowing Center Title */
    .middle-system-title {
        color: #FFFFFF !important; font-size: 60px; font-weight: 900;
        text-transform: uppercase; margin: 0;
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.6);
        letter-spacing: 4px;
    }

    .surveyor-credit { color: #38bdf8 !important; font-size: 20px; font-weight: 500; }

    /* Login Box Styling */
    .login-card {
        background: rgba(30, 41, 59, 0.8);
        padding: 50px; border-radius: 20px;
        border: 2px solid #38bdf8;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.2);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. LOGIN GATE ---
if not st.session_state.logged_in:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Logo_PUO.png/200px-Logo_PUO.png", width=120)
        st.header("SISTEM SURVEY LOT PUO")
        st.subheader("Authentication Required")
        password = st.text_input("Enter Access Key", type="password")
        if st.button("Unlock Dashboard", use_container_width=True):
            if password == "12345678":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Access Denied: Invalid Password")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. DATA PROCESSING FUNCTIONS ---
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

def transform_coords_johor(e, n):
    transformer = Transformer.from_crs("epsg:4390", "epsg:4326", always_xy=True)
    lon, lat = transformer.transform(e, n)
    return lat, lon

# --- 6. HEADER (After Login) ---
# Trying 3 ways to find your logo: Local file, GitHub Raw, then Wikipedia as backup.
github_raw = "https://raw.githubusercontent.com/TamilkumaranPUO/YOUR_REPO/main/logo_puo.png"

st.markdown(f"""
    <div class="hero-container">
        <div style="display: flex; align-items: center; flex: 1.5;">
            <img src="{github_raw}" width="100" onerror="this.src='https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Logo_PUO.png/200px-Logo_PUO.png'">
            <p class="poli-name-text">POLITEKNIK UNGKU OMAR</p>
        </div>
        <div style="flex: 2; text-align: center;">
            <p class="middle-system-title">SISTEM SURVEY LOT PUO</p>
            <p class="surveyor-credit">Lead Surveyor: Tamilkumaran</p>
        </div>
        <div style="flex: 1; text-align: right;">
            <p style="color: #94a3b8;">Status: Secure Access</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 7. MAIN APP LOGIC ---
uploaded_file = st.file_uploader("📂 Import Survey Data (point.csv)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df['lat'], df['lon'] = transform_coords_johor(df['E'].values, df['N'].values)
    dist, bear, rot = get_survey_math(df)
    df['Distance'], df['Bearing'], df['Rotation'] = dist, bear, rot
    
    with st.sidebar:
        st.title("Settings")
        sat_mode = st.toggle("Satellite Imagery", value=True)
        label_mode = st.toggle("Show Lot Labels", value=True)
        st.divider()
        stn_size = st.slider("Station Text", 8, 30, 15)
        dim_size = st.slider("Survey Dimension Text", 6, 20, 11)
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19, tiles=None)
    if sat_mode:
        folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', max_zoom=22).add_to(m)
    else:
        folium.TileLayer('cartodbpositron').add_to(m)

    # Drawing Lot
    folium.Polygon(locations=[[r['lat'], r['lon']] for _, r in df.iterrows()], color="#FBFF00", weight=5, fill=True, fill_opacity=0.2).add_to(m)

    for i, row in df.iterrows():
        folium.CircleMarker(location=[row['lat'], row['lon']], radius=7, color="red", fill=True).add_to(m)
        if label_mode:
            folium.Marker([row['lat'], row['lon']], icon=folium.DivIcon(html=f'<div style="font-size:{stn_size}pt; color:white; font-weight:bold; text-shadow:2px 2px black;">{int(row["STN"])}</div>')).add_to(m)
            
            # Line Labels (Parallel and Sequential)
            next_p = df.iloc[(i + 1) % len(df)]
            m_lat, m_lon = (row['lat'] + next_p['lat']) / 2, (row['lon'] + next_p['lon']) / 2
            folium.Marker([m_lat, m_lon], icon=folium.DivIcon(html=f"""<div style="transform: rotate({row['Rotation']}deg) translateY(-12px); font-size:{dim_size}pt; color:#38bdf8; font-weight:bold; text-shadow: 1px 1px 2px black; white-space:nowrap; text-align:center;">{row['Bearing']} <br> {row['Distance']}m</div>""")).add_to(m)

    folium_static(m, width=1300, height=700)
    
    # Summary Cards
    st.metric("Total Lot Area", f"{0.5 * np.abs(np.dot(df['E'], np.roll(df['N'], 1)) - np.dot(df['N'], np.roll(df['E'], 1))):.3f} m²")
    st.dataframe(df[['STN', 'Distance', 'Bearing']], use_container_width=True)

else:
    st.info("👋 Welcome! Please upload your point.csv to begin the visualization.")