"""
Dynamic Alpha Factor Engine - 動態 Alpha 因子評分系統
支持多因子計算 (Quality, Growth, Valuation, Momentum, SmartMoney)
HMM Dynamic Weighting 機制 - 根據市場狀態動態調整因子權重
Author: Market Structure Platform Team
"""

import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


class FactorCalculator:
    """因子計算器"""
    
    @staticmethod
    def calculate_quality_factors(ticker_symbol: str) -> Dict[str, float]:
        """
        計算質量因子 (Quality Factors)
        - ROIC: Return on Invested Capital
        - ROE: Return on Equity
        - Debt Ratio: 負債比率
        
        Args:
            ticker_symbol: 股票代碼
        
        Returns:
            Dict: 質量因子字典
        """
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            # 從 Yahoo Finance 提取財務指標
            roic = info.get('returnOnCapital', None)
            roe = info.get('returnOnEquity', None)
            
            # 計算負債比率
            total_debt = info.get('totalDebt', 0) or 0
            total_equity = info.get('totalEquity', 1) or 1
            debt_ratio = total_debt / total_equity if total_equity != 0 else 0
            
            # 標準化 (0-100)
            roic_normalized = (roic * 100) if roic else 50  # 假設無數據時為中位數
            roe_normalized = (roe * 100) if roe else 50
            debt_normalized = (1 - debt_ratio) * 100  # 低負債更優
            
            quality_score = (roic_normalized + roe_normalized + debt_normalized) / 3
            
            return {
                'roic': roic_normalized,
                'roe': roe_normalized,
                'debt_ratio': debt_normalized,
                'quality_score': quality_score
            }
        
        except Exception as e:
            logger.warning(f"Error calculating quality factors for {ticker_symbol}: {e}")
            return {
                'roic': 50,
                'roe': 50,
                'debt_ratio': 50,
                'quality_score': 50
            }
    
    @staticmethod
    def calculate_growth_factors(ticker_symbol: str, period: int = 252) -> Dict[str, float]:
        """
        計算成長因子 (Growth Factors)
        - Revenue Growth: 營收增長
        - EPS Growth: EPS 增長
        - Earnings Estimate: 盈利預測
        
        Args:
            ticker_symbol: 股票代碼
            period: 回看週期 (交易日)
        
        Returns:
            Dict: 成長因子字典
        """
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            # 營收與 EPS 增長
            revenue_growth = info.get('revenueGrowth', 0) or 0
            earnings_growth = info.get('earningsGrowth', 0) or 0
            
            # 盈利預測
            earnings_estimate = info.get('epsTrailingTwelveMonths', 0) or 0
            
            # 標準化 (0-100)
            revenue_normalized = (revenue_growth * 100) + 50  # 區間 [-50, 150]
            revenue_normalized = np.clip(revenue_normalized, 0, 100)
            
            earnings_normalized = (earnings_growth * 100) + 50
            earnings_normalized = np.clip(earnings_normalized, 0, 100)
            
            growth_score = (revenue_normalized + earnings_normalized) / 2
            
            return {
                'revenue_growth': revenue_normalized,
                'earnings_growth': earnings_normalized,
                'growth_score': growth_score
            }
        
        except Exception as e:
            logger.warning(f"Error calculating growth factors for {ticker_symbol}: {e}")
            return {
                'revenue_growth': 50,
                'earnings_growth': 50,
                'growth_score': 50
            }
    
    @staticmethod
    def calculate_valuation_factors(ticker_symbol: str) -> Dict[str, float]:
        """
        計算估值因子 (Valuation Factors)
        - PE Ratio: 市盈率
        - PS Ratio: 市銷率
        - PB Ratio: 市淨率
        
        Args:
            ticker_symbol: 股票代碼
        
        Returns:
            Dict: 估值因子字典
        """
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            pe_ratio = info.get('trailingPE', 20) or 20
            ps_ratio = info.get('priceToSalesTrailingTwelveMonths', 2) or 2
            pb_ratio = info.get('priceToBook', 3) or 3
            
            # 反轉標準化 (低 PE/PS/PB 更優)
            # 使用百分比排名 (假設 P/E 在 10-30 是正常範圍)
            pe_normalized = (1 - (pe_ratio - 10) / 20) * 100
            pe_normalized = np.clip(pe_normalized, 0, 100)
            
            ps_normalized = (1 - (ps_ratio - 0.5) / 3.5) * 100
            ps_normalized = np.clip(ps_normalized, 0, 100)
            
            pb_normalized = (1 - (pb_ratio - 1) / 4) * 100
            pb_normalized = np.clip(pb_normalized, 0, 100)
            
            valuation_score = (pe_normalized + ps_normalized + pb_normalized) / 3
            
            return {
                'pe_ratio': pe_normalized,
                'ps_ratio': ps_normalized,
                'pb_ratio': pb_normalized,
                'valuation_score': valuation_score
            }
        
        except Exception as e:
            logger.warning(f"Error calculating valuation factors for {ticker_symbol}: {e}")
            return {
                'pe_ratio': 50,
                'ps_ratio': 50,
                'pb_ratio': 50,
                'valuation_score': 50
            }
    
    @staticmethod
    def calculate_momentum_factors(ticker_symbol: str, period: int = 252) -> Dict[str, float]:
        """
        計算動量因子 (Momentum Factors)
        - 20 日動量
        - 50 日動量
        - 相對強弱 (RSI)
        
        Args:
            ticker_symbol: 股票代碼
            period: 回看週期
        
        Returns:
            Dict: 動量因子字典
        """
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=period)).strftime("%Y-%m-%d")
            
            data = yf.download(ticker_symbol, start=start_date, end=end_date, progress=False)
            
            if data.empty:
                return {
                    'momentum_20d': 50,
                    'momentum_50d': 50,
                    'momentum_200d': 50,
                    'momentum_score': 50
                }
            
            # 計算 20/50/200 日報酬率
            momentum_20d = ((data['Close'].iloc[-1] / data['Close'].iloc[-20]) - 1) * 100
            momentum_20d = np.clip(momentum_20d + 50, 0, 100)
            
            momentum_50d = ((data['Close'].iloc[-1] / data['Close'].iloc[-50]) - 1) * 100
            momentum_50d = np.clip(momentum_50d + 50, 0, 100)
            
            momentum_200d = ((data['Close'].iloc[-1] / data['Close'].iloc[-200]) - 1) * 100
            momentum_200d = np.clip(momentum_200d + 50, 0, 100)
            
            momentum_score = (momentum_20d + momentum_50d + momentum_200d) / 3
            
            return {
                'momentum_20d': momentum_20d,
                'momentum_50d': momentum_50d,
                'momentum_200d': momentum_200d,
                'momentum_score': momentum_score
            }
        
        except Exception as e:
            logger.warning(f"Error calculating momentum factors for {ticker_symbol}: {e}")
            return {
                'momentum_20d': 50,
                'momentum_50d': 50,
                'momentum_200d': 50,
                'momentum_score': 50
            }


