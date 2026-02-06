
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_loader import DataLoader
from indicators import Indicators
from strategies import Strategies
import datetime
import os

st.set_page_config(layout="wide", page_title="A股全市场选股策略")

# Title and Intro
st.title("A股全市场选股 (本地离线版)")
st.markdown("""
基于 **AkShare** 本地数据仓库，覆盖全市场（剔除ST/科创/北交）。
**使用前请确保已运行 `download_data.py` 更新本地数据。**
""")

# --- Sidebar ---
st.sidebar.header("配置")

# Date Range
today = datetime.datetime.now().date()
start_date = st.sidebar.date_input("开始日期", today - datetime.timedelta(days=365))
end_date = st.sidebar.date_input("结束日期", today)

# Strategy Selection
st.sidebar.subheader("策略选择")
with st.sidebar.expander("📖 策略说明 (User Guide)"):
    st.markdown("""
    **一、强势跟随类**
    1. **Fighting / DTR Plus**: MACD翻红 + 股价/成交量创52周新高 + 站上均线。
    2. **CYC MAX**: 股价站上无穷成本均线(CYC_Inf)和短线成本(CYC_13)，全获利状态。
    3. **Range Breakout**: 突破52周震荡箱体上沿。
    4. **20VMA**: 长期缩量后首次放量突破20日均量线。
    5. **HMC 动量**: MACD柱状图持续走强。
    6. **HPS 趋势**: 站上EMA200且突破EMA15通道。
    7. **TKOS 股王**: 月度动量极强 (近似20日涨幅>30%)。
    
    **二、超跌底部类**
    1. **Limit 极致缩量**: 成交量 < 20日均量的一半。
    2. **布林长中下**: 长期弱势后，首次站上中轨并触碰上轨。
    3. **RSI2 回归**: 长期多头趋势中，RSI2连续两天<10，捕捉超卖。
    4. **2B 法则**: 跌破前低后迅速收回，形成底背离。
    5. **Wyckoff 吸筹**: 长期缩量吸筹后放量突破。
    6. **Spring 弹簧**: 跌破支撑迅速缩量拉回。
    7. **Pinbar**: 长下影线探底。
    8. **ES 波动率**: 波动率极度压缩，变盘在即。
    """)

st.sidebar.markdown("**强势跟随类**")
col1, col2 = st.sidebar.columns(2)
with col1:
    strat_fighting = st.checkbox("Fighting", value=True)
    strat_cyc = st.checkbox("CYC MAX")
    strat_range = st.checkbox("Range Break")
    strat_20vma = st.checkbox("20VMA")
with col2:
    strat_hmc = st.checkbox("HMC 动量")
    strat_hps = st.checkbox("HPS 趋势")
    strat_tkos = st.checkbox("TKOS 股王")

st.sidebar.markdown("**超跌底部类**")
col3, col4 = st.sidebar.columns(2)
with col3:
    strat_limit = st.checkbox("Limit 缩量", value=True)
    strat_boll = st.checkbox("布林回归")
    strat_rsi = st.checkbox("RSI2 回归")
    strat_2b = st.checkbox("2B 法则")
with col4:
    strat_wyckoff = st.checkbox("Wyckoff")
    strat_spring = st.checkbox("Spring")
    strat_pinbar = st.checkbox("Pinbar")
    strat_es = st.checkbox("ES 波动率")

# Initialize Loader
@st.cache_resource
def get_loader():
    return DataLoader()

loader = get_loader()

# Check Data Status
stock_list_df = loader.get_stock_list()
if stock_list_df.empty:
    st.error("⚠️ 本地数据仓库未找到！请先运行 `python download_data.py` 下载数据。")
else:
    st.sidebar.success(f"本地数据就绪: {len(stock_list_df)} 只股票")

# --- Session State Management ---
if 'scan_results' not in st.session_state:
    st.session_state['scan_results'] = None

# --- Main Logic ---

