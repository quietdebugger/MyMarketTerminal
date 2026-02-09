"""
UI Components & Styling for Gemini Market Terminal
"""

import streamlit as st

def load_custom_css():
    st.markdown("""
        <style>
        /* Modern Dark Theme Enhancements */
        .stApp {
            background-color: #0e1117;
        }
        
        /* Metric Cards */
        .metric-card {
            background-color: #1e2329;
            border-radius: 10px;
            padding: 15px;
            border: 1px solid #2b3139;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: #4b5563;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #9ca3af;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #f3f4f6;
        }
        .metric-delta {
            font-size: 0.9rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .delta-pos { color: #10b981; }
        .delta-neg { color: #ef4444; }
        .delta-neu { color: #9ca3af; }

        /* Ticker Tape */
        .ticker-tape {
            display: flex;
            gap: 20px;
            overflow-x: auto;
            padding: 10px 0;
            margin-bottom: 20px;
            background: #161b22;
            border-bottom: 1px solid #30363d;
            white-space: nowrap;
        }
        .ticker-item {
            display: inline-flex;
            flex-direction: column;
            padding: 0 15px;
            border-right: 1px solid #30363d;
        }
        
        /* Tables */
        .dataframe {
            font-size: 0.9rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

def render_metric_card(label: str, value: str, delta: str = None, is_positive: bool = None, help_text: str = None):
    """
    Renders a styled metric card.
    """
    delta_html = ""
    if delta:
        if is_positive is True:
            color_class = "delta-pos"
            icon = "▲"
        elif is_positive is False:
            color_class = "delta-neg"
            icon = "▼"
        else:
            color_class = "delta-neu"
            icon = "•"
        delta_html = f'<div class="metric-delta {color_class}">{icon} {delta}</div>'

    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)

def render_ticker_tape(metrics: list):
    """
    Renders a horizontal ticker tape.
    metrics: list of dicts with keys: label, value, delta, is_positive
    """
    items_html = ""
    for m in metrics:
        color = "#10b981" if m.get('is_positive') else "#ef4444"
        if m.get('is_positive') is None: color = "#9ca3af"
        
        items_html += f"""
            <div class="ticker-item">
                <span style="font-size: 0.8rem; color: #9ca3af;">{m['label']}</span>
                <div>
                    <span style="font-weight: bold; color: #e5e7eb;">{m['value']}</span>
                    <span style="font-size: 0.8rem; color: {color}; margin-left: 5px;">{m['delta']}</span>
                </div>
            </div>
        """
    
    st.markdown(f"""
        <div class="ticker-tape">
            {items_html}
        </div>
    """, unsafe_allow_html=True)
