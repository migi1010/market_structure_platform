"""
Market Structure & Alpha Intelligence Dashboard
美股中週期多因子選股平台 - 網頁視覺化面板 (繁體中文專業版)
Author: Market Structure Platform Team
"""

import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 頁面基本配置
st.set_page_config(
    page_title="Alpha Intelligence 決策面板",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 檔案路徑定義
JSON_REPORT_PATH = "./reports/daily_report.json"
ALPHA_CSV_PATH = "./reports/alpha_scores.csv"
SMART_MONEY_CSV_PATH = "./reports/smart_money_signals.csv"
BUBBLE_CSV_PATH = "./reports/bubble_alerts.csv"

# 自訂 CSS 樣式增強視覺，採用高質感深色主體
st.markdown("""
    <style>
    .main { background-color: #0f1116; color: #ffffff; }
    .stMetric { background-color: #1a1c23; padding: 15px; border-radius: 10px; border: 1px solid #2d3139; }
    h1, h2, h3 { color: #00ffcc !important; }
    div.stDataFrame { background-color: #1a1c23; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)


def load_data():
    """安全載入盤後 Pipeline 生成的數據 (內建空值防禦機制)"""
    data = {
        "summary": {},
        "alpha_df": pd.DataFrame(),
        "smart_money_df": pd.DataFrame(),
        "bubble_df": pd.DataFrame()
    }
    
    if os.path.exists(JSON_REPORT_PATH):
        try:
            with open(JSON_REPORT_PATH, 'r', encoding='utf-8') as f:
                data["summary"] = json.load(f)
        except Exception as e:
            st.error(f"讀取 daily_report.json 失敗: {e}")
            
    if os.path.exists(ALPHA_CSV_PATH):
        try:
            data["alpha_df"] = pd.read_csv(ALPHA_CSV_PATH)
        except Exception as e:
            st.error(f"讀取 alpha_scores.csv 失敗: {e}")
        
    if os.path.exists(SMART_MONEY_CSV_PATH):
        try:
            data["smart_money_df"] = pd.read_csv(SMART_MONEY_CSV_PATH)
        except Exception as e:
            st.error(f"讀取 smart_money_signals.csv 失敗: {e}")
        
    if os.path.exists(BUBBLE_CSV_PATH):
        try:
            data["bubble_df"] = pd.read_csv(BUBBLE_CSV_PATH)
        except Exception as e:
            st.error(f"讀取 bubble_alerts.csv 失敗: {e}")
        
    return data

def translate_regime(regime_name: str) -> str:
    """翻譯市場體制為直白繁體中文"""
    regime_name_lower = regime_name.lower()
    if "bull" in regime_name_lower:
        return "低波動牛市 🐂"
    elif "bear" in regime_name_lower:
        return "高波動熊市 🐻"
    elif "volatility" in regime_name_lower:
        return "高波動震盪輪動盤 ⚡"
    return regime_name

def rename_columns_to_tw(df: pd.DataFrame) -> pd.DataFrame:
    """將常見欄位名稱翻譯為繁體中文"""
    rename_dict = {
        'Ticker': '美股代號',
        'ticker': '美股代號',
        'Alpha_Score': '綜合因子得分',
        'alpha_score': '綜合因子得分',
        'Theme_Score': '板塊相對強度得分',
        'theme_score': '板塊相對強度得分',
        'Volume_Ratio': '今日成交量倍數',
        'volume_ratio': '今日成交量倍數',
        'Bubble_Score': '多維泡沫風險評分',
        'bubble_score': '多維泡沫風險評分',
        'Signal_Strength': '機構吸籌信號強度',
        'Growth': '成長因子',
        'Quality': '品質因子',
        'Valuation': '估值因子',
        'MomentumBubble': '動能泡沫警告'
    }
    # 只替換存在的欄位
    existing_renames = {k: v for k, v in rename_dict.items() if k in df.columns}
    return df.rename(columns=existing_renames)

def main():
    # 側邊欄配置
    st.sidebar.title("🦅 Alpha Intelligence")
    st.sidebar.markdown("---")
    st.sidebar.info("🤖 核心戰略：美股中週期多因子配置平台（Universe: S&P 500 / Nasdaq 100）")
    st.sidebar.markdown("---")
    st.sidebar.write("⚡ *系統狀態: 運作正常 (滿血狀態)*")
    
    # 載入數據
    data = load_data()
    
    if not data["summary"] and data["alpha_df"].empty:
        st.error("❌ 找不到盤後報告數據！請先確保在終端機成功執行過 `python orchestrator.py`。")
        return
        
    # 解析摘要資訊
    summary = data["summary"]
    raw_regime_name = summary.get("regime", {}).get("name", "High Volatility") if isinstance(summary.get("regime"), dict) else summary.get("regime_name", "High Volatility")
    regime_name_tw = translate_regime(raw_regime_name)
    
    confidence = summary.get("regime", {}).get("confidence", 1.0) if isinstance(summary.get("regime"), dict) else summary.get("regime_confidence", 1.0)
    duration = summary.get("duration", 0.0)
    timestamp = summary.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 主頁面大標題
    st.title("📊 量化市場結構與 Alpha 決策面板")
    st.write(f"🍏 *數據更新時間：{timestamp} | 流水線耗時：{duration:.2f} 秒*")
    st.markdown("---")
    
    # 頂部三大核心指標區
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="🇨🇭 大盤 HMM 當前體制", value=regime_name_tw)
    with col2:
        st.metric(label="🎯 體制信號信心度", value=f"{confidence * 100:.1f}%")
    with col3:
        total_signals = len(data["smart_money_df"]) + len(data["bubble_df"])
        st.metric(label="🚨 今日量能異常警報總數", value=f"{total_signals} 檔")
        
    st.markdown("##")
    
    # 建立分頁標籤 (對齊你的核心選股綱要)
    tab1, tab2, tab3 = st.tabs(["🏆 綜合因子評級與錯殺選股", "🔥 11大板塊強弱輪動", "🚨 機構吸籌與泡沫警報"])
    
    # ------------------------------------------------------------------
    # TAB 1: Alpha 綜合評級與錯殺選股
    # ------------------------------------------------------------------
    with tab1:
        st.subheader("🎯 核心宇宙 (Universe) 綜合因子得分排序")
        st.write("根據 HMM 市場體制動態調整權重後，計算出的個股總體 Alpha 分數。**得分越高，代表在中週期的勝率及安全邊際越優。**")
        
        if not data["alpha_df"].empty:
            df = data["alpha_df"].copy()
            df = rename_columns_to_tw(df)
            
            # 使用 Plotly 畫出前 10 名的柱狀圖
            if '綜合因子得分' in df.columns and '美股代號' in df.columns:
                top_10 = df.head(10)
                fig_alpha = px.bar(
                    top_10, 
                    x='美股代號', 
                    y='綜合因子得分',
                    color='綜合因子得分',
                    color_continuous_scale='Turbo',
                    title="🔥 Top 10 綜合因子得分領袖股"
                )
                fig_alpha.update_layout(template="plotly_dark")
                st.plotly_chart(fig_alpha, use_container_width=True)
            
            # 顯示完整表格
            st.markdown("### 📋 完整標的打分明細")
            if '綜合因子得分' in df.columns:
                st.dataframe(
                    df.style.background_gradient(subset=['綜合因子得分'], cmap='Greens'),
                    use_container_width=True
                )
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.warning("暫無個股打分數據。")
            
    # ------------------------------------------------------------------
    # TAB 2: 11大板塊強弱輪動
    # ------------------------------------------------------------------
    with tab2:
        st.subheader("🪵 11 大板塊相對強度 (Theme Score) 排序")
        st.write("展示美股各大核心板塊相對於大盤（SPY）的 20 日相對強度與量能變化。**分數越高，代表近期市場資金流入越集中、板塊輪動正在升溫。**")
        
        sector_data = summary.get("sector_rankings", [])
        if sector_data:
            sector_df = pd.DataFrame(sector_data)
            sector_df = rename_columns_to_tw(sector_df)
            
            if '板塊相對強度得分' in sector_df.columns and '美股代號' in sector_df.columns:
                fig_sector = px.bar(
                    sector_df,
                    x='板塊相對強度得分',
                    y='美股代號',
                    orientation='h',
                    color='板塊相對強度得分',
                    color_continuous_scale='Viridis',
                    title="📊 11大板塊資金流入排行榜"
                )
                fig_sector.update_layout(template="plotly_dark", yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_sector, use_container_width=True)
            
            st.dataframe(sector_df, use_container_width=True)
        else:
            st.info("💡 提示：目前尚無板塊相對強度的數據。")
            
    # ------------------------------------------------------------------
    # TAB 3: 機構吸籌與泡沫警報
    # ------------------------------------------------------------------
    with tab3:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 💎 機構明顯吸籌股 (聰明錢追蹤)")
            st.write("篩選邏輯：股價處於中週期低檔或狹幅盤整，但**當日成交量暴增至 20 日均量的 1.5 倍以上**。這通常是機構大戶悄悄進場建倉的鐵證。")
            if not data["smart_money_df"].empty:
                sm_df = data["smart_money_df"].copy()
                sm_df = rename_columns_to_tw(sm_df)
                    
                if '今日成交量倍數' in sm_df.columns:
                    st.dataframe(sm_df.style.format({"今日成交量倍數": "{:.2f}x"}), use_container_width=True)
                else:
                    st.dataframe(sm_df, use_container_width=True)
            else:
                st.success("✅ 今日無異常機構吸籌警報，個股呈常態波動。")
                
        with col_right:
            st.markdown("### 🚨 3D 多維度泡沫出貨警報")
            st.write("篩選邏輯：個股估值嚴重過熱，且出現**高檔放量滯漲或機構異常出貨**。當泡沫風險評分突破 75 分，請強烈警戒潛在的毀滅性回檔。")
            
            if not data["bubble_df"].empty:
                b_df = data["bubble_df"].copy()
                b_df = rename_columns_to_tw(b_df)
                
                # 安全防禦性渲染樣式
                if '多維泡沫風險評分' in b_df.columns:
                    st.dataframe(
                        b_df.style.background_gradient(subset=['多維泡沫風險評分'], cmap='OrRd'),
                        use_container_width=True
                    )
                else:
                    st.dataframe(b_df, use_container_width=True)
            else:
                st.success("✅ 今日無極端泡沫出貨股，個股安全邊際良好。")

if __name__ == "__main__":
    main()