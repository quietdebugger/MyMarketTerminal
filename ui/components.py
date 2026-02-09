import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /* Modern Bloomberg Professional Palette */
        :root {
            --bg-main: #000000;
            --bg-card: #111111;
            --accent: #00d4ff;
            --text-main: #e0e0e0;
            --success: #00ff00;
            --error: #ff4b4b;
        }

        .stApp { background-color: var(--bg-main); color: var(--text-main); }
        
        /* Sidebar Polish */
        [data-testid="stSidebar"] { 
            background-color: #050505; 
            border-right: 1px solid #222;
            width: 260px !important;
        }
        
        /* Glassmorphism Cards */
        .terminal-card {
            background: rgba(20, 20, 20, 0.8);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 1.2rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            transition: 0.3s;
        }
        .terminal-card:hover { border-color: var(--accent); }

        /* Metric Typography */
        .metric-label { color: #888; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
        .metric-value { color: var(--text-main); font-size: 1.6rem; font-weight: 800; font-family: 'Inter', sans-serif; }
        
        /* Responsive Mobile Columns */
        @media (max-width: 600px) {
            [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; margin-bottom: 10px; }
            .metric-value { font-size: 1.3rem; }
        }
        
        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 10px; }
        .stTabs [data-baseweb="tab"] { 
            background-color: #111; border-radius: 5px; padding: 10px 20px; color: #888;
        }
        .stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom: 2px solid var(--accent) !important; }
        </style>
    """, unsafe_allow_html=True)

def render_metric_card(label, value, delta=None, color="blue"):
    color_map = {"blue": "#00d4ff", "green": "#00ff00", "red": "#ff4b4b", "orange": "#ffaa00"}
    d_html = f"<div style='color: {'#00ff00' if '+' in str(delta) else '#ff4b4b'}; font-size: 0.85rem;'>{delta}</div>" if delta else ""
    
    st.markdown(f"""
        <div class="terminal-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {color_map.get(color, 'white')}">{value}</div>
            {d_html}
        </div>
    """, unsafe_allow_html=True)
