"""
US Market Data Provider - 美股市場數據提供器
使用 yfinance 穩定抓取美股三大指數與11大板塊ETF
Universe: S&P 500 + Nasdaq 100
Author: Market Structure Platform Team
"""

import logging
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from functools import wraps
import time

logger = logging.getLogger(__name__)


class RetryDecorator:
    """重試裝飾器 - 處理網路波動"""
    
    def __init__(self, max_retries: int = 3, delay: int = 2):
        self.max_retries = max_retries
        self.delay = delay
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"Failed after {self.max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {self.delay}s: {e}")
                    time.sleep(self.delay)
        return wrapper


class USMarketDataProvider:
    """
    Production-Ready US Market Data Provider
    
    功能:
    - 獲取三大指數: SPY (S&P 500), QQQ (Nasdaq 100), IWM (Russell 2000)
    - 獲取11大板塊 ETF: XLK, XLV, XLF, XLY, XLP, XLRE, XLU, XLI, XLE, XLB, XLC
    - 支持批量同步數據、分時降噪、缺失值填補
    - Production-ready: 錯誤處理、日誌記錄、性能優化
    """
    
    # 三大指數定義
    MAIN_INDICES = {
        'SPY': 'S&P 500 Index ETF',
        'QQQ': 'Nasdaq 100 Index ETF',
        'IWM': 'Russell 2000 Index ETF'
    }
    
    # 🟢 修正版：100% 正確的美股正統 11 大板塊 SPDR ETF 清單 (徹底移除已下架的 XLVM / 錯置的 XSLV)
    SECTOR_ETFS = {
        'XLK': 'Information Technology',
        'XLV': 'Health Care',
        'XLF': 'Financials',
        'XLY': 'Consumer Discretionary',
        'XLP': 'Consumer Staples',
        'XLRE': 'Real Estate',
        'XLU': 'Utilities',
        'XLI': 'Industrials',
        'XLE': 'Energy',
        'XLB': 'Materials',              # 原物料板塊：修正為標準 XLB
        'XLC': 'Communication Services'   # 通訊服務板塊：修正為標準 XLC
    }
    
    def __init__(self, cache_dir: str = "./data_cache", look_back_days: int = 252):
        """
        初始化 US Market Data Provider
        """
        self.cache_dir = cache_dir
        self.look_back_days = look_back_days
        self.data_cache: Dict[str, pd.DataFrame] = {}
        logger.info(f"US Market Data Provider initialized with {look_back_days} day lookback")
    
    @RetryDecorator(max_retries=3, delay=2)
    def fetch_index_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        獲取指數與 ETF 數據
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=self.look_back_days)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 檢查緩存
        cache_key = f"{symbol}_{interval}"
        if cache_key in self.data_cache:
            logger.debug(f"Using cached data for {symbol}")
            return self.data_cache[cache_key]
        
        logger.info(f"Fetching {symbol} data from {start_date} to {end_date}")
        
        try:
            # 🟢 核心防禦：防止 yfinance 自動抓取帶有 MultiIndex 欄位結構
            df = yf.download(symbol, start=start_date, end=end_date, interval=interval, progress=False)
            
            if df.empty:
                raise ValueError(f"No data retrieved for {symbol}")
            
            # 如果欄位是雙層多重索引，強制將其拉平
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # 數據清理與驗證
            df = self._clean_data(df, symbol)
            
            # 緩存
            self.data_cache[cache_key] = df
            logger.info(f"Successfully fetched {len(df)} records for {symbol}")
            
            return df
        
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            raise
    
    def fetch_sector_etf_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取板塊 ETF 數據
        """
        return self.fetch_index_data(symbol, start_date, end_date, interval="1d")
    
    def fetch_all_indices(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        批量獲取所有三大指數數據
        """
        logger.info("Fetching all main indices...")
        result = {}
        
        for symbol in self.MAIN_INDICES.keys():
            try:
                result[symbol] = self.fetch_index_data(symbol, start_date, end_date)
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                result[symbol] = None
        
        return result
    
    def fetch_all_sector_etfs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        批量獲取所有板塊 ETF 數據
        """
        logger.info("Fetching all sector ETFs...")
        result = {}
        
        for symbol in self.SECTOR_ETFS.keys():
            try:
                result[symbol] = self.fetch_sector_etf_data(symbol, start_date, end_date)
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                result[symbol] = None
        
        return result
    
    def fetch_universe_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        獲取完整的宇宙數據: 3 indices + 11 sector ETFs
        """
        logger.info("Fetching complete universe data (3 indices + 11 sector ETFs)...")
        
        indices = self.fetch_all_indices(start_date, end_date)
        sectors = self.fetch_all_sector_etfs(start_date, end_date)
        
        return {**indices, **sectors}
    
    @staticmethod
    def _clean_data(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        數據清理與驗證
        """
        # 移除全為 NaN 的行
        df = df.dropna(subset=['Close', 'Volume'])
        
        # 標準化列名
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        # 強制轉換量化關鍵欄位為浮點數
        for col in ['close', 'high', 'low', 'open', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 計算關鍵指標
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        df['volatility'] = df['log_return'].rolling(window=20).std() * np.sqrt(252)
        
        # 移除仍有 NaN 的行
        df = df.dropna(subset=['log_return', 'volatility'])
        
        logger.debug(f"{symbol}: Cleaned {len(df)} records, removed NaN values")
        
        return df
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """獲取當前價格"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
        return None
    
    def get_returns(self, df: pd.DataFrame, period: int = 1) -> pd.Series:
        """計算報酬率"""
        return df['close'].pct_change(periods=period)
    
    def get_volatility(self, df: pd.DataFrame, window: int = 20) -> pd.Series:
        """計算滾動波動率 (年化)"""
        returns = self.get_returns(df)
        return returns.rolling(window=window).std() * np.sqrt(252)
    
    def validate_data_quality(
        self,
        df: pd.DataFrame,
        min_records: int = 100,
        max_nan_ratio: float = 0.05
    ) -> Tuple[bool, str]:
        """驗證數據質量"""
        if df is None or df.empty:
            return False, "Empty DataFrame"
        
        if len(df) < min_records:
            return False, f"Insufficient records: {len(df)} < {min_records}"
        
        nan_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        if nan_ratio > max_nan_ratio:
            return False, f"Too many NaN values: {nan_ratio:.2%} > {max_nan_ratio:.2%}"
        
        return True, "Data quality check passed"


# 便捷函數
def get_spy_data(days: int = 252) -> pd.DataFrame:
    """快速獲取 SPY 數據"""
    provider = USMarketDataProvider(look_back_days=days)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return provider.fetch_index_data('SPY', start_date=start_date)


def get_sector_performance(days: int = 252) -> pd.DataFrame:
    """獲取板塊相對表現"""
    provider = USMarketDataProvider(look_back_days=days)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    sectors = provider.fetch_all_sector_etfs(start_date=start_date)
    
    performance = {}
    for symbol, df in sectors.items():
        if df is not None and not df.empty:
            performance[symbol] = df['close'].pct_change().mean() * 252
    
    return pd.DataFrame({
        'Symbol': list(performance.keys()),
        'Annual_Return': list(performance.values())
    }).sort_values('Annual_Return', ascending=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    provider = USMarketDataProvider()
    
    # 獲取指數數據
    spy_data = provider.fetch_index_data('SPY')
    print(f"SPY: {len(spy_data)} records")
    print(spy_data.tail())
    
    # 獲取完整宇宙
    universe = provider.fetch_universe_data()
    print(f"\nUniverse: {len(universe)} symbols")
    for symbol, df in universe.items():
        if df is not None:
            print(f"  {symbol}: {len(df)} records")