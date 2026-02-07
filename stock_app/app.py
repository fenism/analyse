
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
st.title("A股全市场选股")
st.markdown("""
基于 **本地数据仓库 (Local Data Warehouse)**，覆盖全市场（剔除ST/科创/北交）。
**使用前请确保已运行数据下载脚本更新本地数据。**
""")

# --- Sidebar Configuration ---
st.sidebar.header("配置")

# --- Data Status Section ---
with st.sidebar.expander("📊 数据状态 (Data Status)", expanded=True):
    # Count stock list
    list_path = os.path.join("stock_app/data/market_data", "stock_list.csv")
    total_stocks = 0
    if os.path.exists(list_path):
        try:
            total_stocks = sum(1 for line in open(list_path)) - 1 # minus header
        except: pass
        
    # Count downloaded files
    data_dir = "stock_app/data/market_data"
    downloaded_count = 0
    if os.path.exists(data_dir):
        files = [name for name in os.listdir(data_dir) if name.endswith('.csv')]
        downloaded_count = len(files)
        if "stock_list.csv" in files:
            downloaded_count -= 1
            
    if total_stocks > 0:
        progress = downloaded_count / total_stocks
        st.progress(min(progress, 1.0))
        st.write(f"已下载: **{downloaded_count}** / {total_stocks}")
    else:
        st.error("未找到股票列表")
        
    if st.button("🔄 刷新下载进度"):
        st.rerun()
        
    st.markdown("---")
    if st.button("📥 立即下载行情数据 (Download)", help="从腾讯财经下载日线数据到本地"):
        import concurrent.futures
        import requests
        import json
        
        # Define download logic inline or import if path allows
        # To ensure stability, let's use a simplified inline version or call the script function if adjusted.
        # Let's use a robust inline version adapted for Streamlit.
        
        status_container = st.status("正在初始化下载任务...", expanded=True)
        
        # 1. Check Stock List
        if not os.path.exists(list_path):
            status_container.write("正在获取全市场股票列表...")
            try:
                import akshare as ak
                stock_df = ak.stock_zh_a_spot_em()
                stock_df = stock_df[['代码', '名称']]
                stock_df.columns = ['code', 'name']
                stock_df.to_csv(list_path, index=False)
                status_container.write(f"已创建股票列表: {len(stock_df)} 只")
            except Exception as e:
                status_container.error(f"获取股票列表失败: {e}")
                st.stop()
        else:
            stock_df = pd.read_csv(list_path, dtype={'code': str})
            
        # 2. Download Loop
        stocks = stock_df.to_dict('records')
        total_d = len(stocks)
        params_list = []
        
        # Prepare params
        for s in stocks:
             code = s['code']
             if code.startswith('6'): symbol = f"sh{code}"
             elif code.startswith('0') or code.startswith('3'): symbol = f"sz{code}"
             else: symbol = f"sz{code}" # fallback
             params_list.append((code, symbol))
             
        status_container.write("正在并发下载数据 (Tencent API)...")
        progress_bar = status_container.progress(0)
        
        def download_one(args):
            c, sym = args
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={sym},day,,,600,qfq"
            try:
                r = requests.get(url, timeout=2)
                if r.status_code != 200: return False
                content = r.text
                if "=" in content: json_str = content.split("=", 1)[1]
                else: json_str = content
                data = json.loads(json_str)
                k_data = data.get('data', {}).get(sym, {})
                klines = k_data.get('qfqday', []) or k_data.get('day', [])
                if not klines: return False
                
                # Save
                cols = ['date', 'open', 'close', 'high', 'low', 'volume']
                recs = []
                for k in klines:
                    if len(k) < 6: continue
                    recs.append({
                        'date': k[0], 
                        'open': k[1], 'close': k[2], 
                        'high': k[3], 'low': k[4], 'volume': k[5]
                    })
                if recs:
                    original_data_path = "stock_app/data/market_data"
                    if not os.path.exists(original_data_path): os.makedirs(original_data_path)
                    pd.DataFrame(recs).to_csv(os.path.join(original_data_path, f"{c}.csv"), index=False)
                    return True
            except:
                return False
            return False

        # Run ThreadPool
        done_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(download_one, p) for p in params_list]
            for f in concurrent.futures.as_completed(futures):
                done_count += 1
                if done_count % 50 == 0:
                    progress_bar.progress(done_count / total_d)
                    
        status_container.update(label="下载完成!", state="complete", expanded=False)
        st.success(f"下载任务结束。请刷新页面查看数据状态。")
        st.rerun()

