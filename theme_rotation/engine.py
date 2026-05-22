import numpy as np
import pandas as pd
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ThemeRotationEngine:
    """
    Theme Rotation Engine
    Identifies which sectors or themes money is flowing into by calculating a Theme Score.
    
    Score Components:
    - 0.30 * relative_strength
    - 0.25 * volume_strength
    - 0.20 * earnings_momentum (Mocked for Phase 1)
    - 0.15 * ETF_inflow (Mocked for Phase 1)
    - 0.10 * sentiment (Mocked for Phase 1)
    """
    def __init__(self):
        self.weights = {
            'relative_strength': 0.30,
            'volume_strength': 0.25,
            'earnings_momentum': 0.20,
            'ETF_inflow': 0.15,
            'sentiment': 0.10
        }

    def _normalize_0_100(self, series: pd.Series) -> pd.Series:
        """Min-Max normalizes a series to 0-100, clipping extreme outliers."""
        s_min = series.quantile(0.05)
        s_max = series.quantile(0.95)
        
        if pd.isna(s_min) or pd.isna(s_max) or s_max == s_min:
            return pd.Series(50.0, index=series.index)
            
        normalized = (series - s_min) / (s_max - s_min) * 100
        return normalized.clip(lower=0, upper=100).fillna(50.0)

    def calculate_relative_strength(self, df_etf: pd.DataFrame, df_spy: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        Calculates Vectorized Relative Strength against the benchmark (SPY).
        Formula: (ETF_Close / SPY_Close) Momentum over 'window' periods.
        """
        # Ensure 'Close' exists
        if 'Close' not in df_etf.columns or 'Close' not in df_spy.columns:
            raise ValueError("DataFrames must contain 'Close' prices.")
            
        ratio = df_etf['Close'] / df_spy['Close']
        rs = ratio.pct_change(periods=window)
        return rs

    def calculate_volume_strength(self, df_etf: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        Calculates Vectorized Volume Strength.
        Formula: Current Volume / Moving Average Volume
        """
        if 'Volume' not in df_etf.columns:
            raise ValueError("DataFrame must contain 'Volume'.")
            
        vol_ma = df_etf['Volume'].rolling(window=window).mean()
        # Handle zero division by replacing 0 with nan before division
        vol_strength = df_etf['Volume'] / vol_ma.replace(0, np.nan)
        return vol_strength

    def calculate_theme_score(self, df_etfs: Dict[str, pd.DataFrame], df_spy: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the Theme Score for a dictionary of ETFs.
        
        Args:
            df_etfs: Dict of {ticker: DataFrame (OHLCV)}
            df_spy: Benchmark DataFrame (OHLCV)
            
        Returns:
            pd.DataFrame: Contains normalized factor scores and final Theme_Score for each ticker.
        """
        results = []
        try:
            for ticker, df in df_etfs.items():
                # Align dates to ensure safe vectorized operations
                common_dates = df.index.intersection(df_spy.index)
                if len(common_dates) < 20:
                    logger.warning(f"Not enough common data points for {ticker}. Skipping.")
                    continue
                
                df_align = df.loc[common_dates].copy()
                spy_align = df_spy.loc[common_dates].copy()
                
                # 1. Calculate Real Features
                rs_raw = self.calculate_relative_strength(df_align, spy_align)
                vs_raw = self.calculate_volume_strength(df_align)
                
                # Setup calculation DataFrame
                df_calc = pd.DataFrame(index=common_dates)
                df_calc['relative_strength'] = self._normalize_0_100(rs_raw)
                df_calc['volume_strength'] = self._normalize_0_100(vs_raw)
                
                # 2. Mock Missing Fundamentals & Sentiment (Earnings, ETF Inflow, Sentiment)
                # Seed with the hash of the ticker to ensure consistent mock values per ticker
                np.random.seed(hash(ticker) % (2**32))
                
                # Use random walk smoothed by a rolling mean to look like realistic time series
                mock_em = pd.Series(np.random.normal(50, 15, len(common_dates)), index=common_dates).rolling(5).mean().fillna(50)
                mock_etf = pd.Series(np.random.normal(50, 20, len(common_dates)), index=common_dates).rolling(5).mean().fillna(50)
                mock_sent = pd.Series(np.random.normal(50, 25, len(common_dates)), index=common_dates).rolling(5).mean().fillna(50)
                
                df_calc['earnings_momentum'] = mock_em.clip(0, 100)
                df_calc['ETF_inflow'] = mock_etf.clip(0, 100)
                df_calc['sentiment'] = mock_sent.clip(0, 100)
                
                # 3. Calculate Final Theme Score
                df_calc['theme_score'] = (
                    df_calc['relative_strength'] * self.weights['relative_strength'] +
                    df_calc['volume_strength'] * self.weights['volume_strength'] +
                    df_calc['earnings_momentum'] * self.weights['earnings_momentum'] +
                    df_calc['ETF_inflow'] * self.weights['ETF_inflow'] +
                    df_calc['sentiment'] * self.weights['sentiment']
                )
                
                # Extract the latest score
                latest_score = df_calc.iloc[-1]
                
                results.append({
                    'Ticker': ticker,
                    'Theme_Score': latest_score['theme_score'],
                    'Relative_Strength': latest_score['relative_strength'],
                    'Volume_Strength': latest_score['volume_strength'],
                    'Earnings_Momentum': latest_score['earnings_momentum'],
                    'ETF_Inflow': latest_score['ETF_inflow'],
                    'Sentiment': latest_score['sentiment']
                })
                
            final_df = pd.DataFrame(results)
            if not final_df.empty:
                final_df.set_index('Ticker', inplace=True)
            return final_df
            
        except Exception as e:
            logger.error(f"Error calculating theme scores: {e}")
            raise
