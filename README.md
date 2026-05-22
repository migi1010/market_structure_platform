# Market Structure Platform

> 🚀 Production-Ready Stock Analysis System with AI-Powered Market Regime Detection
>
> 生產級股票分析系統 - 集市場結構檢測、技術指標分析、智能評分於一體

## 📊 System Overview

Market Structure Platform is a comprehensive stock analysis system that combines:

- **Market Regime Detection**: HMM-based classification (Bull/Bear/High Volatility)
- **Multi-Source Data**: Real-time data from yfinance, AKShare with automatic failover
- **Advanced Analytics**: 9+ technical indicators (RSI, MACD, SMA, Volatility, etc.)
- **AI Integration**: Pluggable AI models for market insights
- **Multi-Channel Notifications**: Discord, Telegram, Email, WeChat, Feishu, Slack
- **GitHub Actions Automation**: Daily scheduled analysis with manual trigger support
- **Production-Grade**: Type hints, exception handling, comprehensive logging

## ✨ Key Features

### 🎯 Core Analysis
- **Market Regime Detection**: 3-state Hidden Markov Model trained on SPY data
- **Alpha Scoring**: 0-100 composite score based on technical indicators
- **Risk Detection**: Identifies overbought/oversold conditions and volatility spikes
- **Catalyst Recognition**: Detects potential catalysts and trend changes

### 📡 Data & Integration
- **Real-Time Data**: Live stock prices and technical indicators
- **Multi-Source**: yfinance (US), AKShare (CN), with fallback providers
- **Caching**: Intelligent caching for performance optimization
- **API Resilience**: Automatic provider failover and retry logic

### 🔔 Communication
- **6 Notification Channels**: Discord, Telegram, Email, WeChat, Feishu, Slack
- **Smart Broadcasting**: Multi-channel dispatch with fallback
- **Rich Formatting**: Channel-specific formatting (embeds, markdown, HTML, cards)
- **Status Tracking**: Monitor delivery status across channels

### 🤖 Automation
- **GitHub Actions**: Scheduled daily execution (workdays 18:00 Beijing time)
- **Trading Day Validation**: Automatic skip on holidays/weekends
- **Manual Trigger**: Run analysis on-demand via GitHub Actions
- **Artifact Upload**: Store analysis results for historical tracking

### 🐳 Deployment
- **Docker Support**: Containerized deployment with compose configuration
- **Easy Setup**: Automated initialization script
- **Environment Config**: Comprehensive `.env` template
- **Health Checks**: Built-in monitoring and validation

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Initialize platform
python init.py

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and stock list
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Analysis
```bash
# Analyze specific stocks
python market_structure/analysis_scheduler.py \
    --stocks "AAPL,600519,TSLA" \
    --mode daily \
    --notify

# Or use environment variable
export STOCK_LIST="AAPL,600519"
python market_structure/analysis_scheduler.py
```

### 4. Deploy to GitHub Actions
```bash
# Push to GitHub
git add .
git commit -m "Deploy market analysis platform"
git push origin main

# Add Secrets in GitHub Settings > Secrets and variables > Actions
# Run workflow manually to test
```

## 📋 Configuration

### Minimal Setup (Required)
```env
# Stock list to analyze (comma-separated)
STOCK_LIST=AAPL,600519,TSLA

# AI API Key (pick one)
ANSPIRE_API_KEYS=your_key_here
# OR
OPENAI_API_KEY=sk-...
```

### Recommended Setup
```env
# Add notification channel
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Configure data source
DATA_PROVIDER_PRIORITY=yfinance,akshare

# System settings
LOG_LEVEL=INFO
TZ=Asia/Shanghai
```

See [`.env.example`](.env.example) for 50+ configuration options.

## 🏗️ Architecture

### Component Structure
```
market_structure_platform/
├── market_structure/
│   ├── engine.py              # Market regime detector (HMM)
│   └── analysis_scheduler.py  # Analysis orchestrator
├── data_provider/
│   └── base.py                # Multi-source data fetching
├── notification/
│   └── manager.py             # 6-channel notification system
├── alpha_engine/              # Alpha scoring engine
├── bubble_detection/          # Bubble detection module
├── deep_value/                # Value analysis module
├── theme_rotation/            # Theme-based analysis
├── smart_money/               # Smart money flow analysis
├── core/
│   └── config.py              # Core configuration
└── dashboard/
    └── app.py                 # Web dashboard
```

### Data Flow
```
User/Schedule Request
    ↓
[AnalysisScheduler]
    ├─ Fetch Stock Data (DataProviderManager)
    ├─ Calculate Indicators
    ├─ Detect Market Regime (MarketRegimeDetector)
    ├─ Generate Alpha Score
    ├─ Identify Risks/Catalysts
    └─ Notify (NotificationManager)
        ├─ Discord
        ├─ Telegram
        ├─ Email
        ├─ WeChat
        ├─ Feishu
        └─ Slack
```

## 📊 Analysis Example

### Input
```python
scheduler = AnalysisScheduler()
result = scheduler.run_analysis(['AAPL', '600519'])
```

