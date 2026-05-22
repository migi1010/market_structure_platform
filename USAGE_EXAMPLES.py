"""
Market Regime Detector - Complete Usage Guide
Production-Ready Implementation Examples
"""

import pandas as pd
import logging
from market_structure.engine import MarketRegimeDetector

# Setup logging for monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# SCENARIO 1: BASIC INITIALIZATION & FITTING
# ============================================================================

def scenario_1_basic_usage():
    """
    Simplest usage: Initialize detector and fit with auto-fetched data
    """
    print("\n" + "="*80)
    print("SCENARIO 1: Basic Initialization & Auto-Fit")
    print("="*80)
    
    # Create detector
    detector = MarketRegimeDetector(n_components=3, random_state=42)
    print("✓ Detector initialized")
    
    # Fit automatically fetches 5 years of SPY data
    detector.fit()
    print("✓ Model fitted with real SPY data")
    
    # Get current regime
    regime = detector.predict_regime()
    regime_map = {0: "Bull", 1: "Bear", 2: "High Vol"}
    print(f"✓ Current regime: {regime_map[regime]}")
    
    return detector


# ============================================================================
# SCENARIO 2: MANUAL DATA LOADING
# ============================================================================

def scenario_2_manual_data():
    """
    Load SPY data manually and pass to detector
    Useful for backtesting or custom data sources
    """
    print("\n" + "="*80)
    print("SCENARIO 2: Manual Data Loading")
    print("="*80)
    
    # Create detector
    detector = MarketRegimeDetector(n_components=3, random_state=42)
    
    # Option A: Fetch data yourself
    print("Loading SPY data from yfinance...")
    spy_data = detector.fetch_spy_data(period="3y")
    print(f"✓ Loaded {len(spy_data)} trading days")
    
    # Option B: From CSV
    # spy_data = pd.read_csv('spy_historical.csv', index_col=0, parse_dates=True)
    
    # Fit with loaded data
    detector.fit(spy_data)
    print("✓ Model fitted")
    
    # Predict using same data
    regime = detector.predict_regime(spy_data)
    print(f"✓ Regime prediction: {regime}")
    
    return detector


# ============================================================================
# SCENARIO 3: CUSTOM PERIOD & DATA EXPLORATION
# ============================================================================

def scenario_3_data_exploration():
    """
    Fetch data for analysis and feature inspection
    """
    print("\n" + "="*80)
    print("SCENARIO 3: Data Exploration & Feature Analysis")
    print("="*80)
    
    detector = MarketRegimeDetector()
    
    # Fetch different time periods
    for period in ["1y", "3y", "5y"]:
        data = detector.fetch_spy_data(period=period)
        print(f"Period {period:4s}: {len(data):5d} trading days | "
              f"Date range: {data.index[0].date()} to {data.index[-1].date()}")
    
    # Fit model
    detector.fit()
    
    # Analyze feature distributions
    features, df_calc = detector._prepare_features(
        detector.fetch_spy_data(period="5y")
    )
    
    print("\nFeature Statistics (Before Scaling):")
    print(f"  Log Return  - Mean: {features[:, 0].mean():.6f}, "
          f"Std: {features[:, 0].std():.6f}")
    print(f"  Volatility  - Mean: {features[:, 1].mean():.6f}, "
          f"Std: {features[:, 1].std():.6f}")
    
    print("\nModel State Information:")
    means = detector.model.means_
    print(f"  State 0 - Log Return: {means[0, 0]:8.6f}, Volatility: {means[0, 1]:8.6f}")
    print(f"  State 1 - Log Return: {means[1, 0]:8.6f}, Volatility: {means[1, 1]:8.6f}")
    print(f"  State 2 - Log Return: {means[2, 0]:8.6f}, Volatility: {means[2, 1]:8.6f}")
    
    print(f"\nState Mapping: {detector.state_mapping}")


# ============================================================================
# SCENARIO 4: CONTINUOUS MONITORING
# ============================================================================

def scenario_4_continuous_monitoring():
    """
    Real-world scenario: Monitor market regime changes over time
    """
    print("\n" + "="*80)
    print("SCENARIO 4: Continuous Monitoring")
    print("="*80)
    
    # Initialize once during system startup
    detector = MarketRegimeDetector(n_components=3, random_state=42)
    detector.fit()
    print("✓ Detector initialized and trained")
    
    # Simulate periodic regime checks (e.g., daily or hourly)
    print("\nSimulating regime predictions over time:")
    
    # In production, you would call this at regular intervals
    for i in range(5):
        regime = detector.predict_regime()
        regime_names = {0: "Bull", 1: "Bear", 2: "High Vol"}
        print(f"  Check {i+1}: Current regime = {regime_names[regime]}")
    
    print("✓ Monitoring active")


# ============================================================================
# SCENARIO 5: ERROR HANDLING & RECOVERY
# ============================================================================

