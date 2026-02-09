import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from core.plugin_interface import MarketTerminalPlugin

class AlphaRadarPlugin(MarketTerminalPlugin):
    @property
    def name(self) -> str: return "Alpha Fusion Radar"
    @property
    def category(self) -> str: return "Intelligence"
    @property
    def icon(self) -> str: return "📡"

    def render(self, ticker: str):
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y")
            if data.empty:
                st.error("No Data Found for Ticker.")
                return
            
            # --- CALCULATE SCORES ---
            rsi = 100 - (100 / (1 + (data['Close'].diff().clip(lower=0).tail(14).mean() / (data['Close'].diff().clip(upper=0).abs().tail(14).mean() + 1e-9))))
            z_score = (data['Close'].iloc[-1] - data['Close'].mean()) / data['Close'].std()
            
            score = 0
            if rsi < 40: score += 30 # Oversold
            if z_score < -1: score += 40 # Statistical value
            if data['Close'].iloc[-1] > data['Close'].rolling(50).mean().iloc[-1]: score += 30 # Trend
            
            # --- UI CARDS ---
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown(f"""
                    <div style='background-color: #111; padding: 20px; border-radius: 10px; border: 1px solid #333;'>
                        <div style='color: #888; font-size: 0.8rem;'>CONVICTION</div>
                        <div style='color: #00d4ff; font-size: 2.5rem; font-weight: bold;'>{score}%</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with c2:
                st.markdown(f"""
                    <div style='background-color: #111; padding: 20px; border-radius: 10px; border: 1px solid #333;'>
                        <div style='color: #888; font-size: 0.8rem;'>RSI (14)</div>
                        <div style='color: {"#00ff00" if rsi < 40 else "#ccc"}; font-size: 2.5rem; font-weight: bold;'>{rsi:.1f}</div>
                    </div>
                """, unsafe_allow_html=True)
                
            with c3:
                st.markdown(f"""
                    <div style='background-color: #111; padding: 20px; border-radius: 10px; border: 1px solid #333;'>
                        <div style='color: #888; font-size: 0.8rem;'>STAT Z-SCORE</div>
                        <div style='color: {"#00ff00" if z_score < -1 else "#ccc"}; font-size: 2.5rem; font-weight: bold;'>{z_score:.2f}</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.area_chart(data['Close'], height=300)
            
            if score > 60:
                st.success("🎯 **HIGH CONVICTION SETUP:** Statistical Anomaly + Momentum turning positive.")
            else:
                st.info("⌛ **WAITING FOR SIGNAL:** Conditions not yet ideal for high-conviction entry.")

        except Exception as e:
            st.error(f"Alpha Engine Error: {e}")
