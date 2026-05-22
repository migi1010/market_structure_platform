"""
Analysis Scheduler - Integrated Daily Analysis Workflow
整合數據獲取、市場分析、風險警報、通知發送的完整流程
"""

import logging
import os
import sys
import argparse
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 導入自定義模組
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_provider.base import DataProviderManager
from notification.manager import NotificationManager
from market_structure.engine import MarketRegimeDetector


class AnalysisScheduler:
    """
    分析調度器
    協調數據獲取、模型分析、通知發送
    """
    
    def __init__(self):
        self.logger = logging.getLogger("AnalysisScheduler")
        self.data_manager = DataProviderManager()
        self.notification_manager = NotificationManager()
        self.regime_detector = None
        self.analysis_results = {}
        
        # 確保日誌目錄存在
        Path("logs").mkdir(exist_ok=True)
        
        self.logger.info("=" * 80)
        self.logger.info("Analysis Scheduler Initialized")
        self.logger.info("=" * 80)
    
    def initialize_regime_detector(self) -> bool:
        """初始化市場狀態檢測器"""
        try:
            self.logger.info("Initializing Market Regime Detector...")
            self.regime_detector = MarketRegimeDetector()
            self.regime_detector.fit()
            self.logger.info("✓ Regime detector ready")
            return True
        except Exception as e:
            self.logger.error(f"✗ Failed to initialize regime detector: {e}")
            return False
    
    def analyze_stock(self, symbol: str) -> Dict:
        """
        分析單隻股票
        
        Args:
            symbol: 股票代碼
        
        Returns:
            Dict: 分析結果
        """
        try:
            self.logger.info(f"\n📊 Analyzing {symbol}...")
            
            # 1. 獲取股票數據
            stock_data = self.data_manager.fetch_stock_data(
                symbol,
                start_date=(datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
            )
            
            if stock_data.empty:
                self.logger.warning(f"⚠ No data available for {symbol}")
                return {
                    "symbol": symbol,
                    "status": "error",
                    "message": "Data fetching failed"
                }
            
            # 2. 計算技術指標
            indicators = self._calculate_indicators(stock_data)
            
            # 3. 評估市場狀態
            regime = self._assess_market_regime(stock_data)
            
            # 4. 生成評分
            score = self._calculate_score(indicators, regime)
            
            # 5. 識別風險與催化因素
            risks, catalysts = self._identify_risks_catalysts(symbol, indicators)
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "indicators": indicators,
                "regime": regime,
                "score": score,
                "risks": risks,
                "catalysts": catalysts,
                "last_price": float(stock_data['Close'].iloc[-1]),
                "daily_change": float(stock_data['Close'].pct_change().iloc[-1] * 100)
            }
            
            self.logger.info(f"✓ Analysis completed for {symbol} (Score: {score})")
            return result
            
        except Exception as e:
            self.logger.error(f"✗ Error analyzing {symbol}: {e}")
            return {
                "symbol": symbol,
                "status": "error",
                "message": str(e)
            }
    
    def _calculate_indicators(self, data: pd.DataFrame) -> Dict:
        """計算技術指標"""
        try:
            # 移動平均線
            data['SMA20'] = data['Close'].rolling(window=20).mean()
            data['SMA50'] = data['Close'].rolling(window=50).mean()
            data['SMA200'] = data['Close'].rolling(window=200).mean()
            
            # RSI (Relative Strength Index)
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            ema12 = data['Close'].ewm(span=12).mean()
            ema26 = data['Close'].ewm(span=26).mean()
            data['MACD'] = ema12 - ema26
            data['Signal'] = data['MACD'].ewm(span=9).mean()
            data['Histogram'] = data['MACD'] - data['Signal']
            
            # 波動率
            data['Volatility'] = data['Close'].pct_change().rolling(window=20).std()
            
            latest = data.iloc[-1]
            return {
                "SMA20": float(latest.get('SMA20', 0)) if pd.notna(latest.get('SMA20')) else None,
                "SMA50": float(latest.get('SMA50', 0)) if pd.notna(latest.get('SMA50')) else None,
                "SMA200": float(latest.get('SMA200', 0)) if pd.notna(latest.get('SMA200')) else None,
                "RSI": float(latest.get('RSI', 0)) if pd.notna(latest.get('RSI')) else None,
                "MACD": float(latest.get('MACD', 0)) if pd.notna(latest.get('MACD')) else None,
                "Signal": float(latest.get('Signal', 0)) if pd.notna(latest.get('Signal')) else None,
                "Volatility": float(latest.get('Volatility', 0)) if pd.notna(latest.get('Volatility')) else None
            }
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            return {}
    
    def _assess_market_regime(self, data: pd.DataFrame) -> str:
        """評估市場狀態"""
        try:
            if self.regime_detector is None:
                return "unknown"
            
            regime = self.regime_detector.predict_regime(data)
            regime_map = {
                0: "Bull Market (低波動牛市)",
                1: "Bear Market (熊市防守)",
                2: "High Volatility (高波動震盪)"
            }
            return regime_map.get(regime, "unknown")
        except Exception as e:
            self.logger.warning(f"Regime detection failed: {e}")
            return "unknown"
    
    def _calculate_score(self, indicators: Dict, regime: str) -> int:
        """
        計算股票評分 (0-100)
        
        基於技術指標和市場狀態
        """
        score = 50  # 基礎分
        
        # RSI 評分
        rsi = indicators.get('RSI')
        if rsi is not None:
            if 30 < rsi < 70:
                score += 10  # 正常區間
            elif rsi > 70:
                score -= 5   # 超買
            elif rsi < 30:
                score += 5   # 超賣（可能反彈）
        
        # MACD 評分
        macd = indicators.get('MACD')
        signal = indicators.get('Signal')
        if macd is not None and signal is not None:
            if macd > signal:
                score += 8   # 上升
            else:
                score -= 8   # 下降
        
        # 市場狀態
        if "Bull" in regime:
            score += 10
        elif "Bear" in regime:
            score -= 10
        
        # 確保分數在 0-100 之間
        return max(0, min(100, score))
    
    def _identify_risks_catalysts(self, symbol: str, indicators: Dict) -> tuple:
        """識別風險和催化因素"""
        risks = []
        catalysts = []
        
        # 簡化的風險識別
        rsi = indicators.get('RSI')
        if rsi is not None:
            if rsi > 70:
                risks.append("RSI > 70: 超買信號")
            elif rsi < 30:
                catalysts.append("RSI < 30: 潛在反彈機會")
        
        volatility = indicators.get('Volatility')
        if volatility is not None:
            if volatility > 0.05:
                risks.append("High Volatility: 波動率較高")
        
        return risks, catalysts
    
    def run_analysis(
        self,
        symbols: List[str],
        mode: str = "daily",
        notify: bool = True
    ) -> Dict:
        """
        執行完整分析流程
        
        Args:
            symbols: 股票代碼列表
            mode: 分析模式 ("daily", "review")
            notify: 是否發送通知
        
        Returns:
            Dict: 分析結果摘要
        """
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"Starting Analysis | Mode: {mode} | Stocks: {len(symbols)}")
        self.logger.info(f"{'='*80}")
        
        # 初始化檢測器
        if self.regime_detector is None:
            self.initialize_regime_detector()
        
        # 分析每隻股票
        results = {}
        success_count = 0
        
        for symbol in symbols:
            result = self.analyze_stock(symbol)
            results[symbol] = result
            if result.get("status") == "success":
                success_count += 1
        
        # 生成分析摘要
        summary = self._generate_summary(results, mode)
        
        # 發送通知
        if notify and self.notification_manager.notifiers:
            self._send_notifications(summary, results)
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"Analysis Complete | Success: {success_count}/{len(symbols)}")
        self.logger.info(f"{'='*80}\n")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "stocks_analyzed": len(symbols),
            "success_count": success_count,
            "summary": summary,
            "results": results
        }
    
    def _generate_summary(self, results: Dict, mode: str) -> str:
        """生成分析摘要"""
        
        successful = [r for r in results.values() if r.get("status") == "success"]
        
        # 按評分排序
        sorted_results = sorted(
            successful,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        summary = f"""
📊 Market Analysis Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Stocks Analyzed: {len(results)}
Successful: {len(successful)}

🏆 Top 3 Opportunities:
"""
        
        for i, result in enumerate(sorted_results[:3], 1):
            summary += f"""
{i}. {result['symbol']}
   Score: {result['score']}/100
   Price: {result['last_price']:.2f}
   Change: {result['daily_change']:.2f}%
   Regime: {result['regime']}
"""
        
        return summary
    
    def _send_notifications(self, summary: str, results: Dict):
        """發送通知"""
        
        try:
            channels = self.notification_manager.get_available_channels()
            self.logger.info(f"Sending notifications to {len(channels)} channels...")
            
            notification_results = self.notification_manager.send(
                message=summary,
                title="📊 Daily Market Analysis",
                channels=channels
            )
            
            for channel, success in notification_results.items():
                status = "✓" if success else "✗"
                self.logger.info(f"{status} {channel}")
            
        except Exception as e:
            self.logger.error(f"Error sending notifications: {e}")


def main():
    """主程式入口"""
    
    # 解析命令行參數
    parser = argparse.ArgumentParser(description="Daily Market Analysis Scheduler")
    parser.add_argument(
        "--stocks",
        type=str,
        default=os.getenv("STOCK_LIST", ""),
        help="Stock symbols separated by comma (e.g., AAPL,MSFT,600519)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="daily",
        choices=["daily", "review"],
        help="Analysis mode"
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        default=True,
        help="Send notifications"
    )
    parser.add_argument(
        "--market",
        type=str,
        default="cn",
        choices=["cn", "us", "hk"],
        help="Market focus"
    )
    
    args = parser.parse_args()
    
    # 解析股票列表
    if not args.stocks:
        logger.error("❌ No stocks specified. Set STOCK_LIST environment variable.")
        sys.exit(1)
    
    symbols = [s.strip() for s in args.stocks.split(",") if s.strip()]
    
    if not symbols:
        logger.error("❌ Invalid stock list format")
        sys.exit(1)
    
    # 執行分析
    scheduler = AnalysisScheduler()
    result = scheduler.run_analysis(symbols, mode=args.mode, notify=args.notify)
    
    # 輸出結果
    logger.info("\n" + "="*80)
    logger.info("Analysis Results Summary:")
    logger.info("="*80)
    logger.info(result["summary"])
    
    sys.exit(0 if result["success_count"] > 0 else 1)


if __name__ == "__main__":
    main()
