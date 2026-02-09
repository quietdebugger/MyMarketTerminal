import streamlit as st
import numpy as np
import yfinance as yf
from core.plugin_interface import MarketTerminalPlugin

class InvestmentDeepDivePlugin(MarketTerminalPlugin):
    @property
    def name(self) -> str: return "Investment Deep Dive"
    @property
    def category(self) -> str: return "Research"
    @property
    def icon(self) -> str: return "🛡️"

    def render(self, ticker: str):
        st.markdown(f"### 📊 Institutional Risk Profile: {ticker}")
        
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="5y")
            info = stock.info
            
            # Risk Math
            returns = data['Close'].pct_change().dropna()
            var_95 = np.percentile(returns, 5) * 100
            max_dd = ((data['Close'] - data['Close'].cummax()) / data['Close'].cummax()).min() * 100
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Value at Risk (95%)", f"{var_95:.2f}%", delta_color="inverse")
                st.write("Interpretation: Highest expected daily loss.")
            with col2:
                st.metric("Max Cycle Drawdown", f"{max_dd:.2f}%")
                st.write("Interpretation: Historical worst-case crash.")

            st.markdown("---")
            st.subheader("Financial Integrity")
            f1, f2, f3 = st.columns(3)
            f1.metric("Debt/Equity", info.get('debtToEquity', 'N/A'))
            f2.metric("Profit Margins", f"{info.get('profitMargins', 0)*100:.2f}%")
            f3.metric("PB Ratio", f"{info.get('priceToBook', 0):.2f}")
            
        except Exception as e:
            st.error(f"Deep Dive Error: {e}")