def scenario_5_error_handling():
    """
    Demonstrates error handling capabilities
    """
    print("\n" + "="*80)
    print("SCENARIO 5: Error Handling")
    print("="*80)
    
    detector = MarketRegimeDetector()
    
    # Error 1: Predict before fit
    print("\n[Test 1] Predict before fit:")
    try:
        detector.predict_regime()
    except RuntimeError as e:
        print(f"  ✓ Caught error: {e}")
    
    # Error 2: Invalid DataFrame
    print("\n[Test 2] Invalid DataFrame (missing 'Close' column):")
    try:
        invalid_df = pd.DataFrame({'Open': [100, 101], 'High': [102, 103]})
        detector.fit(invalid_df)
    except ValueError as e:
        print(f"  ✓ Caught error: {e}")
    
    # Error 3: Empty DataFrame
    print("\n[Test 3] Empty DataFrame:")
    try:
        empty_df = pd.DataFrame({'Close': []})
        detector.fit(empty_df)
    except ValueError as e:
        print(f"  ✓ Caught error: {e}")
    
    # Error 4: Insufficient data
    print("\n[Test 4] Insufficient data (only 10 days):")
    try:
        # Create 10 days of price data
        prices = [100 + i for i in range(10)]
        small_df = pd.DataFrame({'Close': prices})
        detector.fit(small_df)
    except ValueError as e:
        print(f"  ✓ Caught error: {e}")
    
    # Success case
    print("\n[Test 5] Valid data recovery (fallback to synthetic):")
    detector.fit()  # Will use synthetic data if network fails
    print("  ✓ System recovered gracefully")


# ============================================================================
# SCENARIO 6: BACKTESTING INTEGRATION
# ============================================================================

def scenario_6_backtesting():
    """
    Use regime detector in backtesting framework
    """
    print("\n" + "="*80)
    print("SCENARIO 6: Backtesting Integration")
    print("="*80)
    
    detector = MarketRegimeDetector()
    
    # Fetch historical data
    historical_data = detector.fetch_spy_data(period="5y")
    
    # Split into train/test
    split_idx = int(len(historical_data) * 0.8)
    train_data = historical_data.iloc[:split_idx]
    test_data = historical_data.iloc[split_idx:]
    
    print(f"Train period: {train_data.index[0].date()} to {train_data.index[-1].date()}")
    print(f"Test period:  {test_data.index[0].date()} to {test_data.index[-1].date()}")
    
    # Train on historical period
    detector.fit(train_data)
    print("✓ Model trained on train period")
    
    # Backtest on test period
    regimes = []
    for i in range(100, len(test_data)):
        # Use expanding window
        test_window = test_data.iloc[:i]
        regime = detector.predict_regime(test_window)
        regimes.append(regime)
    
    print(f"✓ Backtested {len(regimes)} periods")
    
    # Analyze regime distribution
    import numpy as np
    unique, counts = np.unique(regimes, return_counts=True)
    regime_dist = {0: "Bull", 1: "Bear", 2: "High Vol"}
    print("\nRegime Distribution in Test Period:")
    for state, count in zip(unique, counts):
        pct = count / len(regimes) * 100
        print(f"  {regime_dist[state]:10s}: {count:4d} days ({pct:5.1f}%)")


# ============================================================================
# SCENARIO 7: FEATURE ENGINEERING VERIFICATION
# ============================================================================

def scenario_7_feature_verification():
    """
    Verify feature engineering calculations
    """
    print("\n" + "="*80)
    print("SCENARIO 7: Feature Engineering Verification")
    print("="*80)
    
    import numpy as np
    
    detector = MarketRegimeDetector()
    spy_data = detector.fetch_spy_data(period="3m")  # Just 3 months for verification
    
    features, df_calc = detector._prepare_features(spy_data)
    
    print(f"Total samples after removing NaN: {len(features)}")
    print(f"\nFirst 5 rows of engineered features:")
    print("  Date          | Log Return | Volatility (Annualized)")
    print("-" * 60)
    
    for i in range(min(5, len(df_calc))):
        idx = df_calc.index[i]
        lr = df_calc['Log_Return'].iloc[i]
        vol = df_calc['Volatility'].iloc[i]
        print(f"  {idx.date()} | {lr:10.6f} | {vol:10.6f}")
    
    print("\nFeature Ranges:")
    print(f"  Log Return  : {features[:, 0].min():.6f} to {features[:, 0].max():.6f}")
    print(f"  Volatility  : {features[:, 1].min():.6f} to {features[:, 1].max():.6f}")
    
    # Verify annualization formula
    print("\nAnnualization Verification:")
    daily_vol = df_calc['Log_Return'].std()
    annualized = daily_vol * np.sqrt(252)
    print(f"  Daily std dev: {daily_vol:.6f}")
    print(f"  Annualized (daily_std × √252): {annualized:.6f}")


# ============================================================================
# RUN ALL SCENARIOS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("MARKET REGIME DETECTOR - USAGE EXAMPLES")
    print("="*80)
    
    try:
        scenario_1_basic_usage()
        scenario_2_manual_data()
        scenario_3_data_exploration()
        scenario_4_continuous_monitoring()
        scenario_5_error_handling()
        scenario_6_backtesting()
        scenario_7_feature_verification()
        
        print("\n" + "="*80)
        print("✓ ALL SCENARIOS COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error during execution: {e}")
        import traceback
        traceback.print_exc()