# --- Theme Toggle ---
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'

def toggle_theme():
    if st.session_state['theme'] == 'light':
        st.session_state['theme'] = 'dark'
    else:
        st.session_state['theme'] = 'light'

st.sidebar.button("💡 切换亮/暗模式 (Toggle Theme)", on_click=toggle_theme)

# Apply Theme
if st.session_state['theme'] == 'dark':
    # Custom CSS for Dark Mode (Black Background)
    st.markdown("""
    <style>
    /* Main Area */
    .stApp {
        background-color: #0e1117; 
        color: #FFFFFF;
    }
    
    /* Sidebar - Force Dark Background */
    section[data-testid="stSidebar"] {
        background-color: #262730; 
        color: #FFFFFF;
    }
    
    /* Text Colors */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, label, .stCheckbox, p {
        color: #FFFFFF !important;
    }
    
    /* Input Fields Background */
    div[data-baseweb="input"] {
        background-color: #262730 !important;
        color: #FFFFFF !important;
    }
    input {
        color: #FFFFFF !important;
    }
    
    /* Selectbox/Dropdown options */
    div[data-baseweb="select"] > div {
        background-color: #262730 !important;
        color: #FFFFFF !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #262730 !important;
        color: #FFFFFF !important;
    }
    
    /* Progress Bar Text */
    div[data-testid="stMarkdownContainer"] p {
        color: #FFFFFF !important;
    }
    
    /* Buttons */
    button {
        background-color: #262730 !important;
        color: #FFFFFF !important;
        border: 1px solid #4b4b4b !important;
    }
    button p {
        color: #FFFFFF !important;
    }
    button:hover {
        border-color: #ff4b4b !important;
        color: #ff4b4b !important;
    }
    button:hover p {
        color: #ff4b4b !important;
    }
    
    /* Header (Top Bar) */
    header[data-testid="stHeader"] {
        background-color: #0e1117 !important;
    }
    header[data-testid="stHeader"] button {
        background-color: transparent !important;
        border: none !important;
    }
    header[data-testid="stHeader"] svg {
        fill: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)
    plotly_template = 'plotly_dark'
else:
    # Light Mode
    st.markdown("""
    <style>
    /* Main Area and Global Defaults */
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #F0F2F6;
    }
    
    /* Force Text Color */
    .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, 
    .stApp label, .stApp span, .stApp div[data-testid="stMarkdownContainer"] {
        color: #000000 !important;
    }
    
    /* Specific Widget Overrides */
    .stRadio div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }
    .stCheckbox label div[data-testid="stMarkdownContainer"] p {
         color: #000000 !important;
    }
    
    /* Inputs (Date, Select, Text) - Force White Background */
    div[data-baseweb="input"], 
    div[data-baseweb="select"] > div, 
    div[data-baseweb="base-input"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #E0E0E0 !important;
    }
    
    /* Input Text Color inside the box */
    input[type="text"], input[type="number"], input {
        color: #000000 !important;
    }
    
    /* Dropdown menu items */
    ul[data-baseweb="menu"] li {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }

    /* Buttons */
    .stButton button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #CCCCCC !important;
    }
    .stButton button:hover {
        background-color: #E0E0E0 !important;
        border-color: #999999 !important;
    }

    /* Expanders */
    div[data-testid="stExpander"] details summary {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #E0E0E0 !important;
    }
    div[data-testid="stExpander"] details summary span {
        color: #000000 !important;
    }
    div[data-testid="stExpander"] details {
        border-color: #E0E0E0 !important;
    }

    /* Progress Bar Text */
    div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    plotly_template = 'plotly_white'

# --- Common Date Configuration ---
today = datetime.datetime.now().date()
# Default dates (Screening window default)
default_end = today
default_start = today - datetime.timedelta(days=180)
# Calculation start date (for indicators) - derived from default_start
calc_start_date = default_start - datetime.timedelta(days=400) 

# --- Mode Selection ---
st.sidebar.markdown("---")
app_mode = st.sidebar.radio("模式选择 (Mode)", ["策略选股 (Screening)", "个股行情 (Analysis)"])

# --- Strategy Selection (Sidebar) ---
# Only show strategy selection in Screening Mode? 
# Or keep it visible to let user see what strategies are available?
# Let's keep it visible in sidebar as per original design, largely for Screening.
st.sidebar.subheader("策略配置 (仅选股模式生效)")
with st.sidebar.expander("📖 策略说明"):
    st.markdown("""
    ... (策略说明略, 见完整文档) ...
    """)