if st.sidebar.button("开始筛选 / Run Screening"):
    if stock_list_df.empty:
        st.error("无法开始：请先下载数据。")
        st.stop()
        
    st.info("正在扫描本地数据... (速度取决于硬盘IO)")
    
    stock_codes = stock_list_df['code'].tolist()
    # Optional: Limit for debug
    # stock_codes = stock_codes[:500] 
    
    results = []
    
    # Progress UI
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(stock_codes)
    
    for i, code in enumerate(stock_codes):
        if i % 100 == 0:
            progress_bar.progress((i + 1) / total)
            status_text.text(f"Scanning {i}/{total}: {code}")
        
        # Fetch Data (Local)
        df = loader.get_k_data(code, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        
        # Skip empty or short history
        if df.empty or len(df) < 120: continue
        
        # Add Indicators
        try:
            df = Indicators.add_all_indicators(df)
            
            # Check Strategies
            sigs = Strategies.check_all(df)
            
            # Get latest signal (today)
            last_sig = sigs.iloc[-1]
            
            triggered = []
            if strat_fighting and last_sig.get('Signal_Fighting'): triggered.append("Fighting")
            if strat_cyc and last_sig.get('Signal_CYC_MAX'): triggered.append("CYC_MAX")
            if strat_range and last_sig.get('Signal_RangeBreak'): triggered.append("RangeBreak")
            if strat_20vma and last_sig.get('Signal_20VMA'): triggered.append("20VMA")
            if strat_hmc and last_sig.get('Signal_HMC'): triggered.append("HMC")
            if strat_hps and last_sig.get('Signal_HPS'): triggered.append("HPS")
            if strat_tkos and last_sig.get('Signal_TKOS'): triggered.append("TKOS")
            
            if strat_limit and last_sig.get('Signal_Limit'): triggered.append("Limit")
            if strat_boll and last_sig.get('Signal_Boll_Rev'): triggered.append("Boll_Rev")
            if strat_rsi and last_sig.get('Signal_RSI2_Rev'): triggered.append("RSI2_Rev")
            if strat_2b and last_sig.get('Signal_2B'): triggered.append("2B")
            if strat_wyckoff and last_sig.get('Signal_Wyckoff'): triggered.append("Wyckoff")
            if strat_spring and last_sig.get('Signal_Spring'): triggered.append("Spring")
            if strat_pinbar and last_sig.get('Signal_Pinbar'): triggered.append("Pinbar")
            if strat_es and last_sig.get('Signal_ES'): triggered.append("ES")
            
            if triggered:
                row = stock_list_df[stock_list_df['code'] == code].iloc[0]
                name = row.get('name', code)
                results.append({
                    "Code": code,
                    "Name": name,
                    "Price": df.iloc[-1]['close'],
                    "Strategies": ", ".join(triggered)
                })
        except Exception as e:
            continue
            
    progress_bar.empty()
    status_text.empty()
    
    if results:
        st.session_state['scan_results'] = pd.DataFrame(results)
        st.success(f"筛选完成！发现 {len(results)} 只符合条件的股票。")
    else:
        st.session_state['scan_results'] = pd.DataFrame()
        st.warning("未找到符合条件的股票。")

# --- Results Display & Charting ---
if st.session_state['scan_results'] is not None and not st.session_state['scan_results'].empty:
    res_df = st.session_state['scan_results']
    # Ensure Code is string match
    res_df['Code'] = res_df['Code'].astype(str)
    
    st.dataframe(res_df, use_container_width=True)
    
    # Layout: Chart Controls | Chart
    st.divider()
    
    # Select Stock
    selected_label = st.selectbox("选择股票查看详情", 
                                  options=[f"{r.Code} - {r.Name}" for _, r in res_df.iterrows()],
                                  key='selected_stock_label')
    if selected_label:
        selected_code = selected_label.split(" - ")[0]
        
        # Safe retrieval of strategy name
        strat_rows = res_df[res_df['Code'] == selected_code]
        if not strat_rows.empty:
            current_strats = strat_rows['Strategies'].values[0]
        else:
            current_strats = "Unknown"
        
        # Chart Controls
        col_ctrl, col_chart = st.columns([1, 3])
        
        with col_ctrl:
            st.subheader("图表配置")
            st.markdown("**主图层**")
            show_ma = st.checkbox("MA20 均线", value=True)
            show_ema = st.checkbox("EMA200 (牛熊线)", value=True)
            show_boll = st.checkbox("布林带", value=True)
            show_signals = st.checkbox("买点信号标注", value=True)
            
            st.markdown("**副图指标**")
            sub_chart_type = st.radio("选择副图:", ["MACD", "Volume", "RSI", "Volatility"])
            
            st.markdown("---")
            st.markdown(f"**当前策略**: {current_strats}")
    
    with col_chart:
        df_sel = loader.get_k_data(selected_code, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        if not df_sel.empty:
            df_sel = Indicators.add_all_indicators(df_sel)
            sigs = Strategies.check_all(df_sel) # Re-calc signals for plotting
            
            # Plotly
            # 2 rows: Main(0.7) + Sub(0.3)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, 
                                row_heights=[0.7, 0.3])

            # --- Main Chart ---
            # Candlestick
            fig.add_trace(go.Candlestick(x=df_sel['date'],
                            open=df_sel['open'], high=df_sel['high'],
                            low=df_sel['low'], close=df_sel['close'], name='K线'), row=1, col=1)
            
            # Overlays
            if show_ma:
                fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['MA20'], line=dict(color='orange', width=1), name='MA20'), row=1, col=1)
            if show_ema:
                fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['EMA200'], line=dict(color='purple', width=1.5), name='EMA200'), row=1, col=1)
            if show_boll:
                fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Boll_Upper'], line=dict(color='gray', width=1, dash='dot'), name='Boll Up'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Boll_Lower'], line=dict(color='gray', width=1, dash='dot'), name='Boll Low'), row=1, col=1)
            
            # Signals
            if show_signals:
                # Plot arrows for triggered signals
                # For simplicity, combine all bullish signals
                # Identify days where ANY selected strategy triggered
                # We need to respect the sidebar selection for visual consistency? 
                # Or just show ALL signals triggered by this stock? 
                # Let's show signals relevant to what's in the results table.
                
                # Re-check which strategies triggered today? No, we want historical signals on chart.
                # Use current sidebar config to decide what 'Signal' means
                
                # Construct combined signal series
                combined_sig = pd.Series(False, index=df_sel.index)
                if strat_fighting: combined_sig |= sigs['Signal_Fighting']
                if strat_cyc: combined_sig |= sigs['Signal_CYC_MAX']
                if strat_20vma: combined_sig |= sigs['Signal_20VMA']
                if strat_limit: combined_sig |= sigs['Signal_Limit']
                if strat_wyckoff: combined_sig |= sigs['Signal_Wyckoff']
                # ... add others if needed, or just these key ones
                
                sig_dates = df_sel[combined_sig]['date']
                sig_prices = df_sel[combined_sig]['low'] * 0.98
                if not sig_dates.empty:
                    fig.add_trace(go.Scatter(x=sig_dates, y=sig_prices, mode='markers', 
                                             marker=dict(symbol='triangle-up', size=10, color='red'), name='Buy Signal'), row=1, col=1)

            # --- Sub Chart ---
            if sub_chart_type == "MACD":
                fig.add_trace(go.Bar(x=df_sel['date'], y=df_sel['MACD_Hist'], name='MACD Hist', marker_color=df_sel['MACD_Hist'].apply(lambda x: 'red' if x>0 else 'green')), row=2, col=1)
                fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['DIF'], line=dict(color='black', width=1), name='DIF'), row=2, col=1)
                fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['DEA'], line=dict(color='blue', width=1), name='DEA'), row=2, col=1)
            
            elif sub_chart_type == "Volume":
                colors = ['red' if r.close > r.open else 'green' for i, r in df_sel.iterrows()]
                fig.add_trace(go.Bar(x=df_sel['date'], y=df_sel['volume'], marker_color=colors, name='Volume'), row=2, col=1)
                # Add VMA20
                if 'Vol_MA20' in df_sel.columns:
                     fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Vol_MA20'], line=dict(color='black', width=1), name='MA20 Vol'), row=2, col=1)
                     
            elif sub_chart_type == "RSI":
                if 'RSI6' in df_sel.columns:
                    fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['RSI6'], name='RSI6'), row=2, col=1)
                if 'RSI2' in df_sel.columns:
                    fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['RSI2'], name='RSI2'), row=2, col=1)
                # Overbought/Oversold lines
                fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=80, y1=80, line=dict(color="gray", dash="dot"), row=2, col=1)
                fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=20, y1=20, line=dict(color="gray", dash="dot"), row=2, col=1)
                
            elif sub_chart_type == "Volatility":
                # Show Bollinger Width or Std
                if 'Std20' in df_sel.columns:
                     fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Std20'], name='Std20'), row=2, col=1)
                     fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Std60'], name='Std60'), row=2, col=1)

            fig.update_layout(height=600, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- Indicator Explanation ---
            with st.expander("💡 指标与战法说明", expanded=True):
                if sub_chart_type == "MACD":
                    st.markdown("""
                    **MACD (平滑异同移动平均线)**
                    - **用法**: 
                        - **Fighting**: 柱状图(Hist)翻红，DIF > DEA，且位于0轴上方，配合K线突破，为主升浪信号。
                        - **底背离**: 股价创新低但 MACD 底部抬高，预示反转。
                    """)
                elif sub_chart_type == "Volume":
                    st.markdown("""
                    **Volume (成交量)**
                    - **Limit 缩量**: 当成交量低于 MA20 的一半时，为主力洗盘极致，变盘在即。
                    - **20VMA 启动**: 长期缩量后，成交量首次突破 20日均量线，是趋势启动的信号。
                    """)
                elif sub_chart_type == "RSI":
                    st.markdown("""
                    **RSI (相对强弱指标)**
                    - **RSI2 回归**: 短期震荡策略。在上升趋势中，RSI2 < 10 (或25) 代表极度超卖，是回调买点。
                    """)
                elif sub_chart_type == "Volatility":
                     st.markdown("""
                    **Volatility (波动率)**
                    - **ES 压缩**: Std20 小于长周期波动率，代表K线形态收敛到极致（心电图），通常紧接着剧烈变盘。
                    """)

elif st.session_state['scan_results'] is None:
    st.info("请点击左侧按钮开始筛选。")
