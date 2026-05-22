"""
Smart Money Volume Structure Analysis - 機構吸籌檢測
當日成交量/20日均量 分析，篩選出「股價盤整、成交量放大」的機構吸籌股票
Author: Market Structure Platform Team
"""

import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class VolumeStructureAnalyzer:
    """成交量結構分析器"""
    
    @staticmethod
    def calculate_volume_profile(
        ticker_symbol: str,
        period: int = 20
    ) -> Dict[str, float]:
        """
        計算成交量指標
        
        Args:
            ticker_symbol: 股票代碼
            period: 回看週期 (預設 20 日)
        
        Returns:
            Dict: 成交量指標
        """
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=period * 2)).strftime("%Y-%m-%d")
            
            data = yf.download(ticker_symbol, start=start_date, end=end_date, progress=False)
            
            if data.empty or len(data) < period:
                return {
                    'current_volume': 0,
                    'avg_volume_20d': 0,
                    'volume_ratio': 0,
                    'volume_trend': 0
                }
            
            vol_col = 'Volume' if 'Volume' in data.columns else 'volume'
            if vol_col not in data.columns:
                vol_col = [c for c in data.columns if c.lower() == 'volume'][0]

            # 當日成交量
            current_volume = data[vol_col].iloc[-1]
            
            # 20 日平均成交量
            avg_volume_20d = data[vol_col].iloc[-period:].mean()
            
            # 成交量比率 (當日 / 20 日均)
            volume_ratio = current_volume / avg_volume_20d if avg_volume_20d > 0 else 1
            
            # 成交量趨勢 (5 日平均 / 20 日平均)
            avg_volume_5d = data[vol_col].iloc[-5:].mean()
            volume_trend = avg_volume_5d / avg_volume_20d if avg_volume_20d > 0 else 1
            
            return {
                'current_volume': current_volume,
                'avg_volume_20d': avg_volume_20d,
                'volume_ratio': volume_ratio,
                'volume_trend': volume_trend
            }
        
        except Exception as e:
            logger.warning(f"Error calculating volume profile for {ticker_symbol}: {e}")
            return {
                'current_volume': 0,
                'avg_volume_20d': 0,
                'volume_ratio': 0,
                'volume_trend': 0
            }
    
    @staticmethod
    def calculate_price_action(ticker_symbol: str, period: int = 20) -> Dict[str, float]:
        """
        計算價格動作指標
        
        Args:
            ticker_symbol: 股票代碼
            period: 回看週期
        
        Returns:
            Dict: 價格動作指標
        """
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=period * 2)).strftime("%Y-%m-%d")
            
            data = yf.download(ticker_symbol, start=start_date, end=end_date, progress=False)
            
            if data.empty or len(data) < period:
                return {
                    'price_range': 0,
                    'consolidation_index': 0,
                    'price_momentum': 0,
                    'support_level': 0,
                    'resistance_level': 0
                }
            
            # 計算 20 日價格範圍 (盤整指標)
            high_20d = data['High'].iloc[-period:].max()
            low_20d = data['Low'].iloc[-period:].min()
            price_range = (high_20d - low_20d) / low_20d if low_20d > 0 else 0
            
            # 盤整指標 (0 = 盤整, 1 = 趨勢)
            consolidation_index = 1 - min(price_range, 1)
            
            # 價格動量 (近 5 日 / 20 日)
            price_5d = (data['Close'].iloc[-1] - data['Close'].iloc[-5]) / data['Close'].iloc[-5]
            price_20d = (data['Close'].iloc[-1] - data['Close'].iloc[-20]) / data['Close'].iloc[-20]
            price_momentum = price_5d / (price_20d + 1e-8) if price_20d != 0 else 1
            
            # 支撐位與阻力位
            support_level = low_20d
            resistance_level = high_20d
            
            return {
                'price_range': price_range,
                'consolidation_index': consolidation_index,
                'price_momentum': price_momentum,
                'support_level': support_level,
                'resistance_level': resistance_level
            }
        
        except Exception as e:
            logger.warning(f"Error calculating price action for {ticker_symbol}: {e}")
            return {
                'price_range': 0,
                'consolidation_index': 0,
                'price_momentum': 0,
                'support_level': 0,
                'resistance_level': 0
            }


