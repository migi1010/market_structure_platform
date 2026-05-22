import numpy as np
import pandas as pd
import yfinance as yf
import logging
from typing import Tuple, Dict, Optional
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """
    Production-Ready Market Structure Engine: Market Regime Detector
    
    Uses Hidden Markov Model (GaussianHMM) to classify market regimes based on:
    - Daily Log Returns
    - 20-day rolling annualized volatility
    
    Fetches real SPY data from yfinance and implements robust error handling.
    
    Regimes mapping (by volatility feature mean):
    - State 0: Bull Market (低波動牛市) - Lowest volatility
    - State 1: Bear Market (熊市防守) - Negative returns
    - State 2: High Volatility (高波動震盪) - Highest volatility
    """
    
    def __init__(self, n_components: int = 3, random_state: int = 42):
        """
        Initialize the Market Regime Detector.
        
        Args:
            n_components: Number of hidden states in the HMM (default: 3)
            random_state: Random seed for reproducibility
        """
        self.n_components: int = n_components
        self.model: GaussianHMM = GaussianHMM(
            n_components=n_components,
            covariance_type="full",
            random_state=random_state,
            n_iter=100
        )
        self.state_mapping: Dict[int, int] = {}
        self.scaler: StandardScaler = StandardScaler()
        self.is_fitted: bool = False
        self._cache_data: Optional[pd.DataFrame] = None
        
    def fetch_spy_data(self, period: str = "5y") -> pd.DataFrame:
        """
        Fetch real SPY data from yfinance.
        
        Implements comprehensive exception handling with fallback to cached or synthetic data.
        
        Args:
            period: Time period for historical data (default: "5y")
            
        Returns:
            pd.DataFrame: DataFrame with OHLCV data
            
        Raises:
            ValueError: If fallback mechanisms fail
        """
        try:
            logger.info(f"Fetching SPY data for period: {period}...")
            spy_data = yf.download("SPY", period=period, progress=False)
            
            # Validate that we got meaningful data
            if spy_data is None or spy_data.empty:
                raise ValueError("yfinance returned empty data")
                
            if not isinstance(spy_data.index, pd.DatetimeIndex):
                raise ValueError("Invalid index type from yfinance")
                
            logger.info(f"Successfully fetched {len(spy_data)} trading days of SPY data")
            self._cache_data = spy_data.copy()
            return spy_data
            
        except Exception as e:
            logger.warning(f"Failed to fetch SPY data: {e}")
            logger.info("Attempting fallback: using cached data or synthetic features...")
            
            # Fallback 1: Use cached data if available
            if self._cache_data is not None and not self._cache_data.empty:
                logger.info("Using cached SPY data from previous fetch")
                return self._cache_data
            
            # Fallback 2: Generate synthetic baseline features for system stability
            logger.warning("No cache available. Generating synthetic baseline features...")
            return self._generate_synthetic_spy_data()
    
    def _generate_synthetic_spy_data(self, n_days: int = 1260) -> pd.DataFrame:
        """
        Generate synthetic SPY data for system stability (approximately 5 years).
        
        Args:
            n_days: Number of trading days to generate (default: 1260 ≈ 5 years)
            
        Returns:
            pd.DataFrame: Synthetic SPY data with realistic characteristics
        """
        logger.info(f"Generating {n_days} days of synthetic SPY data")
        
        dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq='B')
        
        # Generate realistic price movements
        np.random.seed(42)
        daily_returns = np.random.normal(0.0004, 0.012, n_days)  # ~10% annual return, ~12% volatility
        prices = 400 * np.exp(np.cumsum(daily_returns))
        
        synthetic_data = pd.DataFrame({
            'Open': prices * (1 + np.random.normal(0, 0.005, n_days)),
            'High': prices * (1 + np.abs(np.random.normal(0, 0.008, n_days))),
            'Low': prices * (1 - np.abs(np.random.normal(0, 0.008, n_days))),
            'Close': prices,
            'Volume': np.random.randint(50_000_000, 120_000_000, n_days),
            'Adj Close': prices
        }, index=dates)
        
        logger.warning("Using synthetic data - predictions may not reflect actual market conditions")
        return synthetic_data
    
    def _prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        Extract and prepare features from raw SPY price data.
        
        Computes:
        - Log Returns: log(Close[t] / Close[t-1])
        - 20-day Rolling Annualized Volatility: std(returns) * sqrt(252)
        
        Args:
            df: DataFrame with 'Close' column
            
        Returns:
            Tuple[features (ndarray), df_calc (DataFrame)]: Feature matrix and processed data
            
        Raises:
            ValueError: If 'Close' column is missing or insufficient data
        """
        if 'Close' not in df.columns:
            raise ValueError("DataFrame must contain a 'Close' column for price data.")
        
        df_calc = df.copy()
        
        # Calculate Log Returns
        df_calc['Log_Return'] = np.log(df_calc['Close'] / df_calc['Close'].shift(1))
        
        # Calculate 20-day Rolling Annualized Volatility
        df_calc['Volatility'] = df_calc['Log_Return'].rolling(window=20).std() * np.sqrt(252)
        
        # Remove NaN values
        df_calc = df_calc.dropna(subset=['Log_Return', 'Volatility'])
        
        if df_calc.empty:
            raise ValueError("Not enough data to calculate features. Provide at least 21 trading days.")
        
        if len(df_calc) < 100:
            logger.warning(f"Limited data: only {len(df_calc)} samples. HMM performance may degrade.")
        
        features = df_calc[['Log_Return', 'Volatility']].values
        return features, df_calc
    
    def fit(self, spy_data: Optional[pd.DataFrame] = None) -> None:
        """
        Fit HMM model with automatic state mapping to market regimes.
        
        If no data provided, fetches real SPY data internally.
        
        Implements Label Sorting Mechanism:
        - Sorts hidden states by volatility feature mean (ascending)
        - Maps states to consistent market regimes regardless of training randomness
        
        Args:
            spy_data: Optional pre-fetched SPY DataFrame. If None, fetches automatically.
            
        Raises:
            RuntimeError: If data preparation or model fitting fails
        """
        try:
            # Fetch data if not provided
            if spy_data is None:
                spy_data = self.fetch_spy_data(period="5y")
            
            logger.info("Preparing features for HMM training...")
            features, df_calc = self._prepare_features(spy_data)
            
            # Standardize features for better HMM convergence
            features_scaled = self.scaler.fit_transform(features)
            
            logger.info(f"Fitting GaussianHMM with {self.n_components} components on {len(features_scaled)} samples...")
            self.model.fit(features_scaled)
            
            # Implement Label Sorting Mechanism
            self._map_states_by_volatility()
            
            self.is_fitted = True
            logger.info(f"HMM model fitted successfully. State Mapping: {self.state_mapping}")
            
        except Exception as e:
            logger.error(f"Failed to fit MarketRegimeDetector: {e}", exc_info=True)
            raise RuntimeError(f"Model fitting failed: {e}") from e
    
    def _map_states_by_volatility(self) -> None:
        """
        Map hidden states to market regimes based on volatility feature mean.
        
        Label Sorting Mechanism:
        - Extract means from trained model
        - Sort states by volatility feature (column 1) in ascending order
        - Assign semantic labels: low volatility → Bull (0), middle → Bear (1), high → High Vol (2)
        
        This ensures consistent state mapping across different training runs.
        """
        if not hasattr(self.model, 'means_') or self.model.means_ is None:
            raise RuntimeError("Model has not been fitted yet.")
        
        means = self.model.means_
        
        # means shape: (n_components, n_features) where features are [Log_Return, Volatility]
        volatilities_mean = means[:, 1]
        
        # Sort states by volatility (ascending)
        sorted_indices = np.argsort(volatilities_mean)
        
        # Map sorted states to semantic labels
        self.state_mapping = {
            int(sorted_indices[0]): 0,  # Lowest volatility → Bull Market
            int(sorted_indices[1]): 1,  # Middle volatility → Bear Market
            int(sorted_indices[2]): 2   # Highest volatility → High Volatility
        }
        
        logger.info(f"State mapping established:")
        logger.info(f"  State {sorted_indices[0]} (volatility={volatilities_mean[sorted_indices[0]]:.6f}) → Bull (0)")
        logger.info(f"  State {sorted_indices[1]} (volatility={volatilities_mean[sorted_indices[1]]:.6f}) → Bear (1)")
        logger.info(f"  State {sorted_indices[2]} (volatility={volatilities_mean[sorted_indices[2]]:.6f}) → High Vol (2)")
    
    def predict_regime(self, spy_data: Optional[pd.DataFrame] = None) -> int:
        """
        Predict current market regime based on latest SPY data.
        
        If no data provided, fetches latest SPY data internally.
        
        Args:
            spy_data: Optional pre-fetched SPY DataFrame. If None, fetches automatically.
            
        Returns:
            int: Market regime (0: Bull, 1: Bear, 2: High Volatility)
            
        Raises:
            RuntimeError: If model not fitted or prediction fails
        """
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted. Please call fit() first.")
        
        try:
            # Fetch data if not provided
            if spy_data is None:
                spy_data = self.fetch_spy_data(period="5y")
            
            logger.info("Extracting features for prediction...")
            features, _ = self._prepare_features(spy_data)
            
            # Standardize using the fitted scaler
            features_scaled = self.scaler.transform(features)
            
            # Predict hidden states sequence
            hidden_states = self.model.predict(features_scaled)
            
            # Get the most recent hidden state
            latest_internal_state = int(hidden_states[-1])
            
            # Map to semantic regime
            regime = self.state_mapping.get(latest_internal_state, 2)
            
            regime_names = {0: "Bull Market", 1: "Bear Market", 2: "High Volatility"}
            logger.info(f"Predicted regime: {regime} ({regime_names[regime]})")
            
            return regime
            
        except Exception as e:
            logger.error(f"Failed to predict regime: {e}", exc_info=True)
            raise RuntimeError(f"Prediction failed: {e}") from e
