import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from core.plugin_interface import MarketTerminalPlugin

class MarketScreenerPlugin(MarketTerminalPlugin):
    @property
    def name(self) -> str: return "Market Screener"
    @property
    def category(self) -> str: return "Intelligence"
    @property
    def icon(self) -> str: return "🔍"

    def render(self, ticker: str):
        st.markdown("### 🔍 Alpha Watchlist Screener")
        
        watchlist = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "ZOMATO.NS", "TATAMOTORS.NS"]
        
        if st.button("Scan All Watchlist Stocks"):
            results = []
            progress = st.progress(0)
            
            for i, stock_sym in enumerate(watchlist):
                try:
                    stock = yf.Ticker(stock_sym)
                    data = stock.history(period="6mo")
                    info = stock.info
                    
                    # Mini Alpha Logic
                    rsi = 100 - (100 / (1 + (data['Close'].diff().clip(lower=0).tail(14).mean() / (data['Close'].diff().clip(upper=0).abs().tail(14).mean() + 1e-9))))
                    z_score = (data['Close'].iloc[-1] - data['Close'].mean()) / data['Close'].std()
                    
                    score = 0
                    if rsi < 40: score += 30
                    if z_score < -1: score += 40
                    if info.get('trailingPE', 100) < 25: score += 30
                    
                    results.append({
                        "Ticker": stock_sym,
                        "Price": f"₹{data['Close'].iloc[-1]:.2f}",
                        "RSI": round(rsi, 1),
                        "Z-Score": round(z_score, 2),
                        "Alpha": f"{score}%"
                    })
                except: pass
                progress.progress((i + 1) / len(watchlist))
            
            df = pd.DataFrame(results)
            st.subheader("Live Market Rankings")
            st.dataframe(df.style.background_gradient(subset=['RSI'], cmap="RdYlGn_r"), use_container_width=True)
            st.success("Scan Complete. Focus on low RSI and high Alpha stocks.")
