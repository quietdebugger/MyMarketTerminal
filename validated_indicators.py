"""
Validated Indicators
Only computes indicators when data permits
NO PLACEHOLDERS - returns None when insufficient data
Borrowed from bbt9
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class IndicatorResult:
    """Wrapper for indicator with quality metadata"""
    value: Optional[float]
    available: bool
    reason_unavailable: Optional[str]
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    
    def display(self, name: str, format_str: str = ".2f") -> str:
        """Format for display"""
        if self.available and self.value is not None:
            formatted_value = f"{self.value:{format_str}}"
            return f"{name}: {formatted_value}"
        else:
            return f"{name}: Not available - {self.reason_unavailable}"

class ValidatedIndicators:
    """
    Compute indicators only when data is sufficient
    All methods return IndicatorResult with quality info
    """
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.bars = len(data)
    
    def rsi(self, period: int = 14) -> IndicatorResult:
        min_bars = period * 3
        if self.bars < min_bars:
            return IndicatorResult(None, False, f"Need {min_bars} bars", "N/A")
        
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi_value = 100 - (100 / (1 + rs))
        current_rsi = rsi_value.iloc[-1]
        
        if pd.isna(current_rsi):
            return IndicatorResult(None, False, "Calculation failed", "N/A")
            
        # Confidence based on trend (RSI less reliable in strong trends)
        ma20 = self.data['close'].rolling(20).mean().iloc[-1]
        current_price = self.data['close'].iloc[-1]
        confidence = "LOW" if abs((current_price/ma20)-1) > 0.1 else "HIGH"
        
        return IndicatorResult(float(current_rsi), True, None, confidence)
    
    def atr(self, period: int = 14) -> IndicatorResult:
        if self.bars < period + 1:
            return IndicatorResult(None, False, f"Need {period+1} bars", "N/A")
            
        high_low = self.data['high'] - self.data['low']
        high_close = np.abs(self.data['high'] - self.data['close'].shift())
        low_close = np.abs(self.data['low'] - self.data['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_value = true_range.rolling(period).mean().iloc[-1]
        
        return IndicatorResult(float(atr_value) if not pd.isna(atr_value) else None, True, None, "HIGH")

    def support_resistance(self) -> Dict[str, IndicatorResult]:
        if self.bars < 50:
            unavailable = IndicatorResult(None, False, "Need 50+ bars", "N/A")
            return {'resistance': unavailable, 'support': unavailable}
            
        recent_high = self.data['high'].iloc[-20:].max()
        recent_low = self.data['low'].iloc[-20:].min()
        
        return {
            'resistance': IndicatorResult(float(recent_high), True, None, "MEDIUM"),
            'support': IndicatorResult(float(recent_low), True, None, "MEDIUM")
        }

class ValidatedOptionsIndicators:
    """Options indicators with validation"""
    
    @staticmethod
    def weighted_oi_levels(option_chain: pd.DataFrame, current_price: float) -> Dict[str, IndicatorResult]:
        if option_chain.empty:
            unavailable = IndicatorResult(None, False, "No option chain", "N/A")
            return {'call_resistance': unavailable, 'put_support': unavailable}
            
        # Weight by inverse distance
        chain = option_chain.copy()
        chain['distance'] = abs(chain['strike'] - current_price)
        chain['weight'] = 1 / (1 + chain['distance']/current_price)
        
        chain['w_ce_oi'] = chain['CE_OI'] * chain['weight']
        chain['w_pe_oi'] = chain['PE_OI'] * chain['weight']
        
        call_res = chain.loc[chain['w_ce_oi'].idxmax(), 'strike']
        put_sup = chain.loc[chain['w_pe_oi'].idxmax(), 'strike']
        
        confidence = "HIGH" if chain['CE_OI'].sum() > 1e6 else "LOW"
        
        return {
            'call_resistance': IndicatorResult(float(call_res), True, None, confidence),
            'put_support': IndicatorResult(float(put_sup), True, None, confidence)
        }
