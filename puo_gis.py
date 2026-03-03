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
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS Final", layout="wide")

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
    /* BRIGHT COLOUR FOR REPORT TITLE */
    .report-title { color: #22d3ee !important; text-align: center; font-weight: bold; font-size: 35px; }
    
    div.stButton > button {
        background-color: #38bdf8;
        color: #0f172a;
        font-weight: bold;
        height: 3em;
        width: 100%;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR SETTINGS (Always Visible) ---
st.sidebar.title("⚙️ Map Settings")
show_satellite = st.sidebar.checkbox("🛰️ Open Satellite Layer (On/Off)", value=True)
st.sidebar.markdown("---")
st.sidebar.title("🏷️ Label Settings")
show_stn_labels = st.sidebar.checkbox("Display Station Labels (STN)", value=True)
show_area_label = st.sidebar.checkbox("Display Area Label", value=True)

# --- TASK 1: HEADER ---
st.markdown('<div class="header-container">', unsafe_allow_html=True)
col_logo, col_title = st.columns([2.5, 3])
with col_logo:
    if os.path.exists("logo_puo.png"):
        st.image("logo_puo.png", width=450)
with col_title:
    st.write("##") 
    st.markdown('<p class="header-title">POLITEKNIK UNGKU OMAR</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8;">Civil Engineering GIS Dashboard</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("📂 Upload Survey CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    
    # Session State to keep results visible
    if 'processed' not in st.session_state:
        st.session_state.processed = False

    if st.button("🚀 GENERATE SURVEY ANALYSIS"):
        st.session_state.processed = True

    if st.session_state.processed:
        x, y = df['E'].values, df['N'].values
        area_val = calculate_area(x, y)
        
        # --- TASK 4: BRIGHT REPORT TITLE ---
        st.divider()
        st.markdown('<p class="report-title">📊 SURVEY ANALYSIS REPORT</p>', unsafe_allow_html=True)
        
        col_res, col_tab = st.columns([1, 2])
        with col_res:
            st.metric("TOTAL AREA", f"{area_val:.3f} m²")
            coords = [[float(row['E']), float(row['N'])] for _, row in df.iterrows()]
            coords.append(coords[0]) 
            geojson = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]}}]}
            st.download_button("📥 Download GeoJSON", json.dumps(geojson), "puo_report.geojson")

        with col_tab:
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()

        # --- VISUALS ---
        col_plot, col_map = st.columns(2)

        with col_plot:
            st.write("### 📐 Geometric Plot")
            fig, ax = plt.subplots(figsize=(8, 8))
            x_p, y_p = np.append(x, x[0]), np.append(y, y[0])
            ax.plot(x_p, y_p, color='black', linewidth=2)
            ax.fill(x_p, y_p, color='#38bdf8', alpha=0.3)
            
            if show_area_label:
                ax.text(np.mean(x), np.mean(y), f"AREA:\n{area_val:.3f} m²", 
                        ha='center', va='center', fontsize=12, fontweight='bold',
                        bbox=dict(boxstyle="round", facecolor="white", edgecolor="black"))
            
            if show_stn_labels:
                for i, row in df.iterrows():
                    ax.annotate(f"STN {int(row['STN'])}", (row['E'], row['N']), fontweight='bold')
            st.pyplot(fig)

        with col_map:
            st.write("### 🛰️ Satellite Map")
            # Using simple scaling for visual context
            m = folium.Map(location=[df['N'].mean() * 0.00001, df['E'].mean() * 0.00001], zoom_start=2)
            if show_satellite:
                folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google').add_to(m)
            folium_static(m, width=500)