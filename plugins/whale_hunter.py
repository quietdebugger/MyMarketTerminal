import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from core.plugin_interface import MarketTerminalPlugin

class WhaleHunterPlugin(MarketTerminalPlugin):
    @property
    def name(self) -> str: return "Whale Hunter"
    @property
    def category(self) -> str: return "Intelligence"
    @property
    def icon(self) -> str: return "🐋"

    def render(self, ticker: str):
        st.markdown(f"### 🐋 Smart Money Tracker: {ticker}")
        
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="6mo")
            if data.empty: return
            
            # --- PORTE LOGIC: OBV Divergence ---
            data['OBV'] = (np.sign(data['Close'].diff()) * data['Volume']).fillna(0).cumsum()
            
            # Simplified Divergence: Price falling but OBV rising
            price_drop = data['Close'].iloc[-1] < data['Close'].iloc[-20]
            obv_rise = data['OBV'].iloc[-1] > data['OBV'].iloc[-20]
            
            # --- PORTED LOGIC: Dark Pool Activity (VWAP Deviation) ---
            data['VWAP'] = (data['Close'] * data['Volume']).rolling(20).sum() / data['Volume'].rolling(20).sum()
            vwap_dev = ((data['Close'].iloc[-1] - data['VWAP'].iloc[-1]) / data['VWAP'].iloc[-1]) * 100
            
            # UI Render
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🏛️ Market Participation")
                if price_drop and obv_rise:
                    st.success("✅ **BULLISH DIVERGENCE:** Price is falling but OBV is rising. Smart money is accumulating.")
                elif not price_drop and not obv_rise:
                    st.error("⚠️ **BEARISH DIVERGENCE:** Price is rising but OBV is falling. Smart money is exiting.")
                else:
                    st.info("⚖️ **SYNCED:** Price and volume are moving together.")

            with col2:
                st.markdown("#### 🌑 Dark Pool Estimation")
                st.metric("VWAP Deviation", f"{vwap_dev:.2f}%", help="Institutional interest often clusters around VWAP.")
                if abs(vwap_dev) > 2:
                    st.warning("Significant deviation detected. Potential block trade activity.")

            st.markdown("---")
            st.subheader("Accumulation/Distribution Line")
            
            # A/D Line Logic
            mfm = ((data['Close'] - data['Low']) - (data['High'] - data['Close'])) / (data['High'] - data['Low'] + 1e-9)
            ad_line = (mfm * data['Volume']).cumsum()
            st.line_chart(ad_line, height=200)
            
        except Exception as e:
            st.error(f"Whale Hunter Error: {e}")
