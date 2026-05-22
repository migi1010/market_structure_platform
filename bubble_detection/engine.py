"""
Bubble Detection Engine - 泡沫檢測
識別「高檔放量出貨」的泡沫股票
使用多維度指標: 估值、動量、成交量、技術形態
Author: Market Structure Platform Team
"""

import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats

logger = logging.getLogger(__name__)


class BubbleIndicators:
    """泡沫指標計算器"""
    
    @staticmethod
    def calculate_valuation_bubble(ticker_symbol: str) -> Dict[str, float]:
        """
        計算估值泡沫指標
        
        - 與產業平均相比的 PE 倍數
        - PB/PS 相對排名
        - 盈利成長率與 PE 的比較
        
        Args:
            ticker_symbol: 股票代碼
        
        Returns:
            Dict: 估值泡沫指標
        """
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            pe_ratio = info.get('trailingPE', 20) or 20
            ps_ratio = info.get('priceToSalesTrailingTwelveMonths', 2) or 2
            pb_ratio = info.get('priceToBook', 3) or 3
            earnings_growth = info.get('earningsGrowth', 0.1) or 0.1
            
            # PEG Ratio (PE / Earnings Growth) - > 2 為高估
            peg_ratio = pe_ratio / (earnings_growth * 100 + 1)
            
            # 估值泡沫分數 (0-100, 越高越泡沫)
            # PE > 30 視為高估
            pe_bubble = min((pe_ratio / 30) * 100, 100)
            
            # PEG > 2 視為高估
            peg_bubble = min((peg_ratio / 2) * 100, 100)
            
            # PB/PS 複合指標
            pb_ps_bubble = min(((pb_ratio + ps_ratio) / 5) * 100, 100)
            
            valuation_bubble_score = (pe_bubble + peg_bubble + pb_ps_bubble) / 3
            
            return {
                'pe_ratio': pe_ratio,
                'peg_ratio': peg_ratio,
                'pb_ratio': pb_ratio,
                'ps_ratio': ps_ratio,
                'pe_bubble_score': pe_bubble,
                'peg_bubble_score': peg_bubble,
                'valuation_bubble_score': valuation_bubble_score
            }
        
        except Exception as e:
            logger.warning(f"Error calculating valuation bubble for {ticker_symbol}: {e}")
            return {
                'pe_ratio': 20,
                'peg_ratio': 1.0,
                'pb_ratio': 3,
                'ps_ratio': 2,
                'pe_bubble_score': 0,
                'peg_bubble_score': 0,
                'valuation_bubble_score': 0
            }
    
    @staticmethod
    def calculate_momentum_bubble(ticker_symbol: str, period: int = 252) -> Dict[str, float]:
        """
        計算動量泡沫指標
        
        - 超買指標 (RSI > 70)
        - 極端漲幅 (1 月漲幅 > 30%)
        - 高波動率
        
        Args:
            ticker_symbol: 股票代碼
            period: 回看週期
        
        Returns:
            Dict: 動量泡沫指標
        """
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=period)).strftime("%Y-%m-%d")
            
            data = yf.download(ticker_symbol, start=start_date, end=end_date, progress=False)
            
            if data.empty or len(data) < 30:
                return {
                    'rsi': 50,
                    'one_month_return': 0,
                    'six_month_return': 0,
                    'volatility': 0.3,
                    'rsi_bubble_score': 0,
                    'momentum_bubble_score': 0
                }
            
            # 計算 RSI (14-day)
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_current = rsi.iloc[-1]
            
            # RSI 泡沫分數 (> 70 為超買)
            rsi_bubble = max((rsi_current - 50) / 50 * 100, 0) if rsi_current > 50 else 0
            
            # 1 月、6 月漲幅
            one_month_return = ((data['Close'].iloc[-1] / data['Close'].iloc[-22]) - 1) * 100
            six_month_return = ((data['Close'].iloc[-1] / data['Close'].iloc[-126]) - 1) * 100
            
            # 極端漲幅泡沫分數
            extreme_return_bubble = 0
            if one_month_return > 30:
                extreme_return_bubble += 50
            if six_month_return > 100:
                extreme_return_bubble += 50
            extreme_return_bubble = min(extreme_return_bubble, 100)
            
            # 波動率泡沫分數 (高波動率 > 40%)
            returns = np.log(data['Close'] / data['Close'].shift(1)).dropna()
            volatility = returns.std() * np.sqrt(252)
            volatility_bubble = min((volatility / 0.4) * 100, 100)
            
            momentum_bubble_score = (rsi_bubble + extreme_return_bubble + volatility_bubble) / 3
            
            return {
                'rsi': rsi_current,
                'one_month_return': one_month_return,
                'six_month_return': six_month_return,
                'volatility': volatility,
                'rsi_bubble_score': rsi_bubble,
                'momentum_bubble_score': momentum_bubble_score
            }
        
        except Exception as e:
            logger.warning(f"Error calculating momentum bubble for {ticker_symbol}: {e}")
            return {
                'rsi': 50,
                'one_month_return': 0,
                'six_month_return': 0,
                'volatility': 0.3,
                'rsi_bubble_score': 0,
                'momentum_bubble_score': 0
            }
    
    @staticmethod
    def calculate_distribution_bubble(ticker_symbol: str, period: int = 20) -> Dict[str, float]:
        """
        計算出貨泡沫指標
        
        - 高檔放量 (成交量相對於平均值的比率)
        - 高檔形成 (20 日高點附近交易)
        - 成交量分佈不均 (集中在高點)
        
        Args:
            ticker_symbol: 股票代碼
            period: 回看週期
        
        Returns:
            Dict: 出貨泡沫指標
        """
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=period * 2)).strftime("%Y-%m-%d")
            
            data = yf.download(ticker_symbol, start=start_date, end=end_date, progress=False)
            
            if data.empty or len(data) < period:
                return {
                    'volume_at_high': 0,
                    'distribution_index': 0,
                    'selling_pressure': 0,
                    'distribution_bubble_score': 0
                }
            
            recent = data.iloc[-period:]
            
            # 高檔放量指標
            current_close = recent['Close'].iloc[-1]
            high_20d = recent['High'].max()
            price_from_high = ((high_20d - current_close) / current_close) * 100
            
            # 在高檔 (距離 20 日高點 < 5%)
            near_high = price_from_high < 5
            
            # 高檔成交量
            current_volume = recent['Volume'].iloc[-1]
            avg_volume = recent['Volume'].mean()
            volume_at_high = current_volume / avg_volume if avg_volume > 0 else 1
            
            volume_at_high_bubble = min((volume_at_high / 1.5) * 100, 100) if near_high else 0
            
            # 成交量分佈指標 (越不均勻越有泡沫)
            volume_skew = stats.skew(recent['Volume'])
            distribution_index = (volume_skew + 3) / 6 * 100 if volume_skew > 0 else 0
            
            # 賣壓指標 (下影線 + 上升的成交量)
            recent['upper_body'] = recent['Close'] - recent['Open']
            recent['lower_wick'] = recent['Open'] - recent['Low']
            selling_pressure = (recent['lower_wick'].mean() / recent['upper_body'].mean()) * 100 if recent['upper_body'].mean() > 0 else 0
            selling_pressure = min(selling_pressure, 100)
            
            distribution_bubble_score = (volume_at_high_bubble + distribution_index + selling_pressure) / 3
            
            return {
                'volume_at_high': volume_at_high,
                'distribution_index': distribution_index,
                'selling_pressure': selling_pressure,
                'distribution_bubble_score': distribution_bubble_score
            }
        
        except Exception as e:
            logger.warning(f"Error calculating distribution bubble for {ticker_symbol}: {e}")
            return {
                'volume_at_high': 0,
                'distribution_index': 0,
                'selling_pressure': 0,
                'distribution_bubble_score': 0
            }


