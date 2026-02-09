import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import json
from upstox_fo_complete import UpstoxAuth, UpstoxFOData

class DataService:
    
    @staticmethod
    def get_credentials():
        """
        Robust credential fetching: Local File -> Streamlit Secrets.
        """
        # Default redirect
        redirect_uri = "http://localhost:5600"
        
        # Try local first
        try:
            import api_config
            return {
                "api_key": api_config.UPSTOX_API_KEY,
                "api_secret": api_config.UPSTOX_API_SECRET,
                "redirect_uri": getattr(api_config, 'UPSTOX_REDIRECT_URI', redirect_uri)
            }
        except ImportError:
            # Fallback to Streamlit Cloud Secrets
            try:
                return {
                    "api_key": st.secrets["UPSTOX_API_KEY"],
                    "api_secret": st.secrets["UPSTOX_API_SECRET"],
                    "redirect_uri": st.secrets.get("UPSTOX_REDIRECT_URI", redirect_uri)
                }
            except Exception as e:
                return {"api_key": "", "api_secret": "", "redirect_uri": redirect_uri}

    @staticmethod
    @st.cache_data(ttl=300)
    def fetch_price_history(ticker: str, period="1y"):
        try:
            return yf.download(ticker, period=period, progress=False)
        except:
            return pd.DataFrame()

    @staticmethod
    def fetch_upstox_portfolio():
        """Fetch portfolio with string-based hashing to prevent hangs"""
        try:
            creds = DataService.get_credentials()
            if not creds["api_key"]: 
                return [], [], "API Key Missing"
            
            auth = UpstoxAuth(creds["api_key"], creds["api_secret"], creds["redirect_uri"])
            token = auth.get_access_token()
            
            if not token:
                st.session_state['upstox_auth_needed'] = True
                return [], [], "Auth Required"
            
            st.session_state['upstox_auth_needed'] = False
            
            # PASS STRING TOKEN, NOT OBJECT to avoid hashing hangs
            return DataService._fetch_portfolio_internal(token)
        except Exception as e:
            st.error(f"Portfolio Fetch Error: {e}")
            return [], [], str(e)

    @staticmethod
    @st.cache_data(ttl=60)
    def _fetch_portfolio_internal(access_token: str):
        """String token prevents hashing hangs in Streamlit Cloud"""
        fo_data = UpstoxFOData(access_token)
        holdings, h_err = fo_data.get_holdings()
        positions, p_err = fo_data.get_positions()
        
        # Combine errors if any
        error = None
        if h_err or p_err:
            error = f"Holdings: {h_err or 'OK'}, Positions: {p_err or 'OK'}"
            
        return holdings, positions, error

    @staticmethod
    def render_upstox_auth_ui():
        """Renders authentication UI in sidebar if token is missing"""
        if st.session_state.get('upstox_auth_needed'):
            st.sidebar.warning("🔐 Upstox Session Expired")
            creds = DataService.get_credentials()
            auth = UpstoxAuth(creds["api_key"], creds["api_secret"], creds["redirect_uri"])
            
            st.sidebar.markdown("### 🛠️ Re-Authentication Steps")
            st.sidebar.markdown("1. Click the button below to open Upstox login.")
            st.sidebar.link_button("🚀 OPEN LOGIN PAGE", auth.get_login_url(), use_container_width=True)
            
            st.sidebar.markdown("2. After login, you will be redirected to a 'localhost' URL (it might fail to load, that's okay!).")
            st.sidebar.markdown("3. Copy the `code=...` part from that URL.")
            st.sidebar.markdown("4. Paste the code below:")
            
            with st.sidebar.form("auth_code_form"):
                code = st.text_input("Paste Auth Code Here")
                if st.form_submit_button("ACTIVATE SESSION", type="primary"):
                    try:
                        auth.exchange_code_for_tokens(code)
                        st.session_state['upstox_auth_needed'] = False
                        st.sidebar.success("Session Active! Reloading...")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Activation Failed: {e}")

    @staticmethod
    def get_market_breadth():
        indices = {"^NSEI": "^NSEI", "^NSEBANK": "^NSEBANK", "RELIANCE.NS": "RELIANCE.NS", "BTC-USD": "BTC-USD"}
        label_map = {"^NSEI": "NIFTY", "^NSEBANK": "BANKNIFTY", "RELIANCE.NS": "RELIANCE", "BTC-USD": "BITCOIN"}
        try:
            # High speed fetch
            data = yf.download(list(indices.keys()), period="2d", progress=False)['Close']
            
            if isinstance(data, pd.Series):
                # Single ticker result might return a Series
                data = data.to_frame()

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            breadth = {}
            for sym in indices.keys():
                if sym in data.columns:
                    s = data[sym].dropna()
                    if len(s) >= 2:
                        label = label_map[sym]
                        breadth[label] = {
                            "price": s.iloc[-1],
                            "change": ((s.iloc[-1] / s.iloc[-2]) - 1) * 100
                        }
            return breadth
        except Exception as e:
            st.error(f"Breadth Error: {e}")
            return {}
