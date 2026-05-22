"""
Market Structure HMM Engine - 市場體制隱馬可夫模型
使用 GaussianHMM 進行市場狀態分類
Regime: 0 = Bull Market, 1 = Bear Market, 2 = High Volatility
Author: Market Structure Platform Team
"""

import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timedelta
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
import pickle
import os

logger = logging.getLogger(__name__)


class MarketRegimeHMM:
    """
    Production-Ready Market Regime HMM Engine
    
    使用 SPY 日線報酬率與波動率訓練 GaussianHMM
    
    Regime 定義:
    - Regime 0: Bull Market (低波動牛市)
    - Regime 1: Bear Market (熊市)
    - Regime 2: High Volatility (高波動震盪)
    """
    
    def __init__(
        self,
        n_components: int = 3,
        covariance_type: str = "full",
        random_state: int = 42,
        n_iter: int = 100,
        model_path: Optional[str] = None
    ):
        """
        初始化 HMM 模型
        """
        self.n_components = n_components
        self.covariance_type = covariance_type
        self.random_state = random_state
        self.n_iter = n_iter
        
        self.model = GaussianHMM(
            n_components=n_components,
            covariance_type=covariance_type,
            random_state=random_state,
            n_iter=n_iter
        )
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.regime_mapping: Dict[int, str] = {}
        self.training_data: Optional[pd.DataFrame] = None
        self.last_training_date: Optional[datetime] = None
        
        # 載入預訓練模型
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
            
        logger.info(f"MarketRegimeHMM initialized with {n_components} components")
    
    def fetch_spy_data(
        self,
        period: str = "5y",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取 SPY 數據
        """
        logger.info(f"Fetching SPY data for period: {period}")
        
        try:
            if start_date and end_date:
                df = yf.download('SPY', start=start_date, end=end_date, progress=False)
            else:
                df = yf.download('SPY', period=period, progress=False)
            
            if df.empty:
                raise ValueError("No data retrieved for SPY")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching SPY data: {e}")
            raise
    
    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        準備訓練特徵: 日報酬率 + 20日波動率 (完美相容 yfinance MultiIndex 與二維 DataFrame 衝突)
        """
        df_cleaned = df.copy()
        
        # 🟢 核心防禦 1：如果 yfinance 帶有雙層欄位 (MultiIndex)，強制將其拉平成單層
        if isinstance(df_cleaned.columns, pd.MultiIndex):
            df_cleaned.columns = df_cleaned.columns.get_level_values(0)
            
        # 🟢 核心防禦 2：強制將 Series/DataFrame 轉為標準一維的 Float64 Series，阻斷二維衝突
        close_series = pd.to_numeric(df_cleaned['Close'].squeeze(), errors='coerce')
        
        # 計算日報酬率 (確保是一維 Series)
        returns = np.log(close_series / close_series.shift(1)).dropna()
        
        # 計算 20 日滾動波動率 (年化)
        volatility = returns.rolling(window=20).std() * np.sqrt(252)
        
        # 🟢 核心防禦 3：使用標準的 pd.concat 對齊一維 Series，絕對不使用 {} 字典建置！
        features_df = pd.concat({'returns': returns, 'volatility': volatility}, axis=1).dropna()
        
        logger.info(f"Prepared {len(features_df)} samples for training")
        
        # 強制以標準的 NumPy float64 二維矩陣輸出
        return np.asarray(features_df[['returns', 'volatility']].values, dtype=np.float64)
    
    def train(
        self,
        period: str = "5y",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, any]:
        """
        訓練 HMM 模型
        """
        logger.info(f"Training MarketRegimeHMM...")
        
        # 獲取 SPY 數據
        df = self.fetch_spy_data(period=period, start_date=start_date, end_date=end_date)
        
        # 準備特徵
        features = self.prepare_features(df)
        
        # 標準化
        features_scaled = self.scaler.fit_transform(features)
        
        # 訓練模型
        self.model.fit(features_scaled)
        
        # 獲取轉移矩陣與發射矩陣
        transition_matrix = self.model.transmat_
        means = self.model.means_
        
        # 排序 Regime (按波動率大小)
        volatility_order = means[:, 1].argsort()
        self.regime_mapping = {
            volatility_order[0]: 'Bull Market (Low Vol)',
            volatility_order[1]: 'High Volatility',
            volatility_order[2]: 'Bear Market (High Vol)'
        }
        
        # 🟢 終極版屬性防禦：相容 hmmlearn 庫所有已知版本 (covariances_, covars_, covariance_)
        if hasattr(self.model, 'covariance_'):
            current_covars = self.model.covariance_
            self.model.covariance_ = current_covars[volatility_order]
        elif hasattr(self.model, 'covariances_'):
            current_covars = self.model.covariances_
            self.model.covariances_ = current_covars[volatility_order]
        elif hasattr(self.model, 'covars_'):
            current_covars = self.model.covars_
            self.model.covars_ = current_covars[volatility_order]
            
        # 重排其餘模型參數
        self.model.means_ = means[volatility_order]
        self.model.transmat_ = transition_matrix[volatility_order][:, volatility_order]
        self.is_fitted = True
        self.training_data = features
        self.last_training_date = datetime.now()
        
        result = {
            'score': self.model.score(features_scaled),
            'means': self.model.means_,
            'converged': self.model.monitor_.converged,
            'n_iter': self.model.monitor_.iter,
            'transmat': transition_matrix,
            'regime_mapping': self.regime_mapping
        }
        
        logger.info(f"Training completed. Score: {result['score']:.4f}")
        logger.info(f"Regime Mapping: {self.regime_mapping}")
        
        return result
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        預測當前市場狀態
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call train() first.")
        
        features = self.prepare_features(df)
        features_scaled = self.scaler.transform(features)
        
        predictions = self.model.predict(features_scaled)
        
        return predictions
    
    def predict_current_regime(self) -> Tuple[int, str, float]:
        """
        預測當前市場狀態 (實時)
        """
        # 獲取最近 120 天數據，確保有足夠的 Bar 計算 20 日滾動年化波動率
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
        
        df = self.fetch_spy_data(start_date=start_date, end_date=end_date)
        
        # 預測
        predictions = self.predict(df)
        current_regime = int(predictions[-1])
        regime_name = self.regime_mapping.get(
            current_regime,
            f"Unknown (State {current_regime})"
        )
        
        # 計算信心度 (最近 5 天相同狀態的比例)
        recent_regimes = predictions[-5:]
        confidence = float(np.sum(recent_regimes == current_regime) / len(recent_regimes))
        
        logger.info(f"Current Regime: {current_regime} ({regime_name}), Confidence: {confidence:.2%}")
        
        return current_regime, regime_name, confidence
    
    def get_regime_probabilities(self, df: pd.DataFrame) -> np.ndarray:
        """獲取各 Regime 的概率"""
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call train() first.")
        
        features = self.prepare_features(df)
        features_scaled = self.scaler.transform(features)
        probabilities = self.model.predict_proba(features_scaled)
        
        return probabilities
    
    def get_transition_matrix(self) -> pd.DataFrame:
        """獲取狀態轉移矩陣"""
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call train() first.")
        
        regime_names = [self.regime_mapping[i] for i in range(self.n_components)]
        
        return pd.DataFrame(
            self.model.transmat_,
            index=regime_names,
            columns=regime_names
        )
    
    def get_model_parameters(self) -> Dict[str, any]:
        """獲取模型參數"""
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call train() first.")
        
        return {
            'n_components': self.n_components,
            'covariance_type': self.covariance_type,
            'means': self.model.means_.tolist(),
            'covariances': self.model.covariances_.tolist(),
            'transmat': self.model.transmat_.tolist(),
            'weights': self.model.weights_.tolist(),
            'regime_mapping': self.regime_mapping,
            'last_training_date': self.last_training_date.isoformat() if self.last_training_date else None
        }
    
    def save_model(self, model_path: str) -> bool:
        """儲存模型"""
        if not self.is_fitted:
            logger.warning("Model not fitted. Cannot save.")
            return False
        
        try:
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'regime_mapping': self.regime_mapping,
                'last_training_date': self.last_training_date
            }
            
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, model_path: str) -> bool:
        """載入模型"""
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.regime_mapping = model_data['regime_mapping']
            self.last_training_date = model_data['last_training_date']
            self.is_fitted = True
            
            logger.info(f"Model loaded from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def should_retrain(self, days_threshold: int = 30) -> bool:
        """判斷是否應該重新訓練模型"""
        if not self.is_fitted or self.last_training_date is None:
            return True
        
        days_since_training = (datetime.now() - self.last_training_date).days
        return days_since_training >= days_threshold


# 便捷函數
def get_market_regime_realtime() -> Tuple[int, str, float]:
    """實時獲取市場狀態"""
    hmm = MarketRegimeHMM()
    
    # 檢查是否有預訓練模型
    model_path = "./models/market_regime_hmm.pkl"
    if os.path.exists(model_path):
        hmm.load_model(model_path)
        if not hmm.should_retrain():
            return hmm.predict_current_regime()
    
    # 訓練新模型
    hmm.train(period="5y")
    hmm.save_model(model_path)
    
    return hmm.predict_current_regime()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 訓練 HMM 模型
    hmm = MarketRegimeHMM()
    
    logger.info("Starting HMM training...")
    result = hmm.train(period="5y")
    
    # 輸出訓練結果
    logger.info(f"Training Score: {result['score']:.4f}")
    logger.info(f"Model Converged: {result['converged']}")
    logger.info(f"Iterations: {result['n_iter']}")
    
    # 獲取轉移矩陣
    transition_df = hmm.get_transition_matrix()
    logger.info(f"\nTransition Matrix:\n{transition_df}")
    
    # 預測當前狀態
    regime, name, confidence = hmm.predict_current_regime()
    logger.info(f"\nCurrent Regime: {regime} ({name})")
    logger.info(f"Confidence: {confidence:.2%}")
    
    # 儲存模型
    hmm.save_model("./models/market_regime_hmm.pkl")