class BubbleDetector:
    """
    泡沫檢測引擎
    綜合多個指標識別泡沫股票
    """
    
    def __init__(self):
        self.indicators = BubbleIndicators()
    
    def detect_bubble(
        self,
        ticker_symbol: str,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, any]:
        """
        檢測股票泡沫
        
        Args:
            ticker_symbol: 股票代碼
            weights: 各維度權重 {valuation: 0.3, momentum: 0.4, distribution: 0.3}
        
        Returns:
            Dict: 泡沫檢測結果
        """
        if weights is None:
            weights = {'valuation': 0.3, 'momentum': 0.4, 'distribution': 0.3}
        
        logger.info(f"Detecting bubble for {ticker_symbol}...")
        
        # 計算各維度泡沫指標
        valuation_bubble = self.indicators.calculate_valuation_bubble(ticker_symbol)
        momentum_bubble = self.indicators.calculate_momentum_bubble(ticker_symbol)
        distribution_bubble = self.indicators.calculate_distribution_bubble(ticker_symbol)
        
        # 計算加權泡沫分數
        total_bubble_score = (
            valuation_bubble['valuation_bubble_score'] * weights['valuation'] +
            momentum_bubble['momentum_bubble_score'] * weights['momentum'] +
            distribution_bubble['distribution_bubble_score'] * weights['distribution']
        )
        
        # 判斷是否為泡沫股
        is_bubble = total_bubble_score > 60
        
        result = {
            'ticker': ticker_symbol,
            'is_bubble': is_bubble,
            'total_bubble_score': total_bubble_score,
            'valuation_bubble': valuation_bubble,
            'momentum_bubble': momentum_bubble,
            'distribution_bubble': distribution_bubble,
            'weights': weights,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Bubble Score: {total_bubble_score:.1f}% - {'BUBBLE DETECTED' if is_bubble else 'NOT A BUBBLE'}")
        
        return result
    
    def detect_portfolio_bubbles(
        self,
        tickers: List[str],
        **kwargs
    ) -> pd.DataFrame:
        """
        檢測投資組合中的泡沫股票
        
        Args:
            tickers: 股票代碼列表
            **kwargs: 其他參數
        
        Returns:
            pd.DataFrame: 泡沫檢測結果
        """
        logger.info(f"Detecting bubbles for {len(tickers)} stocks...")
        
        results = []
        
        for ticker in tickers:
            try:
                bubble = self.detect_bubble(ticker, **kwargs)
                results.append({
                    'Ticker': ticker,
                    'IsBubble': bubble['is_bubble'],
                    'BubbleScore': bubble['total_bubble_score'],
                    'ValuationBubble': bubble['valuation_bubble']['valuation_bubble_score'],
                    'MomentumBubble': bubble['momentum_bubble']['momentum_bubble_score'],
                    'DistributionBubble': bubble['distribution_bubble']['distribution_bubble_score']
                })
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
        
        df = pd.DataFrame(results).sort_values('BubbleScore', ascending=False)
        
        logger.info(f"Bubble Detection completed. Found {df['IsBubble'].sum()} bubbles")
        
        return df


class BubbleReporter:
    """泡沫報告生成器"""
    
    @staticmethod
    def generate_bubble_report(bubble_result: Dict[str, any]) -> str:
        """
        生成單支股票的泡沫分析報告
        
        Args:
            bubble_result: 泡沫檢測結果
        
        Returns:
            str: 報告文本
        """
        ticker = bubble_result['ticker']
        is_bubble = bubble_result['is_bubble']
        score = bubble_result['total_bubble_score']
        
        v = bubble_result['valuation_bubble']
        m = bubble_result['momentum_bubble']
        d = bubble_result['distribution_bubble']
        
        status = "🔴 BUBBLE DETECTED" if is_bubble else "🟢 NOT A BUBBLE"
        warning = "⚠️  AVOID" if is_bubble else "✅ SAFE"
        
        report = f"""
{'═' * 70}
{status} - {ticker}
{'═' * 70}

Overall Bubble Score: {score:.1f}/100 {warning}

VALUATION ANALYSIS (Weight: {bubble_result['weights']['valuation']:.0%})
  • PE Ratio: {v['pe_ratio']:.1f}
  • PEG Ratio: {v['peg_ratio']:.2f}
  • Valuation Bubble Score: {v['valuation_bubble_score']:.1f}

MOMENTUM ANALYSIS (Weight: {bubble_result['weights']['momentum']:.0%})
  • RSI (14): {m['rsi']:.1f}
  • 1-Month Return: {m['one_month_return']:.1f}%
  • 6-Month Return: {m['six_month_return']:.1f}%
  • Volatility: {m['volatility']:.1%}
  • Momentum Bubble Score: {m['momentum_bubble_score']:.1f}

DISTRIBUTION ANALYSIS (Weight: {bubble_result['weights']['distribution']:.0%})
  • Volume at High: {d['volume_at_high']:.2f}x
  • Distribution Index: {d['distribution_index']:.1f}
  • Selling Pressure: {d['selling_pressure']:.1f}
  • Distribution Bubble Score: {d['distribution_bubble_score']:.1f}

Recommendation: {"SELL/SHORT" if is_bubble else "MONITOR"}
Timestamp: {bubble_result['timestamp']}
"""
        
        return report
    
    @staticmethod
    def generate_portfolio_report(df_bubbles: pd.DataFrame) -> str:
        """
        生成投資組合泡沫分析報告
        
        Args:
            df_bubbles: 泡沫檢測 DataFrame
        
        Returns:
            str: 報告文本
        """
        bubble_count = df_bubbles['IsBubble'].sum()
        total_count = len(df_bubbles)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║              BUBBLE DETECTION ANALYSIS REPORT                  ║
╚════════════════════════════════════════════════════════════════╝

Report Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Total Stocks Analyzed: {total_count}
Bubbles Detected: {bubble_count} ({bubble_count/total_count*100:.1f}%)

⚠️  HIGH RISK BUBBLES (Score > 70):
{'─' * 64}
"""
        
        high_risk = df_bubbles[df_bubbles['BubbleScore'] > 70].head(10)
        if not high_risk.empty:
            report += high_risk[['Ticker', 'BubbleScore', 'MomentumBubble', 'DistributionBubble']].to_string(index=False)
        else:
            report += "No high-risk bubbles detected."
        
        report += f"\n\nMEDIUM RISK BUBBLES (Score 50-70):\n{'─' * 64}\n"
        
        medium_risk = df_bubbles[(df_bubbles['BubbleScore'] > 50) & (df_bubbles['BubbleScore'] <= 70)].head(10)
        if not medium_risk.empty:
            report += medium_risk[['Ticker', 'BubbleScore', 'MomentumBubble']].to_string(index=False)
        else:
            report += "No medium-risk bubbles detected."
        
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 測試泡沫檢測
    detector = BubbleDetector()
    
    # 檢測單支股票
    test_ticker = "TSLA"
    bubble = detector.detect_bubble(test_ticker)
    
    print(BubbleReporter.generate_bubble_report(bubble))
    
    # 檢測投資組合
    test_portfolio = ["TSLA", "NFLX", "AMD", "AAPL", "MSFT", "GOOGL"]
    portfolio_bubbles = detector.detect_portfolio_bubbles(test_portfolio)
    
    print("\nPortfolio Analysis:")
    print(portfolio_bubbles)
    
    # 生成報告
    report = BubbleReporter.generate_portfolio_report(portfolio_bubbles)
    print(report)