### Output
```json
{
  "summary": "2/2 stocks analyzed successfully",
  "timestamp": "2024-01-15T18:00:00+08:00",
  "market_regime": "Bull",
  "results": {
    "AAPL": {
      "status": "success",
      "score": 78,
      "indicators": {
        "RSI": 65,
        "MACD": 0.85,
        "SMA_Trend": "bullish"
      },
      "regime": "Bull",
      "risks": ["Overbought"],
      "catalysts": ["Earnings"]
    }
  }
}
```

## 🔧 Advanced Usage

### Custom Analysis
```python
from market_structure.analysis_scheduler import AnalysisScheduler

scheduler = AnalysisScheduler()

# Run with custom settings
result = scheduler.run_analysis(
    symbols=['AAPL', '600519'],
    alert_type='detailed',
    notify=True,
    save_results=True
)
```

### Programmatic Notifications
```python
from notification.manager import NotificationManager

notifier = NotificationManager()
notifier.broadcast(
    title="Market Alert",
    message="SPY enters high volatility regime",
    alert_level="warning"
)
```

### Market Regime Detection
```python
from market_structure.engine import MarketRegimeDetector

detector = MarketRegimeDetector()
detector.fit()
regime = detector.predict_regime()  # 0:Bull, 1:Bear, 2:HighVol
```

## 🐳 Docker Deployment

### Run with Docker
```bash
docker build -t market-analyzer .

docker run -e STOCK_LIST="AAPL,600519" \
           -e DISCORD_WEBHOOK_URL="your_webhook" \
           -v $(pwd)/results:/app/results \
           market-analyzer
```

### Docker Compose (Recommended)
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f market-analyzer

# Stop services
docker-compose down
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [INTEGRATION_GUIDE.py](INTEGRATION_GUIDE.py) | Step-by-step deployment guide |
| [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) | Complete system documentation |
| [README_ZH_TW.md](README_ZH_TW.md) | Traditional Chinese guide |
| [MARKET_DETECTOR_DOCS.md](MARKET_DETECTOR_DOCS.md) | Market regime detection details |
| [USAGE_EXAMPLES.py](USAGE_EXAMPLES.py) | Real-world usage examples |
| [QUICK_REFERENCE.py](QUICK_REFERENCE.py) | API quick reference |

## 🔐 Security

### Best Practices
- Store API keys in `.env` (never commit)
- Use GitHub Secrets for Actions
- Enable webhook URL validation
- Use environment variable substitution
- Run with minimal privileges (non-root in Docker)

### Credential Management
```bash
# Generate API keys in .env
# For GitHub Actions, add Secrets in:
# Settings > Secrets and variables > Actions

# Never share:
- .env files
- API keys
- Webhook URLs
```

## 🚨 Troubleshooting

### Issue: Import errors
```bash
pip install --upgrade -r requirements.txt
```

### Issue: GitHub Actions fails
- Check all Secrets are configured
- Verify `STOCK_LIST` format
- Review workflow logs

### Issue: Notifications not sent
```bash
python -c "from notification.manager import NotificationManager; print(NotificationManager().get_status())"
```

### Issue: Data not available
```bash
python -c "from data_provider.base import DataProviderManager; DataProviderManager().fetch_stock_data('AAPL')"
```

## 📊 Performance

| Metric | Value |
|--------|-------|
| Analysis Time (per stock) | 2-5 seconds |
| Memory Usage (10 stocks) | 100-200 MB |
| API Calls (per stock) | 3-5 |
| Notification Latency | <1 second |

## 🎓 Integration with daily_stock_analysis

This platform fully integrates the three core features from ZhuLinsen/daily_stock_analysis:

1. **Data Acquisition** ✅
   - Multi-source provider (yfinance, AKShare)
   - Automatic fallback system
   - Intelligent caching

2. **GitHub Actions Automation** ✅
   - Daily scheduled execution
   - Trading day validation
   - Manual trigger support

3. **Multi-Channel Notifications** ✅
   - 6 notification channels
   - Rich formatting per channel
   - Broadcast with fallback

## 📈 Feature Roadmap

- [ ] Real-time WebSocket updates
- [ ] Machine learning alpha generation
- [ ] Portfolio-level analysis
- [ ] Custom indicator builder
- [ ] Historical analysis tracking
- [ ] Advanced backtesting engine

## 🤝 Contributing

Contributions are welcome! Areas:
- Additional notification channels
- Custom data providers
- Machine learning models
- Dashboard enhancements
- Documentation improvements

## 📜 License

MIT License - See LICENSE file for details

## 💬 Support

- 📖 Check documentation files
- 🐛 Review logs/ directory
- 💡 See INTEGRATION_GUIDE.py for setup help
- 🎓 Review USAGE_EXAMPLES.py for code samples

---

## 🎯 Next Steps

1. **Setup**: Run `python init.py`
2. **Configure**: Edit `.env` with your settings
3. **Test**: Run analysis locally
4. **Deploy**: Push to GitHub and enable Actions
5. **Monitor**: Track results and optimize

**System Status**: ✅ Production Ready  
**Version**: 2.0 (with daily_stock_analysis integration)  
**Last Updated**: 2024

---

Made with ❤️ for traders and analysts worldwide

希望這個平台能幫助你找到更好的投資機會！
