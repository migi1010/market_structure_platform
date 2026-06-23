# Phase 9.3D Stock Research Final Design

Status: Authoritative specification override  
Reference: `d:/Arthur/Downloads/eaaf0296-1409-48a7-903b-bd6333873d8b.png`

## Product Goal

Stock Research is an institutional equity-research terminal. It must help users determine:

1. Whether the company is fundamentally strong.
2. Whether valuation or price action indicates bubble risk.
3. Which themes drive the stock.
4. Which supply-chain dependencies matter.
5. Which catalysts matter next.
6. Whether current risk/reward is attractive.

The workspace uses a Chinese-first, English-secondary interface and follows the dense geometry, panel rhythm, terminal styling, and chart dominance of the supplied reference screenshot.

## Final Workspace Structure

### Company Header

Display ticker, company name, price, change, market cap, sector, themes, confidence, and last update.

### TradingView Chart

The chart is the largest component on the page and includes price, volume, events, and moving averages.

### Key Metrics

Display Alpha, Risk Score, Momentum, Institutional RS, Smart Money, Valuation, Earnings, Sentiment, and Overall Score.

### 營收與獲利分析 Revenue & Profit Analysis

This replaces all generic Investment Thesis, Bull Case, and Bear Case content.

- 營收動能 Revenue Momentum: YoY growth, QoQ growth, trend, acceleration, and guidance trend.
- 獲利品質 Profit Quality: gross margin, operating margin, net margin, ROE, ROIC, free cash flow, and quality grade.
- 財報趨勢 Earnings Trend: EPS growth, EPS revision, earnings surprise, and analyst revision.
- 市場預期 Market Expectations: forward revenue, forward EPS, consensus trend, estimate revisions, and expectation-versus-reality comparison.

### 泡沫風險 Bubble Risk

This replaces generic Risk Summary. It must reuse the existing Bubble Engine and frontend fallback rather than introducing a new model.

Display Bubble Score, Valuation Heat, Price vs Fundamentals, Momentum Overextension, Crowding Risk, Downside Risk, and Risk Level.

Risk levels:

- 極低
- 低
- 中
- 高
- 極高

Visual treatment uses restrained heat bars, the existing bubble gauge, and a compact institutional risk radar.

### 主題 / 供應鏈曝險 Theme / Supply Exposure

Visual relationship graph:

Stock → Themes → Supply Chain → Beneficiaries

### Supporting Intelligence

- 相關個股 Related Stocks
- 催化事件 Catalyst Timeline
- 估值區間 Valuation Range

## ContextDock

The right ContextDock remains supplementary and follows the global interaction contract.

Actions:

- 泡沫風險 Bubble Risk
- 主題重疊 Theme Overlap
- 供應鏈分析 Supply Chain Analysis
- 財報分析 Earnings Review
- 事件追蹤 Event Tracker
- 技術分析 Technical Analysis
- 加入觀察名單 Add to Watchlist
- 價格警報 Price Alert
- 匯出報告 Export Report

## Data And Architecture Constraints

- Frontend-only.
- Preserve backend, API, cache, quote pipeline, database, deployment configuration, routing contracts, selection architecture, and ContextDock architecture.
- Use actual existing payload fields and Bubble Engine output when available.
- Use existing frontend fallbacks when data is unavailable.
- Static fallback values must be visibly identified as unavailable or calibrating and must not masquerade as live intelligence.

## Explicitly Removed

- Investment Thesis
- Bull Case
- Bear Case
- Generic Risk Summary

## Visual Reference Interpretation

The screenshot is authoritative for:

- chart-first geometry
- panel proportions
- compact metric density
- horizontal analytical bands
- right-side ContextDock rhythm
- true-black and charcoal terminal styling

The screenshot's generic Investment Thesis and Risk Summary modules are replaced by Revenue & Profit Analysis and Bubble Risk respectively.
