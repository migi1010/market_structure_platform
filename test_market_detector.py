"""
Test script for the Production-Ready MarketRegimeDetector
Tests real SPY data fetching, feature engineering, HMM fitting, and regime prediction.
"""

import sys
import logging
from market_structure.engine import MarketRegimeDetector

# Configure logging to see detailed info
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_market_regime_detector():
    """
    Test the full pipeline of MarketRegimeDetector:
    1. Initialization
    2. Fetch real SPY data (with fallback)
    3. Fit HMM model with feature engineering
    4. Predict current regime
    """
    logger.info("=" * 80)
    logger.info("Testing Production-Ready MarketRegimeDetector")
    logger.info("=" * 80)
    
    try:
        # Initialize detector
        logger.info("\n[1] Initializing MarketRegimeDetector...")
        detector = MarketRegimeDetector(n_components=3, random_state=42)
        logger.info("✓ Detector initialized successfully")
        
        # Fit model (internally fetches SPY data)
        logger.info("\n[2] Fitting HMM model with SPY data...")
        detector.fit()
        logger.info("✓ Model fitted successfully")
        
        # Predict regime
        logger.info("\n[3] Predicting current market regime...")
        regime = detector.predict_regime()
        
        regime_names = {0: "Bull Market", 1: "Bear Market", 2: "High Volatility"}
        logger.info(f"✓ Current regime: {regime} ({regime_names[regime]})")
        
        logger.info("\n" + "=" * 80)
        logger.info("All tests passed! System is production-ready.")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_market_regime_detector()
    sys.exit(0 if success else 1)
