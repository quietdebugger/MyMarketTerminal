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
        This enables the app to work independently in the cloud.
        """
        # Try local first
        try:
            # Import inside function to prevent ModuleNotFoundError on Cloud
            import api_config
            return {
                "api_key": api_config.UPSTOX_API_KEY,
                "api_secret": api_config.UPSTOX_API_SECRET
            }
        except ImportError:
            # Fallback to Streamlit Cloud Secrets
            try:
                return {
                    "api_key": st.secrets["UPSTOX_API_KEY"],
                    "api_secret": st.secrets["UPSTOX_API_SECRET"]
                }
            except Exception as e:
                # If both fail, return empty to avoid crash, but log error
                st.error("Authentication credentials missing. Please set st.secrets or api_config.py")
                return {"api_key": "", "api_secret": ""}

    @staticmethod
    @st.cache_data(ttl=300)
    def fetch_price_history(ticker: str, period="1y"):
        try:
            return yf.download(ticker, period=period, progress=False)
        except:
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=60)
    def fetch_upstox_portfolio():
        try:
            creds = DataService.get_credentials()
            if not creds["api_key"]: return [], []
            
            auth = UpstoxAuth(creds["api_key"], creds["api_secret"])
            fo_data = UpstoxFOData(auth)
            holdings = fo_data.get_holdings()
            positions = fo_data.get_positions()
            return holdings, positions
        except Exception:
            return [], []

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
