"""
INTEGRATION DEPLOYMENT GUIDE
市場結構平台 - 完整部署指南

This guide shows how to integrate daily_stock_analysis functionality
into the market_structure_platform
"""

# ============================================================================
# 📋 DEPLOYMENT OVERVIEW
# ============================================================================

DEPLOYMENT_STEPS = """
1. 環境準備
2. 配置設置
3. 本地測試
4. GitHub Actions 部署
5. 自定義擴展
"""


# ============================================================================
# 1️⃣  ENVIRONMENT SETUP
# ============================================================================

STEP_1_SETUP = """
### Step 1: Clone & Install

# 克隆項目
git clone https://github.com/yourusername/market_structure_platform.git
cd market_structure_platform

# 創建虛擬環境
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# 安裝依賴
pip install -r requirements.txt

# 驗證安裝
python -c "from notification.manager import NotificationManager; print('✓ Installed')"
"""


# ============================================================================
# 2️⃣  CONFIGURATION
# ============================================================================

STEP_2_CONFIG = """
### Step 2: Configure Environment Variables

# 複製配置模板
cp .env.example .env

# 編輯 .env 文件
vim .env  # 或使用你的編輯器

# 最少需要配置以下項:
# 1. 股票列表 (STOCK_LIST)
# 2. AI Model Key (ANSPIRE_API_KEYS 或其他)
# 3. 至少一個通知渠道 (DISCORD_WEBHOOK_URL 等)

### 配置優先級:

AI Model (選一個):
- ANSPIRE_API_KEYS (推薦 - 一Key全搞定)
- AIHUBMIX_KEY (備選)
- OPENAI_API_KEY (需要科學上網)

Notification Channels (推薦至少配置一個):
- DISCORD_WEBHOOK_URL (最簡單)
- TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
- EMAIL_SENDER + EMAIL_PASSWORD
- WECHAT_WEBHOOK_URL (企業微信)
- FEISHU_WEBHOOK_URL (飛書)

Stock List:
- STOCK_LIST=600519,000858,hk00700,AAPL,TSLA
"""


# ============================================================================
# 3️⃣  LOCAL TESTING
# ============================================================================

STEP_3_TESTING = """
### Step 3: Local Testing

# 測試分析調度器
python market_structure/analysis_scheduler.py \\
    --stocks "AAPL,600519" \\
    --mode daily \\
    --notify

# 測試通知系統
python -c "
from notification.manager import NotificationManager
manager = NotificationManager()
result = manager.broadcast(
    message='Test message from market analysis',
    title='Test Notification'
)
print(f'Results: {result}')
"

# 測試數據提供者
python -c "
from data_provider.base import DataProviderManager
manager = DataProviderManager()
data = manager.fetch_stock_data('AAPL')
print(f'✓ Got {len(data)} records for AAPL')
"

# 測試市場狀態檢測
python -c "
from market_structure.engine import MarketRegimeDetector
detector = MarketRegimeDetector()
detector.fit()
regime = detector.predict_regime()
regime_map = {0: 'Bull', 1: 'Bear', 2: 'High Vol'}
print(f'Current Regime: {regime_map[regime]}')
"
"""


# ============================================================================
# 4️⃣  GITHUB ACTIONS DEPLOYMENT
# ============================================================================

STEP_4_GITHUB_ACTIONS = """
### Step 4: Deploy with GitHub Actions

#### 4.1 Push Code to GitHub

# 如果還未上傳到 GitHub:
git add .
git commit -m "Integrate daily analysis with market regime detection"
git push origin main

# 確保 .github/workflows/daily-analysis.yml 已提交

#### 4.2 Configure GitHub Secrets

進入 Repository Settings:
  Settings → Secrets and variables → Actions → New repository secret

添加以下 Secrets:

# AI Model (至少一個)
ANSPIRE_API_KEYS = your_key
或
AIHUBMIX_KEY = your_key

# 股票列表
STOCK_LIST = 600519,000858,hk00700,AAPL,TSLA

# 通知渠道 (推薦)
DISCORD_WEBHOOK_URL = https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN = your_bot_token
TELEGRAM_CHAT_ID = your_chat_id
EMAIL_SENDER = your_email
EMAIL_PASSWORD = your_app_password

#### 4.3 Enable Workflows

進入 Actions 標籤:
  Actions → "I understand my workflows, go ahead and enable them"

#### 4.4 Test Workflow

進入 Actions 標籤:
  Daily Market Analysis → Run workflow → Run workflow

查看執行結果:
  - 應該在 1-2 分鐘內完成
  - 檢查日誌確認分析結果
  - 驗證通知已發送到配置的渠道

#### 4.5 Scheduled Execution

工作流會自動在:
  每個工作日 18:00 (北京時間)
  = 每週一到週五
  
可以在 .github/workflows/daily-analysis.yml 中修改時間:
  cron: '0 10 * * 1-5'  # UTC 時間
  # 改為其他時間: cron: '0 09 * * 1-5' (17:00 北京時間)
"""