class DynamicAlphaScorer:
    """
    動態 Alpha 評分系統
    根據 HMM 市場狀態動態調整因子權重
    """
    
    def __init__(self):
        """初始化評分系統"""
        # 根據市場狀態的動態權重配置
        self.regime_weights = {
            0: {  # Bull Market (低波動牛市)
                'growth': 0.40,
                'momentum': 0.25,
                'quality': 0.20,
                'valuation': 0.10,
                'smart_money': 0.05
            },
            1: {  # Bear Market (熊市防守)
                'quality': 0.40,
                'valuation': 0.30,
                'growth': 0.10,
                'momentum': 0.10,
                'smart_money': 0.10
            },
            2: {  # High Volatility (高波動震盪)
                'quality': 0.35,
                'valuation': 0.25,
                'momentum': 0.15,
                'growth': 0.15,
                'smart_money': 0.10
            }
        }
        
        self.factor_calculator = FactorCalculator()
        logger.info("DynamicAlphaScorer initialized")
    
    def score_stock(
        self,
        ticker_symbol: str,
        regime: int = 0,
        smart_money_score: float = 50.0,
        include_details: bool = False
    ) -> Dict[str, float]:
        """
        評分個股
        
        Args:
            ticker_symbol: 股票代碼
            regime: 市場狀態 (0=Bull, 1=Bear, 2=HighVol)
            smart_money_score: 機構吸籌指標 (0-100)
            include_details: 是否返回詳細因子
        
        Returns:
            Dict: 評分結果
        """
        logger.info(f"Scoring {ticker_symbol} with regime {regime}")
        
        # 計算各因子
        quality = self.factor_calculator.calculate_quality_factors(ticker_symbol)
        growth = self.factor_calculator.calculate_growth_factors(ticker_symbol)
        valuation = self.factor_calculator.calculate_valuation_factors(ticker_symbol)
        momentum = self.factor_calculator.calculate_momentum_factors(ticker_symbol)
        
        # 提取主要分數
        factor_scores = {
            'quality': quality['quality_score'],
            'growth': growth['growth_score'],
            'valuation': valuation['valuation_score'],
            'momentum': momentum['momentum_score'],
            'smart_money': smart_money_score
        }
        
        # 獲取權重
        weights = self.regime_weights.get(regime, self.regime_weights[0])
        
        # 計算加權評分
        alpha_score = sum(
            factor_scores[factor] * weights[factor]
            for factor in weights.keys()
        )
        
        result = {
            'ticker': ticker_symbol,
            'regime': regime,
            'alpha_score': alpha_score,
            'weights': weights,
            'factor_scores': factor_scores
        }
        
        if include_details:
            result['details'] = {
                'quality': quality,
                'growth': growth,
                'valuation': valuation,
                'momentum': momentum
            }
        
        return result
    
    def score_portfolio(
        self,
        tickers: List[str],
        regime: int = 0,
        smart_money_scores: Optional[Dict[str, float]] = None,
        top_n: Optional[int] = None
    ) -> pd.DataFrame:
        """
        評分投資組合
        
        Args:
            tickers: 股票代碼列表
            regime: 市場狀態
            smart_money_scores: 機構吸籌字典 {ticker: score}
            top_n: 返回前 N 支股票
        
        Returns:
            pd.DataFrame: 評分結果
        """
        logger.info(f"Scoring portfolio of {len(tickers)} stocks...")
        
        results = []
        
        for ticker in tickers:
            smart_money = smart_money_scores.get(ticker, 50.0) if smart_money_scores else 50.0
            
            score = self.score_stock(
                ticker,
                regime=regime,
                smart_money_score=smart_money,
                include_details=False
            )
            
            results.append({
                'Ticker': ticker,
                'Alpha_Score': score['alpha_score'],
                'Quality': score['factor_scores']['quality'],
                'Growth': score['factor_scores']['growth'],
                'Valuation': score['factor_scores']['valuation'],
                'Momentum': score['factor_scores']['momentum'],
                'SmartMoney': score['factor_scores']['smart_money']
            })
        
        df_results = pd.DataFrame(results).sort_values('Alpha_Score', ascending=False)
        
        if top_n:
            df_results = df_results.head(top_n)
        
        logger.info(f"Portfolio scoring completed. Top stock: {df_results.iloc[0]['Ticker']} ({df_results.iloc[0]['Alpha_Score']:.2f})")
        
        return df_results
    
    def get_regime_weights(self, regime: int) -> Dict[str, float]:
        """獲取特定市場狀態的因子權重"""
        return self.regime_weights.get(regime, self.regime_weights[0])
    
    def get_all_regime_weights(self) -> Dict[int, Dict[str, float]]:
        """獲取所有市場狀態的因子權重"""
        return self.regime_weights


