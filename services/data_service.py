import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from upstox_fo_complete import UpstoxAuth, UpstoxFOData
import api_config

class DataService:
    
    @staticmethod
    @st.cache_data(ttl=300) # Cache for 5 minutes
    def fetch_price_history(ticker: str, period="1y"):
        """Fetches cached price history to prevent re-downloading on tab switch."""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            return data
        except Exception:
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=3600) # Cache Fundamentals for 1 hour
    def fetch_fundamentals(ticker: str):
        try:
            stock = yf.Ticker(ticker)
            return stock.info
        except:
            return {}

    @staticmethod
    @st.cache_data(ttl=60) # Cache Portfolio for 1 minute
    def fetch_upstox_portfolio():
        """Fetches real Upstox holdings."""
        try:
            auth = UpstoxAuth(api_config.UPSTOX_API_KEY, api_config.UPSTOX_API_SECRET)
            fo_data = UpstoxFOData(auth)
            holdings = fo_data.get_holdings()
            positions = fo_data.get_positions()
            return holdings, positions
        except Exception as e:
            return [], []

    @staticmethod
    def get_market_breadth():
        """Optimized batch fetch for top bar."""
        indices = ["^NSEI", "^NSEBANK", "^BSESN", "BTC-USD"]
        try:
            data = yf.download(indices, period="2d", progress=False)['Close']
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            breadth = {}
            for ticker in indices:
                if ticker in data.columns:
                    series = data[ticker].dropna()
                    if len(series) >= 2:
                        breadth[ticker] = {
                            "price": series.iloc[-1],
                            "change": ((series.iloc[-1] / series.iloc[-2]) - 1) * 100
                        }
            return breadth
        except:
            return {}
