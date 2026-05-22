"""
Data Provider Base Module - Multi-Source Data Integration
支持 yfinance, AkShare, Tushare, YahooFinance 等多數據源
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataProviderBase(ABC):
    """
    數據提供者基類
    定義通用的數據獲取介面
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"DataProvider.{name}")
    
    @abstractmethod
    def fetch_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        獲取股票數據
        
        Args:
            symbol: 股票代碼 (e.g., "AAPL", "600519", "hk00700")
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            interval: 數據間隔 ("1d", "1h", "5m" 等)
        
        Returns:
            pd.DataFrame: OHLCV 數據
        """
        pass
    
    @abstractmethod
    def fetch_market_index(
        self,
        index_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取市場指數數據
        
        Args:
            index_code: 指數代碼 (e.g., "000001.SH" for 上證, "^GSPC" for SPX)
            start_date: 開始日期
            end_date: 結束日期
        
        Returns:
            pd.DataFrame: 指數 OHLCV 數據
        """
        pass
    
    @abstractmethod
    def search_stocks(self, query: str) -> List[Dict[str, str]]:
        """
        搜索股票
        
        Args:
            query: 搜索關鍵字 (代碼、名稱、拼音等)
        
        Returns:
            List[Dict]: 匹配的股票列表
        """
        pass
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """驗證數據完整性"""
        if df is None or df.empty:
            self.logger.warning(f"Empty data from {self.name}")
            return False
        
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            self.logger.warning(f"Missing required columns in {self.name}")
            return False
        
        return True
    
    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """標準化列名"""
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        # 確保標準列存在
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        existing_cols = set(df.columns)
        
        if not required_cols.issubset(existing_cols):
            self.logger.warning(f"Standard columns not complete: {required_cols - existing_cols}")
        
        return df


class YFinanceProvider(DataProviderBase):
    """YFinance 數據提供者"""
    
    def __init__(self):
        super().__init__("YFinance")
        try:
            import yfinance as yf
            self.yf = yf
        except ImportError:
            self.logger.error("yfinance not installed")
            raise
    
    def fetch_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """從 YFinance 獲取股票數據"""
        try:
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            self.logger.info(f"Fetching {symbol} from {start_date} to {end_date}")
            
            data = self.yf.download(
                symbol,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False
            )
            
            if self.validate_data(data):
                return self.normalize_columns(data)
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_market_index(
        self,
        index_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """獲取市場指數"""
        return self.fetch_stock_data(index_code, start_date, end_date)
    
    def search_stocks(self, query: str) -> List[Dict[str, str]]:
        """搜索股票 (YFinance 無原生搜索, 返回空列表)"""
        return []


class AkShareProvider(DataProviderBase):
    """AkShare 數據提供者"""
    
    def __init__(self):
        super().__init__("AkShare")
        try:
            import akshare as ak
            self.ak = ak
        except ImportError:
            self.logger.error("akshare not installed")
            raise
    
    def fetch_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """從 AkShare 獲取 A 股數據"""
        try:
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y%m%d")
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            
            self.logger.info(f"Fetching {symbol} from AkShare")
            
            # AkShare 日K線
            data = self.ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前複權
            )
            
            if data is not None and not data.empty:
                # 重命名列
                data.columns = ['Date', 'Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 'Rate']
                data['Date'] = pd.to_datetime(data['Date'])
                data = data.set_index('Date').sort_index()
                return self.normalize_columns(data)
            
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_market_index(
        self,
        index_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """獲取市場指數"""
        try:
            # 大盤指數代碼: 000001 (上證), 399001 (深成), 399006 (創業板)
            data = self.ak.stock_zh_index_daily(
                symbol=f"sh{index_code}" if index_code.startswith("0") else index_code
            )
            if data is not None and not data.empty:
                data['日期'] = pd.to_datetime(data['日期'])
                data = data.set_index('日期').sort_index()
                return self.normalize_columns(data)
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error fetching index {index_code}: {e}")
            return pd.DataFrame()
    
    def search_stocks(self, query: str) -> List[Dict[str, str]]:
        """搜索 A 股"""
        try:
            data = self.ak.stock_info_a_sina()
            results = data[
                (data['代码'].str.contains(query, na=False)) |
                (data['名称'].str.contains(query, na=False))
            ]
            return [
                {"symbol": row['代码'], "name": row['名称']}
                for _, row in results.iterrows()
            ]
        except Exception as e:
            self.logger.error(f"Error searching stocks: {e}")
            return []


class DataProviderManager:
    """
    數據提供者管理器
    管理多數據源，自動降級與故障轉移
    """
    
    def __init__(self):
        self.providers: Dict[str, DataProviderBase] = {}
        self.priority_order: List[str] = []
        self.logger = logging.getLogger("DataProviderManager")
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化所有可用的提供者"""
        providers_config = [
            ("yfinance", YFinanceProvider),
            ("akshare", AkShareProvider),
        ]
        
        for name, provider_class in providers_config:
            try:
                self.providers[name] = provider_class()
                self.priority_order.append(name)
                self.logger.info(f"✓ {name} provider initialized")
            except Exception as e:
                self.logger.warning(f"✗ {name} provider failed: {e}")
    
    def fetch_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
        preferred_provider: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取股票數據，支持故障轉移
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            interval: 數據間隔
            preferred_provider: 優先提供者
        
        Returns:
            pd.DataFrame: 股票數據 (優先級: 優先 → 其他可用提供者)
        """
        
        # 決定提供者順序
        providers_to_try = []
        if preferred_provider and preferred_provider in self.providers:
            providers_to_try.append(preferred_provider)
        
        for name in self.priority_order:
            if name not in providers_to_try:
                providers_to_try.append(name)
        
        # 嘗試每個提供者
        for provider_name in providers_to_try:
            try:
                provider = self.providers[provider_name]
                data = provider.fetch_stock_data(symbol, start_date, end_date, interval)
                
                if not data.empty:
                    self.logger.info(f"✓ Got {symbol} data from {provider_name}")
                    return data
                
            except Exception as e:
                self.logger.warning(f"✗ {provider_name} failed for {symbol}: {e}")
                continue
        
        self.logger.error(f"✗ Failed to fetch {symbol} from all providers")
        return pd.DataFrame()
    
    def fetch_market_index(
        self,
        index_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> pd.DataFrame:
        """獲取市場指數，支持故障轉移"""
        
        providers_to_try = []
        if preferred_provider and preferred_provider in self.providers:
            providers_to_try.append(preferred_provider)
        
        for name in self.priority_order:
            if name not in providers_to_try:
                providers_to_try.append(name)
        
        for provider_name in providers_to_try:
            try:
                provider = self.providers[provider_name]
                data = provider.fetch_market_index(index_code, start_date, end_date)
                
                if not data.empty:
                    return data
            except Exception as e:
                self.logger.debug(f"{provider_name} failed for index {index_code}: {e}")
                continue
        
        return pd.DataFrame()
