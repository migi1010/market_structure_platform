import pandas as pd
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class DynamicAlphaEngine:
    """
    Alpha Factor Engine: Dynamic Alpha Scoring System
    Uses HMM Dynamic Weighting based on the Market Regime provided by the Market Structure Engine.
    """
    def __init__(self):
        # Define factor weights based on the 3 Market Regimes
        # Regimes: 0 = Bull, 1 = Bear, 2 = High Volatility
        # Factors required: quality, growth, smart_money, valuation, market_structure
        
        self.regime_weights: Dict[int, Dict[str, float]] = {
            0: {  # Bull Market: Growth & Momentum focus
                'growth': 0.40,
                'market_structure': 0.25,
                'quality': 0.12,
                'smart_money': 0.12,
                'valuation': 0.11
            },
            1: {  # Bear Market: Quality & Valuation focus (Defensive)
                'quality': 0.40,
                'valuation': 0.30,
                'growth': 0.10,
                'smart_money': 0.10,
                'market_structure': 0.10
            },
            2: {  # High Volatility: Balanced Defensive, lower Momentum
                'quality': 0.35,
                'valuation': 0.25,
                'growth': 0.15,
                'smart_money': 0.15,
                'market_structure': 0.10
            }
        }
        
    def get_weights(self, regime: int) -> Dict[str, float]:
        """
        Returns the appropriate factor weights for a given regime.
        """
        if regime not in self.regime_weights:
            logger.warning(f"Unknown regime '{regime}'. Defaulting to High Volatility (2) weights.")
            return self.regime_weights[2]
            
        return self.regime_weights[regime]

    def calculate_alpha_score(self, regime: int, factor_scores: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the final Alpha Score (0-100) using dynamic weights.
        
        Args:
            regime (int): Current market state (0, 1, or 2).
            factor_scores (pd.DataFrame): Dataframe with ticker as index, containing columns:
                'quality', 'growth', 'smart_money', 'valuation', 'market_structure'.
                (Each factor should theoretically be normalized to 0-100 prior to calling this).
                
        Returns:
            pd.DataFrame: A copy of the input dataframe with an added 'alpha_score' column.
        """
        required_cols = ['quality', 'growth', 'smart_money', 'valuation', 'market_structure']
        
        # Verify that all required factor scores are present
        missing_cols = [col for col in required_cols if col not in factor_scores.columns]
        if missing_cols:
            raise ValueError(f"Missing required factor columns for Alpha Score calculation: {missing_cols}")
            
        try:
            weights = self.get_weights(regime)
            
            # Avoid modifying the original dataframe
            results_df = factor_scores.copy()
            
            # Calculate the weighted sum
            results_df['alpha_score'] = (
                results_df['quality'] * weights['quality'] +
                results_df['growth'] * weights['growth'] +
                results_df['smart_money'] * weights['smart_money'] +
                results_df['valuation'] * weights['valuation'] +
                results_df['market_structure'] * weights['market_structure']
            )
            
            # Ensure the final score strictly bounds between 0 and 100
            results_df['alpha_score'] = results_df['alpha_score'].clip(lower=0, upper=100)
            
            return results_df
            
        except Exception as e:
            logger.error(f"Failed to calculate Alpha Score: {e}")
            raise
