import streamlit as st

def apply_custom_css():
    """Bloomberg Professional Mobile-Optimized Theme"""
    st.markdown("""
        <style>
        /* Global App Dark Theme */
        .stApp { background-color: #000000; color: #e0e0e0; }
        
        /* App Bar Styling */
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
        
        /* Mobile-Ready Metric Cards */
        .metric-card {
            background-color: #111;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #222;
            margin-bottom: 8px;
            text-align: center;
        }
        
        /* Command Line - Console Style */
        .stTextInput input {
            background-color: #0a0a0a !important;
            color: #00ff00 !important;
            border: 1px solid #00ff00 !important;
            border-radius: 4px !important;
            font-family: 'Consolas', monospace !important;
            font-size: 1.1rem !important;
        }
        
        /* Sidebar - Hidden on mobile until swiped */
        [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #111; }
        
        /* Touch-Friendly Buttons */
        .stButton button {
            height: 3rem;
            border-radius: 8px;
            font-weight: 600;
            background-color: #1a1a1a;
            border: 1px solid #333;
        }
        
        /* Stack columns on small screens */
        @media (max-width: 600px) {
            [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
        }
        </style>
    """, unsafe_allow_html=True)

def render_metric_card(label, value, delta=None, color="blue"):
    color_map = {"blue": "#00d4ff", "green": "#00ff00", "red": "#ff4b4b", "orange": "#ffaa00"}
    delta_html = ""
    if delta:
        d_color = "#00ff00" if "+" in str(delta) else "#ff4b4b"
        delta_html = f"<div style='color: {d_color}; font-size: 0.8rem;'>{delta}</div>"
    
    st.markdown(f"""
        <div class="metric-card">
            <div style='color: #888; font-size: 0.7rem; text-transform: uppercase;'>{label}</div>
            <div style='color: {color_map.get(color, 'white')}; font-size: 1.4rem; font-weight: bold;'>{value}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)