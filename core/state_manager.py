import streamlit as st
from typing import Any

class StateManager:
    """
    Singleton-like wrapper for Streamlit Session State.
    Prevents 'reload amnesia' and manages global context.
    """
    
    DEFAULTS = {
        'active_ticker': 'TCS.NS',
        'active_plugin': 'Portfolio Pro',
        'portfolio_cache': None,
        'market_breadth_cache': None,
        'last_refresh': 0,
        'user_settings': {'theme': 'dark', 'refresh_rate': 60}
    }

    @staticmethod
    def init():
        for key, value in StateManager.DEFAULTS.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def get(key: str) -> Any:
        return st.session_state.get(key)

    @staticmethod
    def set(key: str, value: Any):
        st.session_state[key] = value

    @staticmethod
    def get_active_ticker():
        return st.session_state.get('active_ticker', 'TCS.NS')

    @staticmethod
    def set_active_ticker(ticker: str):
        # Basic normalization
        ticker = ticker.upper().strip()
        if not ticker.endswith(".NS") and not ticker.startswith("^") and "USD" not in ticker:
            ticker += ".NS"
        st.session_state['active_ticker'] = ticker
