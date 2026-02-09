import streamlit as st
import pandas as pd
import numpy as np
from core.plugin_interface import MarketTerminalPlugin
from services.data_service import DataService
from ui.components import render_metric_card

class PortfolioProPlugin(MarketTerminalPlugin):
    @property
    def name(self) -> str: return "Portfolio Pro"
    @property
    def category(self) -> str: return "Trading"
    @property
    def icon(self) -> str: return "📊"

    def analyze_holding(self, ticker):
        data = DataService.fetch_price_history(ticker, period="3mo")
        if data.empty: return 0, 0, 0
        rsi = 100 - (100 / (1 + (data['Close'].diff().clip(lower=0).rolling(14).mean() / (data['Close'].diff().clip(upper=0).abs().rolling(14).mean() + 1e-9))))
        trend = (data['Close'].iloc[-1] > data['Close'].rolling(50).mean().iloc[-1])
        score = int(trend) * 50 + (40 if rsi.iloc[-1] < 40 else 10)
        return score, rsi.iloc[-1], data['Close'].pct_change().std() * 100

    def render(self, global_ticker: str):
        st.markdown("### 📊 Portfolio Mobile X-Ray")
        
        try:
            # 1. FETCH REAL DATA WITH CLOUD-READY AUTH
            holdings, positions = DataService.fetch_upstox_portfolio()
            
            if not holdings and not positions:
                st.warning("No live data. Ensure Upstox tokens are active.")
                return

        df = pd.DataFrame(holdings)
        
        # Performance Summary
        curr_val = (df['quantity'] * df['last_price']).sum()
        total_pnl = df['pnl'].sum()
        
        c1, c2 = st.columns(2)
        with c1: render_metric_card("Portfolio Value", f"₹{curr_val:,.0f}")
        with c2: render_metric_card("Total P&L", f"₹{total_pnl:,.0f}", f"{(total_pnl/curr_val)*100:+.2f}%", color="green" if total_pnl > 0 else "red")

        st.markdown("---")
        
        # RESPONSIVE GRID
        st.subheader("Asset Diagnostics")
        for i, row in df.iterrows():
            with st.container():
                # On mobile, these columns stack automatically due to our CSS
                col_a, col_b = st.columns([2, 1])
                
                # Fetch Alpha Data for this row
                score, rsi, vol = self.analyze_holding(row['trading_symbol'] + ".NS")
                
                col_a.markdown(f"**{row['trading_symbol']}** | Qty: {row['quantity']}")
                col_a.markdown(f"<span style='color:#888'>Avg: ₹{row['average_price']:.0f} | LTP: ₹{row['last_price']:.0f}</span>", unsafe_allow_html=True)
                
                pnl_color = "#00ff00" if row['pnl'] > 0 else "#ff4b4b"
                col_b.markdown(f"<div style='text-align:right; color:{pnl_color}; font-weight:bold;'>₹{row['pnl']:,.0f}</div>", unsafe_allow_html=True)
                
                # Alpha Progress Bar
                st.progress(score/100, text=f"Alpha Confidence: {score}% | RSI: {rsi:.1f}")
                st.markdown("<div style='margin-bottom:20px; border-bottom:1px solid #222;'></div>", unsafe_allow_html=True)

        if positions:
            with st.expander("Active F&O Positions"):
                st.write(pd.DataFrame(positions))