# ============================================================================
# 5️⃣  CUSTOMIZATION
# ============================================================================

STEP_5_CUSTOMIZATION = """
### Step 5: Custom Extensions

#### 5.1 添加自定義數據提供者

在 data_provider/base.py 中:

```python
class CustomDataProvider(DataProviderBase):
    def __init__(self):
        super().__init__("CustomProvider")
    
    def fetch_stock_data(self, symbol, ...):
        # 實現自定義邏輯
        pass
```

然後在 _initialize_providers() 中註冊:
```python
self.providers["custom"] = CustomDataProvider()
```

#### 5.2 添加自定義通知渠道

在 notification/manager.py 中:

```python
class CustomNotification(NotificationBase):
    def __init__(self):
        super().__init__("Custom")
        self.enabled = True
    
    def send(self, message, title=None, **kwargs):
        # 實現發送邏輯
        pass
```

在 NotificationManager._initialize_notifiers() 中添加:
```python
self.notifiers["custom"] = CustomNotification()
```

#### 5.3 自定義分析邏輯

修改 market_structure/analysis_scheduler.py:

```python
def _calculate_score(self, indicators, regime):
    # 自定義評分算法
    score = 50
    # ... 你的邏輯
    return score
```

#### 5.4 擴展分析指標

在 _calculate_indicators() 中添加:

```python
# Bollinger Bands
data['BB_Upper'] = data['SMA20'] + 2 * data['Close'].rolling(20).std()
data['BB_Lower'] = data['SMA20'] - 2 * data['Close'].rolling(20).std()

# ATR (Average True Range)
# ... 實現 ATR 計算
```
"""


# ============================================================================
# 6️⃣  ADVANCED FEATURES
# ============================================================================

STEP_6_ADVANCED = """
### Step 6: Advanced Features

#### 6.1 Alpha Score Ranking (Alpha 排名)

在分析完成後計算 Alpha Score:

```python
# 在 analysis_scheduler.py 中添加:
def calculate_alpha_score(self, results):
    '''計算 Alpha Score 用於排名'''
    scores = []
    for symbol, result in results.items():
        if result['status'] == 'success':
            alpha = (result['score'] * 0.4 + 
                    result['indicators']['RSI'] * 0.3 +
                    result['indicators']['Volatility'] * 0.3)
            scores.append((symbol, alpha))
    
    return sorted(scores, key=lambda x: x[1], reverse=True)

# 然後在發送通知時包含排名
```

#### 6.2 Bubble Alert (泡沫警告)

識別潛在泡沫:

```python
def detect_bubble(self, symbol, indicators):
    '''檢測潛在泡沫'''
    alerts = []
    
    rsi = indicators.get('RSI')
    if rsi and rsi > 80:
        alerts.append("Extreme Overbought (RSI > 80)")
    
    volatility = indicators.get('Volatility')
    if volatility and volatility > 0.1:
        alerts.append("Extreme Volatility")
    
    return alerts
```

#### 6.3 實時推送

配置 FastAPI 實時接收市場數據:

```python
# 在 main.py 中
from fastapi import FastAPI

app = FastAPI()

@app.post("/analyze")
async def analyze_endpoint(symbols: list):
    scheduler = AnalysisScheduler()
    result = scheduler.run_analysis(symbols, notify=True)
    return result

# 運行: python main.py --webui
```

#### 6.4 多市場監控

```python
# 支持多市場:
MARKET_CONFIGS = {
    'cn': {
        'exchanges': ['SSE', 'SZSE'],
        'indices': ['000001', '399001'],
        'working_hours': [(9, 30), (15, 0)]
    },
    'us': {
        'exchanges': ['NYSE', 'NASDAQ'],
        'indices': ['^GSPC', '^IXIC'],
        'working_hours': [(9, 30), (16, 0)]
    },
    'hk': {
        'exchanges': ['HKEX'],
        'indices': ['^HSI'],
        'working_hours': [(9, 30), (16, 0)]
    }
}
```
"""


# ============================================================================
# 7️⃣  TROUBLESHOOTING
# ============================================================================

