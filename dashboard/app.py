import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# Append project root to sys.path so modules can be imported safely
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from alpha_engine.scoring import ScoringRankingSystem

# ---------------------------------------------------------
# Streamlit App Configuration
# ---------------------------------------------------------
st.set_page_config(page_title="Quant Alpha Intelligence", layout="wide", page_icon="📈")

@st.cache_data(ttl=3600)
def load_system_data():
    """Caches the heavy computation of the Alpha System."""
    system = ScoringRankingSystem()
    df = system.get_final_universe_ranking()
    
    # Extract the current regime context
    regime_code = df['Regime'].iloc[0]
    regime_map = {
        0: "Bull Market 🐂 (Growth & Momentum Bias)",
        1: "Bear Market 🐻 (Quality & Valuation Bias)",
        2: "High Volatility ⚡ (Defensive & Bubble Penalty Active)"
    }
    regime_str = regime_map.get(regime_code, "Unknown")
    return df, regime_str

def main():
    st.sidebar.title("🧠 Alpha Intelligence Platform")
    
    # 5-Page Navigation System
    page = st.sidebar.radio("Navigation Menu", [
        "🏆 Main Dashboard",
        "🏦 Smart Money Tracker",
        "💎 Deep Value Screener",
        "🚨 Bubble Monitor",
        "🔄 Theme Rotation"
    ])
    
    # Load Data Engine
    with st.spinner("Initializing AI Alpha Engine & Scanning Universe..."):
        try:
            df, regime_str = load_system_data()
        except Exception as e:
            st.error(f"Failed to load intelligence data: {str(e)}")
            return

    # ---------------------------------------------------------
    # 1. Main Dashboard
    # ---------------------------------------------------------
    if page == "🏆 Main Dashboard":
        st.title("Market Overview & Alpha Ranking")
        st.info(f"**Current HMM Market Regime:** {regime_str}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 10 Alpha Leaders")
            # Present top 10 ranked stocks
            top_10 = df.head(10)[['alpha_score', 'smart_money', 'theme_score', 'Is_Deep_Value', 'Red_Alert']]
            st.dataframe(top_10.style.background_gradient(cmap='viridis', subset=['alpha_score']), use_container_width=True)
            
        with col2:
            st.subheader("Market Structure Matrix")
            # Scatter plot to visualize Alpha vs Smart Money Flow
            fig = px.scatter(df, x='smart_money', y='alpha_score', color='theme_score', 
                             hover_name=df.index, size='quality',
                             title="Alpha vs Smart Money (Size: Quality, Color: Theme)",
                             template="plotly_dark", color_continuous_scale="Viridis")
            st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # 2. Smart Money Tracker
    # ---------------------------------------------------------
    elif page == "🏦 Smart Money Tracker":
        st.title("Smart Money & Volume Structure")
        ticker = st.text_input("Enter Ticker to Analyze (e.g. AAPL, NVDA):", "NVDA").upper()
        
        st.markdown(f"#### Scanning Institutional Volume Footprints for **{ticker}**...")
        
        # Mocking specific RVOL data to demonstrate the Plotly bar chart
        np.random.seed(hash(ticker) % (2**32))
        dates = pd.date_range(end=pd.Timestamp.today(), periods=40, freq='B')
        rvol = np.random.normal(1.0, 0.6, 40).clip(0.1, 4.0)
        
        # Color coding: Green for accumulation/breakout (RVOL > 1.5), Gray for normal
        colors = ['#00ff00' if r > 1.5 else '#555555' for r in rvol]
        
        fig = go.Figure(data=[go.Bar(
            x=dates, y=rvol, marker_color=colors, name="RVOL"
        )])
        fig.add_hline(y=1.5, line_dash="dot", line_color="red", annotation_text="Breakout Threshold (1.5x)")
        fig.update_layout(title=f"{ticker} 40-Day Relative Volume (RVOL)", template="plotly_dark", yaxis_title="RVOL (Multiple of 20MA)")
        st.plotly_chart(fig, use_container_width=True)
        
    # ---------------------------------------------------------
    # 3. Deep Value Screener
    # ---------------------------------------------------------
    elif page == "💎 Deep Value Screener":
        st.title("Deep Value Targets (Left-Side Opportunities)")
        st.markdown("Filter criteria: **30-60% Drawdown + Revenue Growth > 10% + ROE > 15% + FCF > 0**")
        
        deep_value_df = df[df['Is_Deep_Value'] == True]
        if not deep_value_df.empty:
            st.success(f"Found {len(deep_value_df)} Deep Value Candidates in the Universe.")
            st.dataframe(deep_value_df[['alpha_score', 'quality', 'valuation', 'smart_money']].sort_values(by='valuation', ascending=False), use_container_width=True)
        else:
            st.warning("No stocks meet the strict deep value criteria at this moment.")

    # ---------------------------------------------------------
    # 4. Bubble Monitor
    # ---------------------------------------------------------
    elif page == "🚨 Bubble Monitor":
        st.title("Bubble Risk & Distribution Monitor")
        
        red_alerts = df[df['Red_Alert'] == True]
        if not red_alerts.empty:
            st.error(f"⚠️ RED ALERT: Found {len(red_alerts)} stocks exhibiting late-stage euphoria and institutional distribution.")
            st.dataframe(red_alerts[['bubble_score', 'smart_money', 'alpha_score']].style.background_gradient(cmap='Reds', subset=['bubble_score']), use_container_width=True)
        else:
            st.success("No critical Red Alerts in the current universe.")
            
        st.markdown("---")
        st.subheader("Individual Ticker Bubble Gauge")
        target = st.selectbox("Select Ticker for Gauge Analysis:", df.index.tolist())
        score = df.loc[target, 'bubble_score']
        
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"{target} Bubble Risk Score"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkred"},
                'steps' : [
                    {'range': [0, 50], 'color': "rgba(0,255,0,0.3)"},
                    {'range': [50, 75], 'color': "rgba(255,255,0,0.3)"},
                    {'range': [75, 100], 'color': "rgba(255,0,0,0.3)"}],
                'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 85}
            }
        ))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # 5. Theme Rotation
    # ---------------------------------------------------------
    elif page == "🔄 Theme Rotation":
        st.title("Sector & Theme Rotation Trends")
        st.markdown("Analyzing capital flows across major ETF themes (Mock Historical Tracking).")
        
        # Mocking theme data for Plotly line chart
        dates = pd.date_range(end=pd.Timestamp.today(), periods=60, freq='B')
        themes = ['Semiconductors (SMH)', 'AI & Cloud (SKYY)', 'Energy (XLE)', 'Defense (ITA)']
        
        fig = go.Figure()
        np.random.seed(88)
        for theme in themes:
            # Generate a random walk that looks like trend momentum
            scores = np.cumprod(1 + np.random.normal(0.002, 0.015, 60)) * 50
            fig.add_trace(go.Scatter(x=dates, y=scores, mode='lines', name=theme, line=dict(width=3)))
            
        fig.update_layout(
            title="Capital Flow Momentum (Theme Scores)", 
            template="plotly_dark",
            yaxis_title="Theme Score",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
