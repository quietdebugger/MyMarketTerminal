import streamlit as st
import importlib
import pkgutil
import inspect
import sys
import os

# Add paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.plugin_interface import MarketTerminalPlugin
from core.state_manager import StateManager
from services.data_service import DataService
from ui.components import apply_custom_css, render_metric_card

# --- 1. INITIALIZATION ---
st.set_page_config(
    page_title="Market Terminal Pro",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PWA & NATIVE APP INJECTION ---
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#000000">
    <style>
        /* Modern Bloomberg Scrollbars */
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }
        ::-webkit-scrollbar-track { background: #000; }
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()
StateManager.init()

# --- HEARTBEAT / AUTO-REFRESH ---
if st.session_state.get('user_settings', {}).get('refresh_rate', 0) > 0:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=st.session_state['user_settings']['refresh_rate'] * 1000, key="heartbeat")
    except ImportError:
        st.warning("Autorefresh library missing. Manual refresh required.")

# --- 2. PLUGIN LOADING ---
@st.cache_resource
def load_plugins_cached():
    """Cache plugin loading to speed up re-runs."""
    plugins = {}
    plugin_path = os.path.join(os.path.dirname(__file__), "plugins")
    for _, name, _ in pkgutil.iter_modules([plugin_path]):
        try:
            module = importlib.import_module(f"plugins.{name}")
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if (inspect.isclass(attribute) and issubclass(attribute, MarketTerminalPlugin) and attribute is not MarketTerminalPlugin):
                    instance = attribute()
                    plugins[instance.name] = instance
        except: pass
    return plugins

# --- 3. UI LAYOUT ---
def main():
    # A. Top Bar (Breadth)
    breadth = DataService.get_market_breadth()
    if breadth:
        cols = st.columns(4)
        indices = {"^NSEI": "NIFTY", "^NSEBANK": "BANKNIFTY", "RELIANCE.NS": "RELIANCE", "BTC-USD": "BITCOIN"}
        for i, (sym, name) in enumerate(indices.items()):
            if sym in breadth:
                d = breadth[sym]
                cols[i].metric(name, f"{d['price']:,.0f}", f"{d['change']:+.2f}%")
    
    st.markdown("---")

    # B. Command Line (Debounced via Form)
    c1, c2 = st.columns([1, 3])
    with c1:
        with st.form("ticker_search"):
            new_ticker = st.text_input("QUERY TICKER", value=StateManager.get('active_ticker'))
            submitted = st.form_submit_button("SEARCH")
            if submitted:
                StateManager.set_active_ticker(new_ticker)
                st.rerun()
    
    with c2:
        # Display context about active ticker
        st.markdown(f"### ACTIVE: <span style='color:#00d4ff'>{StateManager.get('active_ticker')}</span>", unsafe_allow_html=True)

    # C. Sidebar Navigation
    plugins = load_plugins_cached()
    
    st.sidebar.title("NAVIGATOR")
    
    cats = ["Intelligence", "Research", "Trading"]
    for cat in cats:
        st.sidebar.caption(f"{cat.upper()}")
        for name, p in plugins.items():
            if p.category == cat:
                # Use session state to track active plugin to avoid reload issues
                if st.sidebar.button(f"{p.icon}  {p.name}", key=name, use_container_width=True):
                    StateManager.set('active_plugin', name)
                    st.rerun()

    # D. Main Stage (Lazy Loading)
    active = StateManager.get('active_plugin')
    if active in plugins:
        plugin = plugins[active]
        try:
            # Pass the Global Ticker to the plugin
            plugin.render(StateManager.get('active_ticker'))
        except Exception as e:
            st.error(f"Plugin Error: {e}")

if __name__ == "__main__":
    main()