st.sidebar.markdown("**强势跟随类**")
col1, col2 = st.sidebar.columns(2)
with col1:
    strat_fighting = st.checkbox("Fighting", value=True)
    strat_cyc = st.checkbox("CYC MAX")
    strat_range = st.checkbox("Range Break")
    strat_20vma = st.checkbox("20VMA")
    strat_rking = st.checkbox("Rking 趋势")
with col2:
    strat_hmc = st.checkbox("HMC 动量")
    strat_hps = st.checkbox("HPS 趋势")
    strat_tkos = st.checkbox("TKOS 股王")

st.sidebar.markdown("**超跌底部类**")
col3, col4 = st.sidebar.columns(2)
with col3:
    strat_limit = st.checkbox("Limit 缩量")
    strat_boll = st.checkbox("布林回归")
    strat_rsi = st.checkbox("RSI2 回归")
    strat_2b = st.checkbox("2B 法则")
with col4:
    strat_wyckoff = st.checkbox("Wyckoff")
    strat_spring = st.checkbox("Spring")
    strat_pinbar = st.checkbox("Pinbar")
    strat_es = st.checkbox("ES 波动率")



def plot_stock_chart(df_sel, code, name, show_ma, show_ema, show_boll, show_cyc, show_ema15, show_box, show_supt, show_signals, sub_chart_type, plotly_template, sigs=None, signal_dates=None):
    if df_sel.empty:
        st.warning("No data to plot.")
        return

    # Plotly
    # 2 rows: Main(0.7) + Sub(0.3)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, 
                        row_heights=[0.7, 0.3])
    
    # Apply Template
    fig.update_layout(template=plotly_template)

    # --- Main Chart ---
    # Candlestick
    fig.add_trace(go.Candlestick(x=df_sel['date'],
                    open=df_sel['open'], high=df_sel['high'],
                    low=df_sel['low'], close=df_sel['close'],
                    increasing_line_color='red', decreasing_line_color='green',
                    name='K线'), row=1, col=1)
    
    # Overlays
    if show_ma and 'MA20' in df_sel.columns:
        fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['MA20'], line=dict(color='orange', width=1), name='MA20'), row=1, col=1)
    if show_ema and 'EMA200' in df_sel.columns:
        fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['EMA200'], line=dict(color='purple', width=1.5), name='EMA200'), row=1, col=1)
    if show_ema15 and 'EMA_High_15' in df_sel.columns:
         fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['EMA_High_15'], line=dict(color='blue', width=1), name='HPS Channel (EMA15 High)'), row=1, col=1)
    
    if show_cyc:
         if 'CYC_Inf' in df_sel.columns:
             fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['CYC_Inf'], line=dict(color='brown', width=1.5), name='CYC无穷'), row=1, col=1)
         if 'CYC_13' in df_sel.columns:
             fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['CYC_13'], line=dict(color='cyan', width=1, dash='dot'), name='CYC短线'), row=1, col=1)
             
    if show_boll and 'Boll_Upper' in df_sel.columns:
        fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Boll_Upper'], line=dict(color='gray', width=1, dash='dot'), name='Boll Up'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Boll_Lower'], line=dict(color='gray', width=1, dash='dot'), name='Boll Low'), row=1, col=1)
        
    # Strategy Specific Overlays (Box Top, Support, etc)
    if show_box and 'High_52' in df_sel.columns:
        fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['High_52'], line=dict(color='green', width=1, dash='dash'), name='Box Top (250日)'), row=1, col=1)
    if show_supt and 'Low_20' in df_sel.columns:
        fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Low_20'], line=dict(color='red', width=1, dash='dot'), name='Support (20日)'), row=1, col=1)
    
    # RKing Main Chart Overlay REMOVED
    
    # Signals (Custom passed dates)
    if show_signals and signal_dates is not None and not signal_dates.empty:
        # Filter df to find prices for these dates
        mask = df_sel['date'].isin(signal_dates)
        sig_points = df_sel[mask]
        if not sig_points.empty:
            fig.add_trace(go.Scatter(x=sig_points['date'], y=sig_points['low'] * 0.98, mode='markers', 
                                     marker=dict(symbol='triangle-up', size=12, color='red'), name='Strategy Signal'), row=1, col=1)

    # --- Sub Chart ---
    if sub_chart_type == "MACD":
        fig.add_trace(go.Bar(x=df_sel['date'], y=df_sel['MACD_Hist'], name='MACD Hist', marker_color=df_sel['MACD_Hist'].apply(lambda x: 'red' if x>0 else 'green')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['DIF'], line=dict(color='black', width=1), name='DIF'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['DEA'], line=dict(color='blue', width=1), name='DEA'), row=2, col=1)
    
    elif sub_chart_type == "KDJ":
        if 'K' in df_sel.columns:
            fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['K'], name='K'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['D'], name='D'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['J'], name='J'), row=2, col=1)
            fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=20, y1=20, line=dict(color="gray", dash="dot"), row=2, col=1)
            fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=80, y1=80, line=dict(color="gray", dash="dot"), row=2, col=1)

    elif sub_chart_type == "WR":
        if 'WR' in df_sel.columns:
            fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['WR'], name='Williams %R'), row=2, col=1)
            fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=-20, y1=-20, line=dict(color="gray", dash="dot"), row=2, col=1)
            fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=-80, y1=-80, line=dict(color="gray", dash="dot"), row=2, col=1)

    elif sub_chart_type == "CCI":
        if 'CCI' in df_sel.columns:
            fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['CCI'], name='CCI'), row=2, col=1)
            fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=100, y1=100, line=dict(color="gray", dash="dot"), row=2, col=1)
            fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=-100, y1=-100, line=dict(color="gray", dash="dot"), row=2, col=1)

    elif sub_chart_type == "Volume":
        colors = ['red' if r.close > r.open else 'green' for i, r in df_sel.iterrows()]
        fig.add_trace(go.Bar(x=df_sel['date'], y=df_sel['volume'], marker_color=colors, name='Volume'), row=2, col=1)
        if 'Vol_MA20' in df_sel.columns:
             fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Vol_MA20'], line=dict(color='black', width=1), name='MA20 Vol'), row=2, col=1)
    
    elif sub_chart_type == "RKing (趋势)":
        # RKing is a Heikin-Ashi based system with Bands
        # Plot X-Candles
        if 'XOpen' in df_sel.columns:
            # Custom Candles
            fig.add_trace(go.Candlestick(x=df_sel['date'],
                            open=df_sel['XOpen'], high=df_sel['XHigh'],
                            low=df_sel['XLow'], close=df_sel['XClose'],
                            increasing_line_color='red', decreasing_line_color='green',
                            name='RKing HA'), row=2, col=1)
            
            # Bands
            if 'RKing_Upper' in df_sel.columns:
                fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['RKing_Upper'], line=dict(color='orange', width=1), name='RKing UP'), row=2, col=1)
                fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['RKing_Lower'], line=dict(color='cyan', width=1), name='RKing DOWN'), row=2, col=1)

            # Signals
            bu_mask = df_sel['RKing_BU']
            sel_mask = df_sel['RKing_SEL']
            
            # Adjust marker position relative to XLow/XHigh
            fig.add_trace(go.Scatter(x=df_sel[bu_mask]['date'], y=df_sel[bu_mask]['XLow']*0.98, mode='markers', 
                                     marker=dict(symbol='triangle-up', size=10, color='yellow'), name='Buy'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_sel[sel_mask]['date'], y=df_sel[sel_mask]['XHigh']*1.02, mode='markers', 
                                     marker=dict(symbol='triangle-down', size=10, color='blue'), name='Sell'), row=2, col=1)

    elif sub_chart_type == "RSI":
        if 'RSI6' in df_sel.columns:
            fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['RSI6'], name='RSI6'), row=2, col=1)
        if 'RSI2' in df_sel.columns:
            fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['RSI2'], name='RSI2'), row=2, col=1)
        fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=80, y1=80, line=dict(color="gray", dash="dot"), row=2, col=1)
        fig.add_shape(type="line", x0=df_sel['date'].iloc[0], x1=df_sel['date'].iloc[-1], y0=20, y1=20, line=dict(color="gray", dash="dot"), row=2, col=1)
        
    elif sub_chart_type == "Volatility":
        if 'Std20' in df_sel.columns:
             fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Std20'], name='Std20'), row=2, col=1)
             fig.add_trace(go.Scatter(x=df_sel['date'], y=df_sel['Std60'], name='Std60'), row=2, col=1)

    fig.update_layout(height=600, margin=dict(l=0, r=0, t=30, b=0), title=f"{code} - {name} ({df_sel['date'].iloc[-1].strftime('%Y-%m-%d')})")
    fig.update_xaxes(rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Indicator Explanation
    st.markdown("### 📚 指标与战法说明")
    with st.expander("点击展开查看详细说明", expanded=False):
        if sub_chart_type == "MACD":
            st.markdown("""
            **MACD (平滑异同移动平均线)**
            - **用法**: 
                - **Fighting**: 柱状图(Hist)翻红，DIF > DEA，且位于0轴上方，配合K线突破，为主升浪信号。
                - **底背离**: 股价创新低但 MACD 底部抬高，预示反转。
            """)
        elif sub_chart_type == "KDJ":
             st.markdown("""
            **KDJ (随机指标)**
            - **用法**:
                - **超买**: J > 100, K/D > 80.
                - **超卖**: J < 0, K/D < 20.
                - **金叉**: K 上穿 D (低位更佳).
            """)
        elif sub_chart_type == "WR":
             st.markdown("""
            **Williams %R (威廉指标)**
            - **用法**:
                - **超买**: %R > -20.
                - **超卖**: %R < -80.
            """)
        elif sub_chart_type == "CCI":
             st.markdown("""
            **CCI (顺势指标)**
            - **用法**:
                - **趋势**: > 100 强势，< -100 弱势。
                - **背离**: 股价创新高但 CCI 未创新高。
            """)
        elif sub_chart_type == "Volume":
            st.markdown("""
            **Volume (成交量)**
            - **Limit 缩量**: 当成交量低于 MA20 的一半时，为主力洗盘极致，变盘在即。
            - **20VMA 启动**: 长期缩量后，成交量首次突破 20日均量线，是趋势启动的信号。
            """)
        elif sub_chart_type == "RKing (趋势)":
            st.markdown("""
            **RKing 趋势跟随系统**
            - **核心逻辑**: 基于平均K线(Heikin-Ashi)变体与波动率通道构建的趋势系统。
            - **信号**: 
                - <font color='red'>**红色/黄色柱**</font>: 多头趋势 (Long State)。
                - <font color='green'>**绿色/蓝色柱**</font>: 空头趋势 (Short State)。
                - **🔺 买入点**: 趋势由空转多，且突破上轨 (UP)。
                - **🔻 卖出点**: 趋势由多转空，跌破下轨 (DOWN)。
            """, unsafe_allow_html=True)
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


# Initialize Loader
@st.cache_resource
def get_loader():
    # Use absolute path relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data/market_data")
    return DataLoader(data_dir=data_dir)
loader = get_loader()
stock_list_df = loader.get_stock_list()

# --- Main Application Logic ---

if app_mode == "个股行情 (Analysis)":
    st.header("📈 个股行情分析/Analysis")
    
    if stock_list_df.empty:
        st.error("数据未就绪，请先下载。")
        st.stop()
        
    # 1. Stock Selection
    # Format: "000001 - 平安银行"
    stock_options = [f"{r['code']} - {r['name']}" for r in stock_list_df.to_dict('records')]
    
    selected_stock = st.selectbox("搜索/选择股票 (Search Stock)", options=stock_options)
    
    if selected_stock:
        code = selected_stock.split(" - ")[0]
        name = selected_stock.split(" - ")[1]
        
        # Controls
        col_ctrl, col_chart = st.columns([1, 3])
        with col_ctrl:
            st.subheader("图表配置")
            
            # Date Range override
            analysis_start = st.date_input("开始日期", default_start, key='ana_start')
            analysis_end = st.date_input("结束日期", default_end, key='ana_end')
            
            st.markdown("**主图层**")
            show_ma = st.checkbox("MA20 均线", value=True)
            show_ema = st.checkbox("EMA200 (牛熊线)", value=True)
            show_ema15 = st.checkbox("EMA15 (HPS通道)", value=False)
            show_cyc = st.checkbox("CYC (成本均线)", value=False)
            show_boll = st.checkbox("布林带", value=True)
            show_box = st.checkbox("Box Top (250日高点)", value=False)
            show_supt = st.checkbox("Support (20日低点)", value=False)

            st.markdown("**副图指标**")
            sub_chart_type = st.radio("选择副图:", ["MACD", "KDJ", "RSI", "WR", "CCI", "Volume", "RKing (趋势)", "Volatility"])
            

        with col_chart:
            # Load Data
            # Need strict load range for proper indicator calc? 
            # Loader basically just loads file, we filter later.
            # But calculating indicators needs history.
            load_start = (analysis_start - datetime.timedelta(days=400)).strftime("%Y-%m-%d")
            load_end = analysis_end.strftime("%Y-%m-%d")
            
            df = loader.get_k_data(code, load_start, load_end)
            
            if not df.empty:
                df = Indicators.add_all_indicators(df)
                # Filter for display
                df_display = df[(df['date'].dt.date >= analysis_start) & (df['date'].dt.date <= analysis_end)]
                
                # Plot
                plot_stock_chart(df_display, code, name, show_ma, show_ema, show_boll, show_cyc, show_ema15, show_box, show_supt, False, sub_chart_type, plotly_template)
                
                # --- Indicator Table (Analysis) ---
                with st.expander("📊 指标数值详情 (Indicator Values)"):
                    # Show last 5 rows of key indicators
                    cols_to_show = ['date', 'close', 'volume', 'MA20', 'MACD_Hist', 'K', 'D', 'J', 'RSI6', 'RKing_State']
                    # Filter existing cols
                    cols_final = [c for c in cols_to_show if c in df_display.columns]
                    st.dataframe(df_display[cols_final].tail(10).sort_values(by='date', ascending=False).style.format({"close": "{:.2f}", "MA20": "{:.2f}"}), use_container_width=True)

                # --- AI Diagnosis ---
                st.markdown("---")
                st.subheader("🤖 AI 智能诊断 (Gemini 3 Pro)")
                
                if st.button("开始诊断 (Start Diagnosis)"):
                    # Try to get API Key from secrets, or use a placeholder/input
                    try:
                        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
                    except (FileNotFoundError, KeyError):
                        st.error("未找到 API Key。请在 .streamlit/secrets.toml 中配置 GEMINI_API_KEY。")
                        st.stop()
                        
                    from stock_diagnosis import StockDiagnoser
                    diagnoser = StockDiagnoser(GEMINI_API_KEY)
                    
                    with st.spinner("正在请求 AI 模型进行深度分析... (可能需要30-60秒)"):
                        sigs = Strategies.check_all(df)
                        report = diagnoser.generate_report(df, code, name, sigs)
                    st.markdown(report)
            else:
                st.warning("暂无数据 (No Data).")
                st.error(f"Debug: Code={code}, LoadStart={load_start}, LoadEnd={load_end}")
                # Check file existence
                file_p = os.path.join("stock_app/data/market_data", f"{code}.csv")
                if os.path.exists(file_p):
                    st.write(f"File exists at {file_p}")
                else:
                    st.write(f"File NOT found at {file_p}")

elif app_mode == "策略选股 (Screening)":
    # --- Strategy Screening Logic ---
    st.header("🔍 策略选股/Screening")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        chart_start = st.date_input("筛选/显示开始日期", default_start, key='scr_start')
    with col_d2:
        chart_end = st.date_input("筛选/显示结束日期", default_end, key='scr_end')
    
    # Session State
    if 'scan_results' not in st.session_state:
        st.session_state['scan_results'] = None

    if st.sidebar.button("开始筛选 / Run Screening"):
        if stock_list_df.empty:
            st.error("无法开始：请先下载数据。")
            st.stop()
            
        st.info(f"正在扫描 {chart_start} 至 {chart_end} 期间符合策略的股票...")
        
        stock_codes = stock_list_df['code'].tolist()
        
        # Prepare Dates
        # Load enough data for indicators (e.g. 400 days before start)
        load_start_str = (chart_start - datetime.timedelta(days=400)).strftime("%Y-%m-%d")
        load_end_str = chart_end.strftime("%Y-%m-%d")
        
        scan_start_str = chart_start.strftime("%Y-%m-%d")
        scan_end_str = chart_end.strftime("%Y-%m-%d")
        
        # Determine Check Config
        # (is_checked, col_str, disp_name)
        checks_config = [
            (strat_fighting, 'Signal_Fighting', "Fighting"),
            (strat_cyc, 'Signal_CYC_MAX', "CYC_MAX"),
            (strat_range, 'Signal_RangeBreak', "RangeBreak"),
            (strat_20vma, 'Signal_20VMA', "20VMA"),
            (strat_hmc, 'Signal_HMC', "HMC"),
            (strat_hps, 'Signal_HPS', "HPS"),
            (strat_tkos, 'Signal_TKOS', "TKOS"),
            (strat_rking, 'Signal_RKing', "RKing"),
            (strat_limit, 'Signal_Limit', "Limit"),
            (strat_boll, 'Signal_Boll_Rev', "Boll_Rev"),
            (strat_rsi, 'Signal_RSI2_Rev', "RSI2_Rev"),
            (strat_2b, 'Signal_2B', "2B"),
            (strat_wyckoff, 'Signal_Wyckoff', "Wyckoff"),
            (strat_spring, 'Signal_Spring', "Spring"),
            (strat_pinbar, 'Signal_Pinbar', "Pinbar"),
            (strat_es, 'Signal_ES', "ES"),
        ]
        
        tasks = []
        for code in stock_codes:
            row = stock_list_df[stock_list_df['code'] == code].iloc[0]
            name = row.get('name', code)
            tasks.append((code, name, load_start_str, load_end_str, scan_start_str, scan_end_str, checks_config))
            
        import multiprocessing
        # Use almost all cores
        cpu_count = max(1, multiprocessing.cpu_count() - 1)
        
        from scanner import scan_single_stock
        
        # Progress Bar Logic
        total = len(tasks)
        processed = 0
        results = []
        
        st.write(f"正在使用 {cpu_count} 个 CPU 核心进行并行筛选...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with multiprocessing.Pool(processes=cpu_count) as pool:
            # unordered yields results as soon as they are ready
            for res in pool.imap_unordered(scan_single_stock, tasks, chunksize=10):
                processed += 1
                if processed % 100 == 0 or processed == total:
                    progress_bar.progress(processed / total)
                    status_text.text(f"Scanning {processed}/{total}...")
                
                if res:
                    results.append(res)
                
        progress_bar.empty()
        status_text.empty()
        
        if results:
            res_df = pd.DataFrame(results)
            # Sort by Signal Date Descending
            if 'Signal Date' in res_df.columns:
                res_df['Signal Date'] = pd.to_datetime(res_df['Signal Date'])
                res_df = res_df.sort_values(by='Signal Date', ascending=False)
                res_df['Signal Date'] = res_df['Signal Date'].dt.strftime('%Y-%m-%d')
                
            st.session_state['scan_results'] = res_df
            st.success(f"筛选完成！发现 {len(results)} 只符合条件的股票 (Date Range Scan)。")
        else:
            st.session_state['scan_results'] = pd.DataFrame()
            st.warning("未找到符合条件的股票。")

    # --- Results Display ---
    if st.session_state['scan_results'] is not None and not st.session_state['scan_results'].empty:
        res_df = st.session_state['scan_results']
        # Convert Code to string to avoid comma format
        res_df['Code'] = res_df['Code'].astype(str)
        
        # Interactive Dataframe
        st.markdown("### 📊 筛选结果 (点击表格行查看详情)")
        event = st.dataframe(
            res_df, 
            use_container_width=True,
            on_select="rerun",  # Rerun app on selection
            selection_mode="single-row" 
        )
        
        st.divider()
        
        # Determine Selected Stock
        # Priority 1: Table Selection
        # Priority 2: Selectbox (Fallback/Legacy)
        
        selected_row_index = None
        if event.selection.rows:
            selected_row_index = event.selection.rows[0]
            
        # Update session state for selection if table clicked? 
        # Actually, let's use the table selection directly if present.
        
        if selected_row_index is not None:
             row_data = res_df.iloc[selected_row_index]
             code_s = str(row_data['Code'])
             name_s = str(row_data['Name'])
             # Optional: Show what is selected
             st.info(f"当前选中: {code_s} - {name_s}")
        else:
             st.info("👆 请在上方表格中点击选择一只股票查看详情。")
             # Fallback to Selectbox if no table selection? 
             # Let's keep selectbox as valid alternative or just hide it? 
             # User asked for "click table", so table is primary.
             # We can keep selectbox consistent. 
             # If table selected, we can't easily force selectbox to update unless we use a key and session state.
             # Simple approach: If table selection exists, use it. Else show selectbox.
             
             if 'Signal Date' in res_df.columns:
                screen_options = [f"{r['Code']} - {r['Name']} (Signal: {r['Signal Date']})" for r in res_df.to_dict('records')]
             else:
                screen_options = [f"{r['Code']} - {r['Name']}" for r in res_df.to_dict('records')]
                
             selected_screen = st.selectbox("或者：从下拉列表选择", options=screen_options, index=None, placeholder="选择股票...")
             
             if selected_screen:
                 code_s = selected_screen.split(" - ")[0]
                 name_s = selected_screen.split(" - ")[1].split(" (")[0]
             else:
                 code_s = None
        
        if code_s:
            # Show Chart
            # We need to load data again for this specific stock
            # Use strict load range?
            load_start_s = (chart_start - datetime.timedelta(days=400)).strftime("%Y-%m-%d")
            load_end_s = chart_end.strftime("%Y-%m-%d")
            
            df_s = loader.get_k_data(code_s, load_start_s, load_end_s)
            
            if not df_s.empty:
                df_s = Indicators.add_all_indicators(df_s)
                # Filter for display
                df_disp_s = df_s[(df_s['date'].dt.date >= chart_start) & (df_s['date'].dt.date <= chart_end)]
                
                # Re-calculate signals for display markers
                # We need to re-run strategies on the loaded df
                sigs_s = Strategies.check_all(df_s)
                
                # Determine combined signal mask for visualization
                # We want to see where the selected strategies triggered
                final_sig = pd.Series(True, index=df_s.index)
                selected_any_cfg = False
                 
                checks_map = {
                    'Signal_Fighting': strat_fighting,
                    'Signal_CYC_MAX': strat_cyc,
                    'Signal_RangeBreak': strat_range,
                    'Signal_20VMA': strat_20vma,
                    'Signal_HMC': strat_hmc,
                    'Signal_HPS': strat_hps,
                    'Signal_TKOS': strat_tkos,
                    'Signal_RKing': strat_rking,
                    'Signal_Limit': strat_limit,
                    'Signal_Boll_Rev': strat_boll,
                    'Signal_RSI2_Rev': strat_rsi,
                    'Signal_2B': strat_2b,
                    'Signal_Wyckoff': strat_wyckoff,
                    'Signal_Spring': strat_spring,
                    'Signal_Pinbar': strat_pinbar,
                    'Signal_ES': strat_es
                }
                
                for col_name, is_chk in checks_map.items():
                    if is_chk:
                        selected_any_cfg = True
                        if col_name in sigs_s.columns:
                            final_sig &= sigs_s[col_name]
                
                signal_dates = None
                if selected_any_cfg:
                    # Filter for display range signals
                    signal_dates = df_s[final_sig & (df_s['date'].dt.date >= chart_start) & (df_s['date'].dt.date <= chart_end)]['date']

                # Controls Layout
                col_c1, col_c2 = st.columns([1, 4])
                with col_c1:
                    st.subheader("图表配置")
                    show_ma = st.checkbox("MA20", value=True, key='sc_ma')
                    show_ema = st.checkbox("EMA200", value=True, key='sc_ema')
                    show_boll = st.checkbox("Boll", value=True, key='sc_boll')
                    show_signals = st.checkbox("标注信号", value=True, key='sc_sig')
                    sub_chart_type = st.radio("副图:", ["MACD", "KDJ", "RSI", "WR", "CCI", "Volume", "RKing (趋势)", "Volatility"], key='sc_sub')
                    
                with col_c2:
                    # Plot
                    plot_stock_chart(df_disp_s, code_s, name_s, show_ma, show_ema, show_boll, False, False, False, False, show_signals, sub_chart_type, plotly_template, sigs_s, signal_dates)
                
                # --- Indicator Table (Screening) ---
                with st.expander("📊 指标数值详情 (Indicator Values)"):
                     cols_to_show = ['date', 'close', 'volume', 'MA20', 'MACD_Hist', 'K', 'D', 'J', 'RSI6', 'RKing_State']
                     cols_final = [c for c in cols_to_show if c in df_disp_s.columns]
                     st.dataframe(df_disp_s[cols_final].tail(10).sort_values(by='date', ascending=False).style.format({"close": "{:.2f}", "MA20": "{:.2f}"}), use_container_width=True)

                # --- AI Diagnosis (Screening) ---
                st.subheader("🤖 AI 智能诊断 (Gemini 3 Pro)")
                if st.button("开始诊断 (Start Diagnosis)", key='diag_scr'):
                     try:
                        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
                     except (FileNotFoundError, KeyError):
                        st.error("未找到 API Key。请在 .streamlit/secrets.toml 中配置 GEMINI_API_KEY。")
                        st.stop()

                     from stock_diagnosis import StockDiagnoser
                     diagnoser = StockDiagnoser(GEMINI_API_KEY)
                     with st.spinner("正在请求 AI 模型进行深度分析..."):
                         report = diagnoser.generate_report(df_s, code_s, name_s, sigs_s)
                     st.markdown(report)

    elif st.session_state['scan_results'] is None:
        st.info("请点击左侧按钮开始筛选。")