class SmartMoneyDetector:
    """
    機構吸籌檢測器
    特徵: 股價盤整 + 成交量放大 = 機構吸籌信號
    """
    
    def __init__(self):
        self.volume_analyzer = VolumeStructureAnalyzer()
    
    def detect_smart_money_signal(
        self,
        ticker_symbol: str,
        volume_ratio_threshold: float = 1.5,
        consolidation_threshold: float = 0.05,
        price_momentum_threshold: float = 0.5
    ) -> Dict[str, any]:
        """
        檢測機構吸籌信號
        
        條件:
        1. 成交量放大 (成交量比 > 1.5x)
        2. 股價盤整 (20 日波動 < 5%)
        3. 價格動量穩定 (5日動量 / 20日動量 在 0.5-1.5 之間)
        
        Args:
            ticker_symbol: 股票代碼
            volume_ratio_threshold: 成交量比閾值
            consolidation_threshold: 盤整波動閾值
            price_momentum_threshold: 價格動量閾值
        
        Returns:
            Dict: 檢測結果
        """
        logger.info(f"Detecting smart money signal for {ticker_symbol}...")
        
        # 獲取成交量數據
        volume_data = self.volume_analyzer.calculate_volume_profile(ticker_symbol)
        
        # 獲取價格動作
        price_data = self.volume_analyzer.calculate_price_action(ticker_symbol)
        
        # 計算信號強度
        volume_signal = 1 if volume_data['volume_ratio'] > volume_ratio_threshold else 0
        consolidation_signal = 1 if price_data['price_range'] < consolidation_threshold else 0
        momentum_signal = 1 if 0.5 < price_data['price_momentum'] < 1.5 else 0
        
        # 組合信號 (0-3)
        total_signal = volume_signal + consolidation_signal + momentum_signal
        
        # 信號強度 (0-100)
        signal_strength = (total_signal / 3) * 100
        
        # 判斷是否為機構吸籌
        is_smart_money = total_signal >= 2
        
        result = {
            'ticker': ticker_symbol,
            'is_smart_money': is_smart_money,
            'signal_strength': signal_strength,
            'signals': {
                'volume_expansion': volume_signal,
                'price_consolidation': consolidation_signal,
                'momentum_stable': momentum_signal
            },
            'volume_data': volume_data,
            'price_data': price_data,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Smart Money Signal: {signal_strength:.1f}% - {'DETECTED' if is_smart_money else 'NOT DETECTED'}")
        
        return result
    
    def detect_portfolio_smart_money(
        self,
        tickers: List[str],
        **kwargs
    ) -> pd.DataFrame:
        """
        檢測投資組合中的機構吸籌信號
        
        Args:
            tickers: 股票代碼列表
            **kwargs: 其他參數
        
        Returns:
            pd.DataFrame: 檢測結果 DataFrame
        """
        logger.info(f"Detecting smart money signals for {len(tickers)} stocks...")
        
        results = []
        
        for ticker in tickers:
            try:
                signal = self.detect_smart_money_signal(ticker, **kwargs)
                results.append({
                    'Ticker': ticker,
                    'SmartMoney': signal['is_smart_money'],
                    'Signal_Strength': signal['signal_strength'],
                    'Volume_Ratio': f"{signal['volume_data']['volume_ratio']:.2f}x",
                    'Consolidation_Index': signal['price_data']['consolidation_index'],
                    'Price_Momentum': signal['price_data']['price_momentum']
                })
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
        
        df = pd.DataFrame(results).sort_values('Signal_Strength', ascending=False)
        
        logger.info(f"Smart Money Detection completed. Found {df['SmartMoney'].sum()} signals")
        
        return df
    
    def get_smart_money_scores(
        self,
        tickers: List[str]
    ) -> Dict[str, float]:
        """
        獲取所有股票的機構吸籌評分 (0-100)
        
        Args:
            tickers: 股票代碼列表
        
        Returns:
            Dict: {ticker: score}
        """
        scores = {}
        
        for ticker in tickers:
            try:
                signal = self.detect_smart_money_signal(ticker)
                scores[ticker] = signal['signal_strength']
            except Exception as e:
                logger.warning(f"Error scoring {ticker}: {e}")
                scores[ticker] = 50  # 預設中位數
        
        return scores


class SmartMoneyReporter:
    """機構吸籌報告生成器"""
    
    @staticmethod
    def generate_signal_report(signal_result: Dict[str, any]) -> str:
        """
        生成單支股票的機構吸籌信號報告
        
        Args:
            signal_result: 信號檢測結果
        
        Returns:
            str: 報告文本
        """
        ticker = signal_result['ticker']
        is_smart_money = signal_result['is_smart_money']
        strength = signal_result['signal_strength']
        signals = signal_result['signals']
        volume = signal_result['volume_data']
        price = signal_result['price_data']
        
        status = "✅ SMART MONEY DETECTED" if is_smart_money else "❌ NOT DETECTED"
        color = "🟢" if is_smart_money else "🔴"
        
        report = f"""
{'═' * 70}
{color} Smart Money Analysis: {ticker}
{'═' * 70}

Status: {status}
Signal Strength: {strength:.1f}%

Signal Components:
  • Volume Expansion: {'✓' if signals['volume_expansion'] else '✗'} (Ratio: {volume['volume_ratio']:.2f}x)
  • Price Consolidation: {'✓' if signals['price_consolidation'] else '✗'} (Range: {price['price_range']:.2%})
  • Momentum Stable: {'✓' if signals['momentum_stable'] else '✗'} (Ratio: {price['price_momentum']:.2f})

Volume Profile:
  • Current Volume: {volume['current_volume']:,.0f}
  • 20-Day Avg: {volume['avg_volume_20d']:,.0f}
  • Volume Trend: {volume['volume_trend']:.2f}x

Price Action:
  • Support: ${price['support_level']:.2f}
  • Resistance: ${price['resistance_level']:.2f}
  • Consolidation Index: {price['consolidation_index']:.2%}

Timestamp: {signal_result['timestamp']}
"""
        
        return report
    
    @staticmethod
    def generate_portfolio_report(
        df_signals: pd.DataFrame
    ) -> str:
        """
        生成投資組合機構吸籌報告
        
        Args:
            df_signals: 信號 DataFrame
        
        Returns:
            str: 報告文本
        """
        smart_money_count = df_signals['SmartMoney'].sum()
        total_count = len(df_signals)
        
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║        SMART MONEY VOLUME STRUCTURE ANALYSIS REPORT            ║
╚════════════════════════════════════════════════════════════════╝

Report Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Total Stocks Analyzed: {total_count}
Smart Money Signals Detected: {smart_money_count} ({smart_money_count/total_count*100:.1f}%)

TOP SMART MONEY SIGNALS:
{'─' * 64}
"""
        
        smart_money_df = df_signals[df_signals['SmartMoney']].head(10)
        if not smart_money_df.empty:
            report += smart_money_df[['Ticker', 'Signal_Strength', 'Volume_Ratio', 'Consolidation_Index']].to_string(index=False)
        else:
            report += "No smart money signals detected."
        
        report += f"\n\nHIGHEST SIGNAL STRENGTH (Top 10):\n{'─' * 64}\n"
        report += df_signals.head(10)[['Ticker', 'Signal_Strength', 'Volume_Ratio']].to_string(index=False)
        
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 測試機構吸籌檢測
    detector = SmartMoneyDetector()
    
    # 檢測單支股票
    test_ticker = "AAPL"
    signal = detector.detect_smart_money_signal(test_ticker)
    
    print(SmartMoneyReporter.generate_signal_report(signal))
    
    # 檢測投資組合
    test_portfolio = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    portfolio_signals = detector.detect_portfolio_smart_money(test_portfolio)
    
    print("\nPortfolio Analysis:")
    print(portfolio_signals)
    
    # 生成報告
    report = SmartMoneyReporter.generate_portfolio_report(portfolio_signals)
    print(report)