class AlphaExplanation:
    """Alpha 評分解釋器"""
    
    @staticmethod
    def explain_score(score_result: Dict[str, any]) -> str:
        """
        生成可讀的評分解釋
        
        Args:
            score_result: 評分結果字典
        
        Returns:
            str: 解釋文本
        """
        ticker = score_result['ticker']
        alpha_score = score_result['alpha_score']
        regime = score_result['regime']
        factors = score_result['factor_scores']
        weights = score_result['weights']
        
        regime_names = {0: "Bull Market", 1: "Bear Market", 2: "High Volatility"}
        regime_name = regime_names.get(regime, "Unknown")
        
        explanation = f"""
═══════════════════════════════════════════
Alpha Score Explanation: {ticker}
═══════════════════════════════════════════

Market Regime: {regime_name}
Alpha Score: {alpha_score:.2f}/100
{"🚀 STRONG BUY" if alpha_score > 70 else "📈 BUY" if alpha_score > 60 else "⚖️ HOLD" if alpha_score > 40 else "📉 SELL"}

Factor Breakdown:
"""
        
        # 按權重排序因子
        sorted_factors = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        
        for factor, weight in sorted_factors:
            score = factors[factor]
            contribution = score * weight
            bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
            explanation += f"  {factor:15s} [{bar}] {score:5.1f} × {weight:5.1%} = {contribution:5.2f}\n"
        
        return explanation
    
    @staticmethod
    def generate_report(
        df_scores: pd.DataFrame,
        regime: int,
        top_n: int = 10
    ) -> str:
        """
        生成投資組合評分報告
        
        Args:
            df_scores: 評分 DataFrame
            regime: 市場狀態
            top_n: 返回前 N 支
        
        Returns:
            str: 報告文本
        """
        regime_names = {0: "Bull Market", 1: "Bear Market", 2: "High Volatility"}
        regime_name = regime_names.get(regime, "Unknown")
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║           DYNAMIC ALPHA SCORING REPORT                         ║
╚════════════════════════════════════════════════════════════════╝

Market Regime: {regime_name}
Report Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Total Stocks: {len(df_scores)}

TOP {top_n} RECOMMENDATIONS:
{'─' * 64}
{df_scores.head(top_n).to_string(index=False)}

Portfolio Statistics:
  Mean Alpha Score: {df_scores['Alpha_Score'].mean():.2f}
  Median Alpha Score: {df_scores['Alpha_Score'].median():.2f}
  Std Dev: {df_scores['Alpha_Score'].std():.2f}
  Min Score: {df_scores['Alpha_Score'].min():.2f}
  Max Score: {df_scores['Alpha_Score'].max():.2f}
"""
        
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 測試評分系統
    scorer = DynamicAlphaScorer()
    
    # 評分單支股票
    test_ticker = "AAPL"
    score = scorer.score_stock(test_ticker, regime=0, include_details=True)
    
    print(f"Score for {test_ticker}: {score['alpha_score']:.2f}")
    print(AlphaExplanation.explain_score(score))
    
    # 評分投資組合
    test_portfolio = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    portfolio_scores = scorer.score_portfolio(test_portfolio, regime=0, top_n=5)
    
    print("\nPortfolio Scores:")
    print(portfolio_scores)
    
    # 生成報告
    report = AlphaExplanation.generate_report(portfolio_scores, regime=0, top_n=5)
    print(report)
