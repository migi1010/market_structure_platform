import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DeepValueEngine:
    """
    Deep Value Engine
    Identifies fundamentally strong companies whose stock prices have been unfairly punished (Left-side buying).
    """
    def __init__(self):
        # Strict constraints as defined in the system specifications
        self.min_drawdown = 0.30
        self.max_drawdown = 0.60
        self.min_rev_growth = 0.10
        self.min_roe = 0.15

    def screen_deep_value_stocks(self, df_prices: pd.DataFrame, df_fundamentals: pd.DataFrame) -> pd.DataFrame:
        """
        Screens for deep value opportunities based on strict price drawdown and fundamental health.
        
        Args:
            df_prices: DataFrame containing Daily Close prices. 
                       Expected format: Tickers as columns, Dates as index.
            df_fundamentals: DataFrame containing fundamental metrics.
                             Expected format: Tickers as index.
                             Expected columns: 'Revenue_Growth', 'ROE', 'FCF'
                             
        Returns:
            pd.DataFrame: A filtered DataFrame containing the deep value targets and their metrics.
        """
        results = []
        try:
            # Iterate over each ticker present in the price data
            for ticker in df_prices.columns:
                # Ensure we have fundamental data for this ticker
                if ticker not in df_fundamentals.index:
                    continue
                
                prices = df_prices[ticker].dropna()
                
                # We need at least one year of data to calculate a reliable 52-week high
                if len(prices) < 252:
                    logger.debug(f"Not enough price history for {ticker} (requires 252 days).")
                    continue
                    
                # 1. Drawdown Calculation (Current vs Recent 52-week High)
                recent_high = prices.iloc[-252:].max()
                current_price = prices.iloc[-1]
                
                if pd.isna(recent_high) or recent_high == 0:
                    continue
                    
                drawdown = (recent_high - current_price) / recent_high
                
                # Check if drawdown is within the 30% - 60% sweet spot
                if not (self.min_drawdown <= drawdown <= self.max_drawdown):
                    continue
                    
                # 2. Fundamental Validation
                fund_data = df_fundamentals.loc[ticker]
                
                # Handle possible missing values gracefully
                rev_growth = fund_data.get('Revenue_Growth', 0.0)
                roe = fund_data.get('ROE', 0.0)
                fcf = fund_data.get('FCF', 0.0)
                
                # Replace NaNs with 0 to ensure logical comparisons work
                rev_growth = 0.0 if pd.isna(rev_growth) else rev_growth
                roe = 0.0 if pd.isna(roe) else roe
                fcf = 0.0 if pd.isna(fcf) else fcf
                
                # 3. Apply Hard Filters
                # Revenue Growth > 10%, ROE > 15%, Positive Free Cash Flow
                if rev_growth > self.min_rev_growth and roe > self.min_roe and fcf > 0:
                    results.append({
                        'Ticker': ticker,
                        'Drawdown': drawdown,
                        'Current_Price': current_price,
                        'Recent_High': recent_high,
                        'Revenue_Growth': rev_growth,
                        'ROE': roe,
                        'FCF': fcf,
                        'Status': 'Deep Value'
                    })
                    
            res_df = pd.DataFrame(results)
            if not res_df.empty:
                res_df.set_index('Ticker', inplace=True)
                
            return res_df
            
        except Exception as e:
            logger.error(f"Error executing Deep Value screen: {e}")
            raise
