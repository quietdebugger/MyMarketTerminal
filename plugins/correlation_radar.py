import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from core.plugin_interface import MarketTerminalPlugin

# Use a session with a custom user-agent to mitigate rate limits
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

class CorrelationRadarPlugin(MarketTerminalPlugin):
    @property
    def name(self) -> str: return "Correlation Radar"
    @property
    def category(self) -> str: return "Research"
    @property
    def icon(self) -> str: return "🔗"

    def render(self, ticker: str):
        st.markdown(f"### 🔗 Systemic Correlation: {ticker}")
        
        try:
            # Tickers to compare
            benchmarks = ["^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS"]
            all_tickers = benchmarks + [ticker]
            
            with st.spinner("Calculating Peer Correlation..."):
                data = yf.download(all_tickers, period="6mo", progress=False, session=session)['Close']
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                returns = data.pct_change().dropna()
                corr_matrix = returns.corr()
                
                # Extract correlations for current ticker
                ticker_corr = corr_matrix[ticker].sort_values(ascending=False)
                
                st.subheader("Correlation with Benchmarks")
                c1, c2, c3 = st.columns(3)
                
                # Mapping symbols to names for UI
                names = {"^NSEI": "NIFTY 50", "^NSEBANK": "BANK NIFTY", ticker: "ACTIVE"}
                
                if "^NSEI" in ticker_corr:
                    c1.metric("Nifty 50 Beta", f"{ticker_corr['^NSEI']:.2f}")
                if "^NSEBANK" in ticker_corr:
                    c2.metric("Bank Nifty Beta", f"{ticker_corr['^NSEBANK']:.2f}")
                
                st.markdown("---")
                st.subheader("Heatmap Visualization")
                st.dataframe(corr_matrix.style.background_gradient(cmap="coolwarm"), use_container_width=True)
                
                st.info("**Tip:** High correlation (>0.8) means this stock moves with the market. Low correlation (<0.3) means it offers diversification.")

        except Exception as e:
            st.error(f"Correlation Error: {e}")