STEP_7_TROUBLESHOOTING = """
### Step 7: Troubleshooting

#### Issue 1: Import Errors

# 解決方案:
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

# 檢查 Python 版本:
python --version  # 需要 3.10+

#### Issue 2: GitHub Actions 失敗

# 檢查:
1. 查看 Actions 標籤中的日誌
2. 確認所有 Secrets 已正確配置
3. 確認 STOCK_LIST 格式正確 (逗號分隔)
4. 確認至少一個 AI Model Key 已配置

# 手動觸發測試:
Actions → Daily Market Analysis → Run workflow

#### Issue 3: 通知未發送

# 檢查:
1. 驗證通知渠道配置
2. 查看日誌確認發送嘗試
3. 檢查 Discord/Telegram 權限

# 本地測試通知:
python -c "
from notification.manager import NotificationManager
m = NotificationManager()
print('Available channels:', m.get_available_channels())
print('Status:', m.get_status())
"

#### Issue 4: 數據獲取失敗

# 檢查:
1. 網路連接
2. 數據提供者可用性
3. 股票代碼格式

# 測試數據獲取:
python -c "
from data_provider.base import DataProviderManager
mgr = DataProviderManager()
data = mgr.fetch_stock_data('AAPL', preferred_provider='yfinance')
print(f'Records: {len(data)}')
"

#### Issue 5: 市場狀態偵測失敗

# 解決方案:
python -c "
from market_structure.engine import MarketRegimeDetector
d = MarketRegimeDetector()
d.fit()  # 需要5年數據, 初次較慢
"
"""


# ============================================================================
# 8️⃣  USAGE EXAMPLES
# ============================================================================

STEP_8_EXAMPLES = """
### Step 8: Usage Examples

#### Example 1: 日常執行

# 命令行執行
python market_structure/analysis_scheduler.py \\
    --stocks "AAPL,MSFT,600519" \\
    --mode daily \\
    --notify

#### Example 2: 美股盤後複盤

python market_structure/analysis_scheduler.py \\
    --stocks "^GSPC,^IXIC,AAPL" \\
    --market us \\
    --mode review \\
    --notify

#### Example 3: 自定義時間執行

# 定時任務 (使用 APScheduler)
from apscheduler.schedulers.background import BackgroundScheduler
from market_structure.analysis_scheduler import AnalysisScheduler

scheduler = BackgroundScheduler()
analysis_scheduler = AnalysisScheduler()

def job():
    analysis_scheduler.run_analysis(['AAPL', '600519'], notify=True)

scheduler.add_job(job, 'cron', hour=18, minute=0, day_of_week='mon-fri')
scheduler.start()

#### Example 4: Docker 執行

docker build -t market-analyzer .
docker run -e STOCK_LIST="AAPL,600519" \\
           -e DISCORD_WEBHOOK_URL="..." \\
           market-analyzer

#### Example 5: 編程使用

from market_structure.analysis_scheduler import AnalysisScheduler
from notification.manager import NotificationManager

# 創建分析器
analyzer = AnalysisScheduler()

# 執行分析
result = analyzer.run_analysis(['AAPL', '600519'])

# 使用結果
for symbol, analysis in result['results'].items():
    if analysis['status'] == 'success':
        print(f"{symbol}: Score {analysis['score']}/100")
        print(f"Risks: {analysis['risks']}")
        print(f"Catalysts: {analysis['catalysts']}")
"""


# ============================================================================
# 📝 SUMMARY
# ============================================================================

print(f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║              MARKET STRUCTURE PLATFORM - DEPLOYMENT GUIDE                 ║
║                                                                            ║
║              Integrated with daily_stock_analysis Functionality            ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

{STEP_1_SETUP}

{STEP_2_CONFIG}

{STEP_3_TESTING}

{STEP_4_GITHUB_ACTIONS}

{STEP_5_CUSTOMIZATION}

{STEP_6_ADVANCED}

{STEP_7_TROUBLESHOOTING}

{STEP_8_EXAMPLES}

════════════════════════════════════════════════════════════════════════════════

Key Features Integrated:
  ✓ Multi-source data fetching (yfinance, AKShare, etc.)
  ✓ GitHub Actions automation (daily at 18:00 Beijing time)
  ✓ Multi-channel notifications (Discord, Telegram, Email, etc.)
  ✓ Market regime detection (Bull/Bear/High Vol)
  ✓ Technical indicators analysis (RSI, MACD, etc.)
  ✓ Alpha score ranking
  ✓ Risk & catalyst identification

Getting Started:
  1. cp .env.example .env
  2. Fill in your API keys and stock list
  3. python market_structure/analysis_scheduler.py --stocks "AAPL,600519"
  4. Configure GitHub Secrets for automation

Support:
  - Check logs/ directory for detailed logs
  - Review notification/manager.py for supported channels
  - Customize data_provider/base.py for additional sources

════════════════════════════════════════════════════════════════════════════════
""")
