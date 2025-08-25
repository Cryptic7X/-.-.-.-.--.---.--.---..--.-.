"""
ANALYZERS MODULE - TrendPulse & StochRSI Implementation
Perfect replication of Pine Script logic with Heikin Ashi conversion
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging


class HeikinAshiConverter:
    """
    Heikin Ashi candle converter - exact implementation
    Converts regular OHLC candles to Heikin Ashi format
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def convert(self, df):
        """Convert regular OHLC DataFrame to Heikin Ashi"""
        if df is None or len(df) < 2:
            return None
        
        try:
            ha_df = df.copy()
            
            # Initialize Heikin Ashi columns
            ha_df['HA_Close'] = 0.0
            ha_df['HA_Open'] = 0.0
            ha_df['HA_High'] = 0.0
            ha_df['HA_Low'] = 0.0
            
            # Calculate first Heikin Ashi candle
            first_idx = ha_df.index[0]
            ha_df.loc[first_idx, 'HA_Close'] = (
                df.loc[first_idx, 'Open'] + df.loc[first_idx, 'High'] + 
                df.loc[first_idx, 'Low'] + df.loc[first_idx, 'Close']
            ) / 4.0
            
            ha_df.loc[first_idx, 'HA_Open'] = (
                df.loc[first_idx, 'Open'] + df.loc[first_idx, 'Close']
            ) / 2.0
            
            ha_df.loc[first_idx, 'HA_High'] = df.loc[first_idx, 'High']
            ha_df.loc[first_idx, 'HA_Low'] = df.loc[first_idx, 'Low']
            
            # Calculate subsequent candles
            for i in range(1, len(df)):
                curr_idx = ha_df.index[i]
                prev_idx = ha_df.index[i-1]
                
                # HA Close = (O + H + L + C) / 4
                ha_df.loc[curr_idx, 'HA_Close'] = (
                    df.loc[curr_idx, 'Open'] + df.loc[curr_idx, 'High'] + 
                    df.loc[curr_idx, 'Low'] + df.loc[curr_idx, 'Close']
                ) / 4.0
                
                # HA Open = (prev HA Open + prev HA Close) / 2
                ha_df.loc[curr_idx, 'HA_Open'] = (
                    ha_df.loc[prev_idx, 'HA_Open'] + ha_df.loc[prev_idx, 'HA_Close']
                ) / 2.0
                
                # HA High = max(H, HA Open, HA Close)
                ha_df.loc[curr_idx, 'HA_High'] = max(
                    df.loc[curr_idx, 'High'],
                    ha_df.loc[curr_idx, 'HA_Open'],
                    ha_df.loc[curr_idx, 'HA_Close']
                )
                
                # HA Low = min(L, HA Open, HA Close)
                ha_df.loc[curr_idx, 'HA_Low'] = min(
                    df.loc[curr_idx, 'Low'],
                    ha_df.loc[curr_idx, 'HA_Open'],
                    ha_df.loc[curr_idx, 'HA_Close']
                )
            
            return ha_df
            
        except Exception as e:
            self.logger.error(f"Heikin Ashi conversion error: {e}")
            return None


