"""
QUICK REFERENCE GUIDE
Market Regime Detector - 快速參考
"""

# ============================================================================
# 🚀 5分鐘快速開始
# ============================================================================

"""
# Step 1: 初始化
from market_structure.engine import MarketRegimeDetector
detector = MarketRegimeDetector()

# Step 2: 訓練（自動取得5年美股數據）
detector.fit()

# Step 3: 預測當前市場狀態
regime = detector.predict_regime()

# Step 4: 解釋結果
regime_map = {
    0: "Bull Market (低波動牛市)",
    1: "Bear Market (熊市防守)", 
    2: "High Volatility (高波動震盪)"
}
print(f"Current Regime: {regime_map[regime]}")
"""


# ============================================================================
# 📋 核心方法列表
# ============================================================================

CORE_METHODS = {
    "fetch_spy_data(period='5y')": """
        下載美股 SPY 數據
        Return: pd.DataFrame (OHLCV 數據)
        若失敗自動降級至緩存/合成數據
    """,
    
    "fit(spy_data=None)": """
        訓練 HMM 模型
        • 獲取特徵（對數報酬率、年化波動率）
        • 標準化特徵
        • 訓練 3 狀態 GaussianHMM
        • 根據波動率排序狀態映射
    """,
    
    "predict_regime(spy_data=None)": """
        預測當前市場狀態
        Return: int (0, 1, 或 2)
        • 0: Bull Market
        • 1: Bear Market
        • 2: High Volatility
    """
}


# ============================================================================
# 🔍 特徵說明
# ============================================================================

FEATURES = {
    "Log_Return": """
        對數報酬率 = log(Close[t] / Close[t-1])
        數值範圍: -0.05 到 +0.05
        優點: 可加性、統計性質佳
    """,
    
    "Volatility": """
        20日滾動年化波動率 = std(log_returns) × √252
        數值範圍: 0.10 到 0.50
        解釋: 預期年度波動率
    """
}


# ============================================================================
# 🎯 狀態映射（State Mapping）
# ============================================================================

STATE_MAPPING = {
    0: {
        "name": "Bull Market",
        "chinese": "低波動牛市",
        "characteristics": [
            "最低的波動率",
            "溫和的正報酬",
            "市場有序上升"
        ]
    },
    1: {
        "name": "Bear Market", 
        "chinese": "熊市防守",
        "characteristics": [
            "中等波動率",
            "負報酬傾向",
            "市場防守姿態"
        ]
    },
    2: {
        "name": "High Volatility",
        "chinese": "高波動震盪",
        "characteristics": [
            "最高的波動率",
            "報酬波動大",
            "市場不確定"
        ]
    }
}


# ============================================================================
# ⚙️ 參數配置
# ============================================================================

CONFIGURATION = {
    "n_components": {
        "default": 3,
        "meaning": "隱馬爾可夫模型的隱含狀態數",
        "typical": "3 (Bull, Bear, High Vol)"
    },
    
    "random_state": {
        "default": 42,
        "meaning": "隨機種子，確保可重複性",
        "usage": "同一數據下確保訓練結果一致"
    },
    
    "covariance_type": {
        "value": "full",
        "meaning": "完整協方差矩陣",
        "benefit": "捕捉特徵間的相關性"
    },
    
    "n_iter": {
        "value": 100,
        "meaning": "HMM 訓練迭代次數",
        "benefit": "充分收斂"
    }
}


# ============================================================================
# 📊 性能指標
# ============================================================================

PERFORMANCE = {
    "data_fetch": "1-3 秒（網路速度依賴）",
    "model_training": "100-500 毫秒（5年數據）",
    "prediction": "1-3 秒（含數據獲取）",
    "memory_usage": "低（< 50MB）",
    "cpu_usage": "低（單線程充分）"
}


# ============================================================================
# 🛡️ 錯誤處理
# ============================================================================

ERROR_SCENARIOS = {
    "Network Failure": {
        "behavior": "自動使用緩存或合成數據",
        "outcome": "系統繼續運作"
    },
    
    "Missing Data": {
        "behavior": "ValueError with detail",
        "outcome": "明確錯誤訊息"
    },
    
    "Predict Before Fit": {
        "behavior": "RuntimeError",
        "outcome": "提示先調用 fit()"
    },
    
    "Empty DataFrame": {
        "behavior": "Synthetic fallback",
        "outcome": "系統不崩潰"
    }
}


# ============================================================================
# 🔧 常見操作
# ============================================================================

