import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class SmartMoneyEngine:
    """
    Smart Money Engine
    Identifies institutional accumulation and smart money footprints using primarily Volume Structure 
    to bypass the 45-day delay of 13F filings.
    
    Score Components:
    - 0.40 * volume_structure
    - 0.25 * ETF_flow (Mocked Phase 1)
    - 0.20 * institutional_change (Mocked Phase 1)
    - 0.15 * insider_activity (Mocked Phase 1)
    """
    def __init__(self):
        self.weights = {
            'volume_structure': 0.40,
            'ETF_flow': 0.25,
            'institutional_change': 0.20,
            'insider_activity': 0.15
        }
        
    def _normalize_0_100(self, series: pd.Series) -> pd.Series:
        """Min-Max normalizes a series to 0-100, clipping extreme outliers."""
        s_min = series.quantile(0.05)
        s_max = series.quantile(0.95)
        
        if pd.isna(s_min) or pd.isna(s_max) or s_max == s_min:
            return pd.Series(50.0, index=series.index)
            
        normalized = (series - s_min) / (s_max - s_min) * 100
        return normalized.clip(lower=0, upper=100).fillna(50.0)

    def calculate_volume_structure(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculates the core Volume Structure metric to detect Smart Money footprints.
        Includes:
        1. RVOL (Relative Volume)
        2. Accumulation Detection (Consolidation + High RVOL)
        3. Breakout Detection (Strong Price Up + High RVOL)
        4. Dry-up in Pullbacks (Price Down + Low RVOL)
        """
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"DataFrame must contain {required_cols}")
            
        df_calc = df.copy()
        
        # 1. RVOL (Relative Volume over 20 days)
        vol_20ma = df_calc['Volume'].rolling(window=20).mean()
        df_calc['RVOL'] = df_calc['Volume'] / vol_20ma.replace(0, np.nan)
        
        # Price Features
        df_calc['Daily_Return'] = df_calc['Close'].pct_change()
        
        # Real body calculation to detect consolidation or tight closes
        range_hl = df_calc['High'] - df_calc['Low']
        real_body = (df_calc['Close'] - df_calc['Open']).abs()
        df_calc['Body_Ratio'] = real_body / range_hl.replace(0, np.nan)
        
        # Scoring System
        # Start with a baseline score of 0 for each day
        df_calc['Daily_VS_Score'] = 0.0
        
        # Mask 1: Accumulation Day
        # Tight price action (small body), high volume, didn't dump (return >= -0.5%)
        acc_mask = (df_calc['Body_Ratio'] < 0.5) & (df_calc['RVOL'] > 1.5) & (df_calc['Daily_Return'] >= -0.005)
        
        # Mask 2: Volume Breakout
        # Strong up day (> 2%), high volume
        breakout_mask = (df_calc['Daily_Return'] > 0.02) & (df_calc['RVOL'] > 1.5)
        
        # Mask 3: Volume Dry-up in Pullbacks
        # Price pulling back (negative return) but volume dries up completely (RVOL < 0.8)
        dryup_mask = (df_calc['Daily_Return'] < 0) & (df_calc['RVOL'] < 0.8)
        
        # Mask 4: Institutional Distribution (Selling)
        # Strong down day, high volume
        dist_mask = (df_calc['Daily_Return'] < -0.015) & (df_calc['RVOL'] > 1.5)
        
        # Apply logic points
        df_calc.loc[acc_mask, 'Daily_VS_Score'] += 2.0
        df_calc.loc[breakout_mask, 'Daily_VS_Score'] += 3.0
        df_calc.loc[dryup_mask, 'Daily_VS_Score'] += 1.0     # Constructive pullback
        df_calc.loc[dist_mask, 'Daily_VS_Score'] -= 3.0      # Heavy distribution
        
        # The structure is the accumulation of these points over a rolling window (e.g. 20 days)
        smoothed_vs_raw = df_calc['Daily_VS_Score'].rolling(window=20).sum()
        
        return self._normalize_0_100(smoothed_vs_raw)

    def calculate_smart_money_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the complete Smart Money Score for a single ticker over time.
        Returns a DataFrame identical to input index with factor columns.
        """
        try:
            if len(df) < 20:
                raise ValueError("Requires at least 20 periods of data to calculate Smart Money.")
                
            # 1. Real Calculation
            vs_score_normalized = self.calculate_volume_structure(df)
            
            # 2. Mocking external data
            # Simulating correlation with price/volume structures to make mock data look realistic
            
            # Institutional change generally follows mid-term momentum and volume trends
            mom_60 = df['Close'].pct_change(60).fillna(0)
            mock_inst = self._normalize_0_100(mom_60 * df['Volume'].rolling(60).mean())
            
            # ETF Flow generally correlates with short-term momentum
            mom_20 = df['Close'].pct_change(20).fillna(0)
            mock_etf = self._normalize_0_100(mom_20)
            
            # Insider activity is often contrarian (buying the dip)
            mom_10 = df['Close'].pct_change(10).fillna(0)
            mock_insider = self._normalize_0_100(-mom_10)  # Inverse of short term momentum
            
            # Construct result DataFrame
            df_res = pd.DataFrame(index=df.index)
            df_res['volume_structure'] = vs_score_normalized
            df_res['ETF_flow'] = mock_etf
            df_res['institutional_change'] = mock_inst
            df_res['insider_activity'] = mock_insider
            
            # 3. Final Smart Money Score Calculation
            df_res['smart_money_score'] = (
                df_res['volume_structure'] * self.weights['volume_structure'] +
                df_res['ETF_flow'] * self.weights['ETF_flow'] +
                df_res['institutional_change'] * self.weights['institutional_change'] +
                df_res['insider_activity'] * self.weights['insider_activity']
            )
            
            # Strict boundary constraint
            df_res['smart_money_score'] = df_res['smart_money_score'].clip(lower=0, upper=100)
            
            return df_res
            
        except Exception as e:
            logger.error(f"Error calculating Smart Money score: {e}")
            raise