class TrendPulseAnalyzer:
    """
    TrendPulse analyzer - exact Pine Script replication
    Your private indicator logic with precise parameter matching
    """
    
    def __init__(self):
        # Your exact Pine Script parameters
        self.ch_len = 9      # Channel Length
        self.avg_len = 12    # Average Length
        self.smooth_len = 3  # Smoothing Length
        self.logger = logging.getLogger(__name__)
    
    def ema(self, series, length):
        """Exponential Moving Average - exact Pine Script calculation"""
        return series.ewm(span=length, adjust=False).mean()
    
    def sma(self, series, length):
        """Simple Moving Average"""
        return series.rolling(window=length).mean()
    
    def analyze(self, ha_df, tier_type):
        """
        Analyze Heikin Ashi data with exact Pine Script logic
        Only checks most recent CLOSED candle - no historical loops
        """
        if ha_df is None or len(ha_df) < self.ch_len + self.avg_len + 5:
            return {
                'has_signal': False,
                'signal_type': 'none',
                'wt1': 0,
                'wt2': 0,
                'strength': 0
            }
        
        try:
            # Use HLC3 from Heikin Ashi candles (your exact calculation)
            ha_hlc3 = (ha_df['HA_High'] + ha_df['HA_Low'] + ha_df['HA_Close']) / 3.0
            
            # TrendPulse calculation - your exact Pine Script logic
            esa = self.ema(ha_hlc3, self.ch_len)
            dev = self.ema(abs(ha_hlc3 - esa), self.ch_len)
            
            # Avoid division by zero
            dev_safe = dev.replace(0, 0.001)
            ci = (ha_hlc3 - esa) / (0.015 * dev_safe)
            
            # Wave Trend calculations
            wt1 = self.ema(ci, self.avg_len)
            wt2 = self.sma(wt1, self.smooth_len)
            
            # CRITICAL: Only check most recent CLOSED candle
            if len(wt1) < 3:
                return {
                    'has_signal': False,
                    'signal_type': 'none',
                    'wt1': 0,
                    'wt2': 0,
                    'strength': 0
                }
            
            # Current values from closed candle (not in-progress candle)
            wt1_current = float(wt1.iloc[-2])   # Most recent closed
            wt2_current = float(wt2.iloc[-2])
            wt1_previous = float(wt1.iloc[-3])  # Previous closed
            wt2_previous = float(wt2.iloc[-3])
            
            # In TrendPulseAnalyzer.analyze() for HIGH_RISK
            if tier_type == "HIGH_RISK":
                # FIXED: Use your exact HIGH_RISK thresholds
                oversold   = (wt1_current <= -60) and (wt2_current <= -60)
                overbought = (wt1_current >= 60)  and (wt2_current >= 60)
            else:
                # STANDARD (no change)
                oversold   = (wt1_current <= -60) and (wt2_current <= -60)
                overbought = (wt1_current >= 60)  and (wt2_current >= 60)

            
            # Cross detection (your exact logic)
            bullish_cross = (wt1_previous <= wt2_previous) and (wt1_current > wt2_current)
            bearish_cross = (wt1_previous >= wt2_previous) and (wt1_current < wt2_current)
            
            # Signal generation - only if cross AND extreme condition
            signal_type = 'none'
            has_signal = False
            
            if bullish_cross and oversold:
                signal_type = 'BUY'
                has_signal = True
            elif bearish_cross and overbought:
                signal_type = 'SELL'
                has_signal = True
            
            return {
                'has_signal': has_signal,
                'signal_type': signal_type,
                'wt1': wt1_current,
                'wt2': wt2_current,
                'strength': abs(wt1_current) + abs(wt2_current),
                'cross_type': 'bullish' if bullish_cross else 'bearish' if bearish_cross else 'none'
            }
            
        except Exception as e:
            self.logger.error(f"TrendPulse analysis error: {e}")
            return {
                'has_signal': False,
                'signal_type': 'none',
                'wt1': 0,
                'wt2': 0,
                'strength': 0
            }


class StochRSICalculator:
    """
    Stochastic RSI calculator for 2H confirmation
    Standard implementation with configurable parameters
    """
    
    def __init__(self, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.k_smooth = k_smooth
        self.d_smooth = d_smooth
        self.logger = logging.getLogger(__name__)
    
    def calculate_rsi(self, close_prices):
        """Calculate RSI using standard formula"""
        delta = close_prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.rsi_period).mean()
        avg_loss = loss.rolling(window=self.rsi_period).mean()
        
        # Avoid division by zero
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate(self, df):
        """
        Calculate Stochastic RSI for 2H confirmation
        Returns current K and D values for signal confirmation
        """
        if df is None or len(df) < self.rsi_period + self.stoch_period + self.k_smooth + self.d_smooth + 10:
            return None
        
        try:
            # Calculate RSI first
            close_prices = df['Close']
            rsi = self.calculate_rsi(close_prices)
            
            # Calculate Stochastic of RSI
            rsi_min = rsi.rolling(window=self.stoch_period).min()
            rsi_max = rsi.rolling(window=self.stoch_period).max()
            
            # Avoid division by zero
            rsi_range = rsi_max - rsi_min
            rsi_range = rsi_range.replace(0, 1e-10)
            
            stoch_rsi = ((rsi - rsi_min) / rsi_range) * 100
            
            # Smooth with moving averages
            stoch_rsi_k = stoch_rsi.rolling(window=self.k_smooth).mean()
            stoch_rsi_d = stoch_rsi_k.rolling(window=self.d_smooth).mean()
            
            # Get current values from most recent CLOSED candle
            if len(stoch_rsi_k) < 2 or len(stoch_rsi_d) < 2:
                return None
            
            current_k = float(stoch_rsi_k.iloc[-2])  # Closed candle
            current_d = float(stoch_rsi_d.iloc[-2])  # Closed candle
            
            return {
                'stoch_rsi_k': stoch_rsi_k,
                'stoch_rsi_d': stoch_rsi_d,
                'current_k': current_k,
                'current_d': current_d,
                'calculation_timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            self.logger.error(f"StochRSI calculation error: {e}")
            return None