COMMON_OPERATIONS = {
    "載入自定義數據": """
        import pandas as pd
        spy_data = pd.read_csv('spy.csv', index_col=0, parse_dates=True)
        detector.fit(spy_data)
    """,
    
    "連續監控": """
        while True:
            regime = detector.predict_regime()
            print(f"Current: {regime}")
            time.sleep(3600)  # 每小時檢查
    """,
    
    "回測": """
        train_data = data.iloc[:500]
        test_data = data.iloc[500:]
        detector.fit(train_data)
        regime = detector.predict_regime(test_data)
    """,
    
    "檢查特徵": """
        features, df = detector._prepare_features(data)
        print(f"Shape: {features.shape}")
        print(f"Returns range: {features[:, 0].min():.4f} to {features[:, 0].max():.4f}")
    """
}


# ============================================================================
# 📈 型別簽名
# ============================================================================

TYPE_SIGNATURES = {
    "__init__": """
        (n_components: int = 3, random_state: int = 42) -> None
    """,
    
    "fetch_spy_data": """
        (period: str = "5y") -> pd.DataFrame
    """,
    
    "fit": """
        (spy_data: Optional[pd.DataFrame] = None) -> None
    """,
    
    "predict_regime": """
        (spy_data: Optional[pd.DataFrame] = None) -> int
    """,
    
    "_prepare_features": """
        (df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]
    """
}


# ============================================================================
# ✅ 檢查清單
# ============================================================================

DEPLOYMENT_CHECKLIST = """
部署前檢查:
  □ requirements.txt 已安裝
  □ yfinance 可正常連接
  □ test_market_detector.py 通過
  □ 日誌記錄設置完成
  □ 緩存目錄可寫
  □ 監控告警已配置

運行時監控:
  □ 定期檢查日誌
  □ 監控網路異常
  □ 追蹤模型準確性
  □ 驗證狀態轉換邏輯

定期維護:
  □ 重新訓練模型（如數據變化大）
  □ 驗證特徵計算
  □ 檢查狀態映射一致性
  □ 更新合成數據基線
"""


# ============================================================================
# 🎓 概念解釋
# ============================================================================

CONCEPTS = {
    "Hidden Markov Model": """
        使用隱含狀態序列模型化市場狀態
        • 3 個隱含狀態代表 3 種市場狀態
        • 狀態間有轉移概率
        • 捕捉市場狀態的粘性（stickiness）
    """,
    
    "Label Sorting": """
        解決 HMM 狀態代碼隨機性問題
        • 根據波動率均值排序
        • 確保一致的狀態映射
        • 穩定的市場解釋
    """,
    
    "StandardScaler": """
        特徵標準化（μ=0, σ=1）
        • 改善 HMM 收斂速度
        • 防止特徵主導偏差
        • 確保數值穩定性
    """,
    
    "Annualization": """
        將日波動率轉換為年化波動率
        • 乘以 √252（252=年交易天數）
        • 便於與年度預期比較
        • 標準化波動率表示
    """
}


# ============================================================================
# 📞 故障排除
# ============================================================================

TROUBLESHOOTING = {
    "無法連接 Yahoo Finance": {
        "症狀": "Network error in fetch_spy_data()",
        "解決": "系統自動使用緩存或合成數據，檢查網路連接"
    },
    
    "模型訓練失敗": {
        "症狀": "ValueError in fit()",
        "解決": "檢查數據完整性，確保 'Close' 列存在"
    },
    
    "預測結果不穩定": {
        "症狀": "Regime 頻繁變化",
        "解決": "正常現象（市場轉換），或檢查數據品質"
    },
    
    "內存使用過高": {
        "症狀": "Memory error",
        "解決": "減少訓練數據，或增加系統內存"
    }
}


# ============================================================================
# 📚 進階主題
# ============================================================================

ADVANCED_TOPICS = {
    "模型持久化": """
        import joblib
        joblib.dump(detector, 'detector.pkl')
        detector = joblib.load('detector.pkl')
    """,
    
    "超參數調優": """
        # 測試不同的狀態數
        for n in [2, 3, 4]:
            det = MarketRegimeDetector(n_components=n)
            det.fit()
            score = evaluate(det)
    """,
    
    "多資產擴展": """
        # 可擴展支持 QQQ, IWM 等
        assets = ['SPY', 'QQQ', 'IWM']
        detectors = {asset: MarketRegimeDetector() 
                     for asset in assets}
    """,
    
    "實時流處理": """
        # 集成實時數據流
        from kafka import KafkaConsumer
        for msg in consumer:
            regime = detector.predict_regime(msg)
    """
}


print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                        QUICK REFERENCE READY                              ║
╚════════════════════════════════════════════════════════════════════════════╝

查看以下文件獲取詳細信息:
  • USAGE_EXAMPLES.py         - 7 個實際場景
  • MARKET_DETECTOR_DOCS.md   - 技術文檔
  • test_market_detector.py   - 集成測試

快速開始: python USAGE_EXAMPLES.py
""")
