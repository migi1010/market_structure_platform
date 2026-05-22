"""
=══════════════════════════════════════════════════════════════════════════════
  MARKET STRUCTURE PLATFORM - PHASE 1 IMPLEMENTATION GUIDE
  中週期美股選股平台 - 第一階段完整實現指南
=══════════════════════════════════════════════════════════════════════════════

完整實現概述：

該系統完全實現了「中週期美股選股平台」的 Phase 1，包含：
✓ 數據與排程自動化 (GitHub Actions 每日盤後執行)
✓ HMM 市場體制引擎 (3 狀態: Bull/Bear/HighVol)
✓ 動態 Alpha 因子評分系統 (支援 HMM 動態權重)
✓ 機構吸籌檢測 (成交量結構分析)
✓ 泡沫檢測引擎 (估值/動量/出貨多維度)
✓ 多渠道通知推送 (Discord/Telegram/Email)
✓ 完全的 Production-ready 代碼

=══════════════════════════════════════════════════════════════════════════════
1. 快速開始
=══════════════════════════════════════════════════════════════════════════════

步驟 1: 環境配置
───────────────
$ cd market_structure_platform
$ python -m venv venv
$ source venv/bin/activate  # Windows: venv\\Scripts\\activate
$ pip install -r requirements.txt

步驟 2: 複製配置文件
─────────────────
$ cp .env.example .env

編輯 .env 文件，配置：
- DISCORD_WEBHOOK_URL (可選)
- TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID (可選)
- EMAIL 配置 (可選)

步驟 3: 運行完整 Pipeline
──────────────────────
$ python orchestrator.py

輸出應如下所示：
```
╔══════════════════════════════════════════════════════════════════╗
║          🚀 PRODUCTION PIPELINE STARTED                          ║
╚══════════════════════════════════════════════════════════════════╝

STEP 1: 📥 FETCH US MARKET DATA
  ✓ Fetched 14/14 symbols
  SPY: 252 records, Last: $450.25
  QQQ: 252 records, Last: $380.15
  ...

STEP 2: 🎯 TRAIN MARKET REGIME HMM MODEL
  ✓ Current Regime: Bull Market (Low Vol)
    Confidence: 89.5%

STEP 3: 🧮 CALCULATE DYNAMIC ALPHA FACTOR SCORES
  Scoring 30 stocks with regime=0...
  ✓ Alpha Scores Calculated:
  
    Ticker  Alpha_Score  Growth  Quality  Valuation  Momentum
    AAPL    75.3         68.2    82.1     65.4       72.1
    MSFT    72.8         71.5    79.3     62.1       70.2
    ...

STEP 4: 💰 DETECT SMART MONEY VOLUME STRUCTURE
  Analyzing 20 stocks for Smart Money signals...
  ✓ Smart Money Signals Detected: 5/20
  
    Ticker  Signal_Strength  Volume_Ratio  Consolidation_Index
    AAPL    78.5             1.82          0.32
    MSFT    75.2             1.65          0.28
    ...

STEP 5: 🚨 DETECT BUBBLE STOCKS
  Analyzing 14 stocks for bubble indicators...
  ✓ Bubble Alerts: 3/14
  
    Ticker  BubbleScore  MomentumBubble  DistributionBubble
    TSLA    72.5         85.2            61.3
    NFLX    68.1         78.9            52.4
    ...

STEP 6: 📈 GENERATE COMPREHENSIVE ANALYSIS REPORT
  ✓ HTML report saved: ./reports/daily_report.html
  ✓ JSON report saved: ./reports/daily_report.json

STEP 7: 📢 SEND MULTI-CHANNEL NOTIFICATIONS
  ✓ Notifications sent: {'discord': True, 'telegram': True}

╔══════════════════════════════════════════════════════════════════╗
║         ✅ PIPELINE COMPLETED SUCCESSFULLY                       ║
║         ⏱️  Duration: 125.3 seconds                              ║
╚══════════════════════════════════════════════════════════════════╝
```

=══════════════════════════════════════════════════════════════════════════════
2. 各模組詳細說明
=══════════════════════════════════════════════════════════════════════════════

2.1 數據提供層 (data_provider/us_market.py)
──────────────────────────────────────────

功能:
- 使用 yfinance 穩定抓取美股數據
- Universe: 3 大指數 (SPY/QQQ/IWM) + 11 大板塊 ETF (XLK/XLV 等)
- 自動快取 & 數據驗證
- 計算日報酬率與波動率

使用示例:
```python
from data_provider.us_market import USMarketDataProvider

provider = USMarketDataProvider()

# 獲取 SPY 數據
spy_data = provider.fetch_index_data('SPY')
print(spy_data.tail())

# 獲取完整宇宙 (所有指數 + 板塊)
universe = provider.fetch_universe_data()
for symbol, df in universe.items():
    print(f"{symbol}: {len(df)} records")

# 快速獲取
from data_provider.us_market import get_spy_data, get_sector_performance
spy = get_spy_data(days=252)
sectors = get_sector_performance()
```

2.2 市場體制引擎 (market_structure/regime_hmm.py)
───────────────────────────────────────────────

功能:
- 使用 GaussianHMM (hmmlearn) 訓練市場狀態分類器
- 輸入: SPY 日報酬率 + 20日波動率
- 輸出: 3 個 Regime (Bull/Bear/HighVol)
- 自動模型緩存與重訓練邏輯

使用示例:
```python
from market_structure.regime_hmm import MarketRegimeHMM
import os

hmm = MarketRegimeHMM()

# 訓練模型 (若無緩存)
if not os.path.exists('./models/market_regime_hmm.pkl'):
    result = hmm.train(period='5y')
    print(f"Training Score: {result['score']:.4f}")
    hmm.save_model('./models/market_regime_hmm.pkl')
else:
    hmm.load_model('./models/market_regime_hmm.pkl')

# 獲取當前市場狀態
regime, regime_name, confidence = hmm.predict_current_regime()
print(f"Current: {regime_name} (Confidence: {confidence:.1%})")

# 獲取轉移矩陣
transition_matrix = hmm.get_transition_matrix()
print(transition_matrix)
```

2.3 動態 Alpha 因子系統 (alpha_engine/dynamic_factor.py)
──────────────────────────────────────────────────────

功能:
- 多因子計算: Quality (ROIC/ROE), Growth (Rev/EPS), Valuation (PE/PS)
- Momentum 計算: 20/50/200 日報酬率
- HMM 動態權重: Bull 時加權 Growth, Bear 時加權 Quality
- 投資組合批量評分

Regime 權重配置:
```
Bull Market (Regime 0):
  Growth: 40%, Momentum: 25%, Quality: 20%, Valuation: 10%, SmartMoney: 5%

Bear Market (Regime 1):
  Quality: 40%, Valuation: 30%, Growth: 10%, Momentum: 10%, SmartMoney: 10%

High Volatility (Regime 2):
  Quality: 35%, Valuation: 25%, Growth: 15%, Momentum: 15%, SmartMoney: 10%
```

使用示例:
```python
from alpha_engine.dynamic_factor import DynamicAlphaScorer, AlphaExplanation

scorer = DynamicAlphaScorer()

# 評分單支股票
score = scorer.score_stock('AAPL', regime=0, smart_money_score=75, include_details=True)
print(AlphaExplanation.explain_score(score))

# 評分投資組合
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
portfolio_scores = scorer.score_portfolio(tickers, regime=0, top_n=5)
print(portfolio_scores)

# 獲取權重
weights = scorer.get_regime_weights(regime=0)
print(f"Bull Market weights: {weights}")
```

2.4 機構吸籌檢測 (smart_money/volume_structure.py)
──────────────────────────────────────────────

功能:
- 檢測「股價盤整 + 成交量放大」的機構吸籌信號
- 指標: 成交量比 > 1.5x, 20日波動 < 5%, 價格動量穩定
- 評分 0-100, 得分 >= 2 個條件判定為吸籌

使用示例:
```python
from smart_money.volume_structure import SmartMoneyDetector, SmartMoneyReporter

detector = SmartMoneyDetector()

# 檢測單支股票
signal = detector.detect_smart_money_signal('AAPL')
print(SmartMoneyReporter.generate_signal_report(signal))

# 檢測投資組合
portfolio = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
signals = detector.detect_portfolio_smart_money(portfolio)
print(signals[signals['SmartMoney']])  # 只顯示有信號的股票

# 獲取評分 (0-100)
scores = detector.get_smart_money_scores(portfolio)
for ticker, score in scores.items():
    print(f"{ticker}: {score:.1f}")
```

2.5 泡沫檢測引擎 (bubble_detection/engine.py)
──────────────────────────────────────────

功能:
- 多維度泡沫指標:
  * 估值泡沫: PE/PEG/PB/PS 相對排名
  * 動量泡沫: RSI 超買, 極端漲幅, 高波動率
  * 出貨泡沫: 高檔放量, 成交量分佈, 賣壓
- 加權綜合評分, 分數 > 60 判定為泡沫

使用示例:
```python
from bubble_detection.engine import BubbleDetector, BubbleReporter

detector = BubbleDetector()

# 檢測單支股票
bubble = detector.detect_bubble('TSLA')
print(BubbleReporter.generate_bubble_report(bubble))

# 檢測投資組合
high_growth = ['TSLA', 'NFLX', 'AMD', 'NVDA', 'SOFI']
bubbles = detector.detect_portfolio_bubbles(high_growth)
print(bubbles[bubbles['IsBubble']])

# 生成組合報告
report = BubbleReporter.generate_portfolio_report(bubbles)
print(report)
```

2.6 通知管理系統 (notification/manager.py)
─────────────────────────────────────────

功能:
- 支持 Discord, Telegram, Email 多渠道
- 自動失敗重試機制
- 異步推送, 不阻塞主流程
- 結構化報告推送

使用示例:
```python
from notification.manager import NotificationManager

manager = NotificationManager()

# 簡單消息
result = manager.send(
    "This is a test",
    title="Test Alert",
    channels=['discord', 'telegram']
)

# 交易警報
alert = manager.send_alert(
    alert_type="SMART_MONEY",
    ticker="AAPL",
    details="Volume expansion detected",
    severity="WARNING",
    channels=['discord']
)

# 市場報告 (需要準備 DataFrames)
import pandas as pd
report_result = manager.send_market_report(
    regime="Bull Market",
    alpha_scores=df_alpha,
    smart_money_signals=df_smart,
    bubble_alerts=df_bubble,
    channels=['discord', 'telegram']
)
```

=══════════════════════════════════════════════════════════════════════════════
3. GitHub Actions 自動化執行
=══════════════════════════════════════════════════════════════════════════════

配置位置: .github/workflows/daily-analysis.yml

工作流觸發條件:
- 定時: 每個工作日 20:00 UTC (美股盤後)
- 手動: 可通過 GitHub Actions 頁面手動觸發

工作流步驟:
1. 檢出代碼
2. 設置 Python 3.10 環境
3. 安裝依賴
4. 準備數據目錄
5. 訓練/更新 HMM 模型
6. 獲取美股數據
7. 計算 Alpha 評分
8. 檢測機構吸籌
9. 檢測泡沫股
10. 生成 HTML 報告
11. 推送多渠道通知
12. 提交報告到 Git
13. 上傳工件 (30 天保留)

配置 GitHub Secrets:
──────────────────
進入 Settings → Secrets and variables → Actions，添加:
- DISCORD_WEBHOOK_URL
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
- EMAIL_SENDER
- EMAIL_PASSWORD
- EMAIL_RECIPIENT

=══════════════════════════════════════════════════════════════════════════════
4. 完整執行示例
=══════════════════════════════════════════════════════════════════════════════

從 orchestrator.py 直接運行:
──────────────────────────
$ python orchestrator.py

將執行完整 7 步 Pipeline:
1. 📥 獲取市場數據 (SPY + 11 ETFs)
2. 🎯 訓練 HMM 模型並獲取當前 Regime
3. 🧮 計算 Alpha 因子評分 (30 支股票)
4. 💰 檢測機構吸籌信號 (20 支股票)
5. 🚨 檢測泡沫股票 (14 支高成長股)
6. 📈 生成 HTML + JSON 報告
7. 📢 推送 Discord/Telegram 通知

輸出文件:
────────
./reports/
  ├── alpha_scores.csv          # Alpha 評分詳細列表
  ├── smart_money_signals.csv   # 機構吸籌信號列表
  ├── bubble_alerts.csv         # 泡沫警報列表
  ├── daily_report.html         # 完整 HTML 報告
  └── daily_report.json         # 完整 JSON 報告

./models/
  └── market_regime_hmm.pkl     # 訓練的 HMM 模型

=══════════════════════════════════════════════════════════════════════════════
5. 自定義配置與擴展
=══════════════════════════════════════════════════════════════════════════════

修改評分股票池:
──────────────
# 在 orchestrator.py 中修改:

# Step 3 - Alpha 評分的股票列表
sp500_universe = ['AAPL', 'MSFT', ...]

# Step 4 - Smart Money 檢測的股票
smart_money_universe = ['AAPL', 'MSFT', ...]

# Step 5 - 泡沫檢測的股票
bubble_universe = ['TSLA', 'NFLX', ...]

調整因子權重:
─────────────
# 在 alpha_engine/dynamic_factor.py 中修改 regime_weights:

self.regime_weights = {
    0: {  # Bull Market - 自定義權重
        'growth': 0.45,  # 增加 Growth 權重
        'momentum': 0.20,
        'quality': 0.20,
        'valuation': 0.10,
        'smart_money': 0.05
    },
    ...
}

調整泡沫判定標準:
────────────────
# 在 orchestrator.py Step 5 中修改:

bubble = detector.detect_bubble(
    ticker,
    weights={'valuation': 0.25, 'momentum': 0.5, 'distribution': 0.25}
)

添加新的通知渠道:
────────────────
# 在 notification/manager.py 中添加新類別:

class SlackNotification(NotificationBase):
    def __init__(self, webhook_url):
        ...
    def send(self, message, title, **kwargs):
        ...

# 然後在 _init_channels() 中註冊:

slack = SlackNotification()
if slack.enabled:
    self.channels['slack'] = slack

=══════════════════════════════════════════════════════════════════════════════
6. 故障排除
=══════════════════════════════════════════════════════════════════════════════

問題 1: yfinance 下載超時
───────────────────────
原因: 網路連接或 Yahoo Finance 服務問題
解決:
- 確保網路連接正常
- 在 data_provider/us_market.py 中增加 retry 邏輯
- 使用 VPN 或代理

問題 2: HMM 模型訓練失敗
──────────────────────
原因: 數據不足或格式錯誤
解決:
- 確保至少有 252 天的 SPY 數據
- 檢查 market_structure/regime_hmm.py 的 prepare_features()
- 增加日誌輸出級別: LOG_LEVEL=DEBUG

問題 3: 通知未發送
──────────────────
原因: 配置錯誤或認證失敗
解決:
- 檢查 .env 文件中的密鑰配置
- 驗證 Discord Webhook URL 格式
- 測試 Telegram Bot 連接: 
  curl "https://api.telegram.org/botYOUR_TOKEN/getMe"
- 查看 notification/manager.py 的日誌輸出

問題 4: GitHub Actions 執行失敗
────────────────────────────────
原因: 依賴版本衝突或超時
解決:
- 檢查 requirements.txt 中的版本相容性
- 增加 timeout-minutes (目前設為 45)
- 檢查 GitHub Actions 日誌: Actions → workflow → logs

=══════════════════════════════════════════════════════════════════════════════
7. 性能優化建議
=══════════════════════════════════════════════════════════════════════════════

1. 數據緩存
   - 使用 pickle 快取已下載的數據
   - 避免重複下載同一時間段的數據

2. 並行處理
   - 使用 ThreadPoolExecutor 並行計算因子
   - 在 NotificationManager 中已實現異步推送

3. 模型快取
   - HMM 模型按 7 天週期更新，中間使用緩存版本
   - 减少模型訓練開銷

4. 代碼剖析
   - 使用 cProfile 識別性能瓶頸
   - 重點優化 yfinance 下載和因子計算

=══════════════════════════════════════════════════════════════════════════════
8. 下一步計劃 (Phase 2)
=══════════════════════════════════════════════════════════════════════════════

待實現功能:
✓ 回測框架 (Backtest Engine)
✓ 持倉管理 (Portfolio Manager)
✓ 風險控制 (Risk Management)
✓ 交易執行 (Order Executor)
✓ 實時監控儀表板 (Live Dashboard)
✓ 機器學習模型 (ML-based Predictions)

=══════════════════════════════════════════════════════════════════════════════

現在您已經擁有了一個 Production-ready 的中週期美股選股平台！
立即執行: python orchestrator.py

祝您交易順利！🚀

"""

if __name__ == "__main__":
    print(__doc__)
