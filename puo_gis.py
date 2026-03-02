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
    """Calculates polygon area using the Shoelace formula."""
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- PAGE CONFIG ---
st.set_page_config(page_title="PUO GIS - Professional Edition", layout="wide")

# --- CLASSY STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .header-container {
        background-color: #0f172a; 
        padding: 40px; 
        border-radius: 0px 0px 20px 20px; 
        margin-bottom: 30px;
        border-bottom: 5px solid #38bdf8;
    }
    .header-title { color: #ffffff !important; font-size: 48px; font-weight: bold; margin: 0; }
    .header-subtitle { color: #94a3b8 !important; font-size: 22px; margin: 5px 0 0 0; }
    
    /* Process Button */
    div.stButton > button {
        background-color: #1e293b;
        color: white;
        font-weight: bold;
        font-size: 18px;
        height: 4em;
        width: 100%;
        border-radius: 12px;
        border: 2px solid #38bdf8;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TASK 1: BRANDING & HEADER ---
st.markdown('<div class="header-container">', unsafe_allow_html=True)
col_logo, col_title = st.columns([2.5, 3])

with col_logo:
    if os.path.exists("logo_puo.png"):
        st.image("logo_puo.png", width=450)
    else:
        st.error("Missing 'logo_puo.png'")

with col_title:
    st.write("##") 
    st.markdown('<p class="header-title">POLITEKNIK UNGKU OMAR</p>', unsafe_allow_html=True)
    st.markdown('<p class="header-subtitle">Department of Civil Engineering | GIS Surveying App</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- SIDEBAR (Task 3 & 4 Controls) ---
st.sidebar.title("⚙️ Map Settings")
st.sidebar.markdown("---")
show_satellite = st.sidebar.checkbox("🛰️ Open Satellite Layer (On/Off)", value=True)
st.sidebar.markdown("---")
st.sidebar.title("🏷️ Label Settings")
show_stn_labels = st.sidebar.checkbox("Display Station Labels (STN)", value=True)
show_area_label = st.sidebar.checkbox("Display Area Label", value=True)

# --- FILE UPLOADER ---
st.subheader("📂 1. Data Input")
uploaded_file = st.file_uploader("Upload Survey CSV file", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file).sort_values(by='STN')
    
    st.write("---")
    st.subheader("⚙️ 2. Processing")
    generate_report = st.button("🚀 CLICK HERE TO CALCULATE AREA & GENERATE REPORT")

    if generate_report:
        # DATA PROCESSING
        x, y = df['E'].values, df['N'].values
        area_val = calculate_area(x, y)
        
        # --- RESULTS SECTION ---
        st.divider()
        st.markdown("<h2 style='text-align:center; color:#0f172a;'>📊 SURVEY ANALYSIS REPORT</h2>", unsafe_allow_html=True)
        
        col_res, col_tab = st.columns([1, 2])
        with col_res:
            st.metric("TOTAL CALCULATED AREA", f"{area_val:.3f} m²")
            # TASK 2: EXPORT
            coords = [[float(row['E']), float(row['N'])] for _, row in df.iterrows()]
            coords.append(coords[0]) 
            geojson = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"Area": area_val}, "geometry": {"type": "Polygon", "coordinates": [coords]}}]}
            st.download_button("📥 Download GeoJSON for QGIS", json.dumps(geojson), "survey_report.geojson", use_container_width=True)

        with col_tab:
            st.write("### 📋 Survey Coordinate Table")
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()

        # --- VISUALIZATION ---
        col_plot, col_sat = st.columns(2)

        with col_plot:
            st.write("### 📐 Geometric Plot (Task 4)")
            fig, ax = plt.subplots(figsize=(10, 10))
            x_p, y_p = np.append(x, x[0]), np.append(y, y[0])
            
            ax.plot(x_p, y_p, color='#0f172a', linewidth=3, zorder=2)
            ax.fill(x_p, y_p, color='#bae6fd', alpha=0.4, zorder=1)
            ax.scatter(x, y, color='#ef4444', s=120, edgecolors='black', zorder=3)
            
            # AREA LABEL CONTROL
            if show_area_label:
                ax.text(np.mean(x), np.mean(y), f"AREA:\n{area_val:.3f} m²", 
                        ha='center', va='center', fontsize=18, fontweight='bold',
                        color='black', 
                        bbox=dict(boxstyle="round,pad=0.8", facecolor="white", edgecolor="black", linewidth=2.5),
                        zorder=5)
            
            # STATION LABEL CONTROL
            if show_stn_labels:
                for i, row in df.iterrows():
                    ax.annotate(f"STN {int(row['STN'])}", (row['E'], row['N']), 
                                xytext=(15, 15), textcoords="offset points", 
                                fontsize=12, fontweight='bold',
                                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8),
                                zorder=6)
            
            ax.set_aspect('equal')
            ax.grid(True, linestyle='--', alpha=0.3)
            st.pyplot(fig)

        with col_sat:
            st.write("### 🛰️ Satellite Map (Task 3)")
            m = folium.Map(location=[df['N'].mean() * 0.00001, df['E'].mean() * 0.00001], zoom_start=2)
            # SATELLITE LAYER CONTROL
            if show_satellite:
                folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite').add_to(m)
            folium_static(m, width=580)
else:
    st.info("👋 Welcome! Please upload your Survey CSV file above to begin.")