"""
Royal 股票抄底实战策略模块
实现 weak.md 中定义的8种抄底策略

核心心法：行情始于"无"（极致缩量/绝望），终于"有"（放量/贪婪）
抄底不是买在最低点，而是买在"绝望后的确认转折点"
"""

import pandas as pd
import numpy as np


class WeakStrategies:
    """弱势股抄底策略集合"""
    
    @staticmethod
    def _calculate_rsi(series, period):
        """辅助函数：计算RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    # ========== 第一阶段：扫描与初筛（寻找"绝望"与"无"） ==========
    
    @staticmethod
    def strategy_hlp3(df, winner_col='winner_pct'):
        """
        HLP3 (大慈悲点) - 筹码绝望筛查
        
        核心逻辑：昨日获利盘 < 1% (全场99%都在亏损，多头死绝)
                 今日获利盘 > 35% (主力进场扫货)
        
        :param df: 包含OHLCV和获利盘比例的DataFrame
        :param winner_col: 获利盘比例列名，默认'winner_pct' (0-100)
        :return: 包含HLP3信号的DataFrame
        """
        df = df.copy()
        
        # 检查是否有获利盘数据
        if winner_col not in df.columns:
            # 如果没有数据，返回全False信号
            df['HLP3_Signal'] = False
            df['HLP3_Warning'] = True  # 标记数据缺失
            return df
        
        # 昨日获利盘 < 1
        cond_despair = df[winner_col].shift(1) < 1
        
        # 今日获利盘 > 35
        cond_surge = df[winner_col] > 35
        
        # 综合信号
        df['HLP3_Signal'] = cond_despair & cond_surge
        df['HLP3_Warning'] = False
        
        return df
    
    @staticmethod
    def strategy_limit(df):
        """
        Limit (极致缩量) - 量能静默筛查
        
        核心逻辑：成交量 < 20日均量 * 0.5 (市场极度死寂，变盘前夜)
        买入扳机：缩量后放量突破20日均量线 + 收阳
        
        :param df: 包含OHLCV的DataFrame
        :return: 包含Limit信号的DataFrame
        """
        df = df.copy()
        
        # 计算20日均量
        vma20 = df['volume'].rolling(window=20).mean()
        
        # 极致缩量：量 < 均量的一半
        df['Limit_Signal'] = df['volume'] < (vma20 * 0.5)
        
        # 进阶：Limit后放量突破 (Limit Breakout)
        # 过去5天内出现过Limit + 今日放量突破20日线 + 收阳
        limit_setup = df['Limit_Signal'].rolling(window=5).max() > 0
        vol_breakout = df['volume'] > vma20
        bull_candle = df['close'] > df['open']
        
        df['Limit_BO_Signal'] = limit_setup & vol_breakout & bull_candle
        
        return df
    
    @staticmethod
    def strategy_rsi_reversion(df):
        """
        RSI均值回归 - 技术极度超卖
        
        核心逻辑：价格 > EMA200 (牛市趋势) 
                 AND RSI(2) 连续2天 < 25 (短期非理性恐慌抛售)
        买入时机：第3天开盘博弈反弹
        
        :param df: 包含OHLCV的DataFrame
        :return: 包含RSI回归信号的DataFrame
        """
        df = df.copy()
        
        # 计算 EMA200
        ema200 = df['close'].ewm(span=200, adjust=False).mean()
        
        # 计算 RSI(2)
        rsi2 = WeakStrategies._calculate_rsi(df['close'], 2)
        
        # 条件1: 趋势向上 (在牛市中抄底)
        cond_trend = df['close'] > ema200
        
        # 条件2: RSI2 连续2天小于25
        cond_oversold = (rsi2.shift(1) < 25) & (rsi2 < 25)
        
        # 综合信号 (在第3天触发)
        df['RSI_Rev_Signal'] = cond_trend & cond_oversold
        
        return df
    
    # ========== 第二阶段：形态确认（寻找"诱空"与"试探"） ==========
    
    @staticmethod
    def strategy_spring(df):
        """
        Spring (弹簧) - 诱空形态
        
        核心逻辑：跌破支撑位(20日低点) + 1-3天内迅速拉回支撑上方 + 缩量下杀
        含义：主力清洗最后浮筹，测试供应
        
        :param df: 包含OHLCV的DataFrame
        :return: 包含Spring信号的DataFrame
        """
        df = df.copy()
        
        # 定义支撑：过去20天的最低点（不含今日）
        support = df['low'].rolling(window=20).min().shift(1)
        
        # 1. 最低价跌破支撑
        break_support = df['low'] < support
        
        # 2. 收盘价收回支撑上方 (Spring回抽)
        recover = df['close'] > support
        
        # 3. 缩量特征 (可选，增强信号质量)
        vma20 = df['volume'].rolling(window=20).mean()
        low_volume = df['volume'] < vma20
        
        # Spring信号：击穿且拉回
        df['Spring_Signal'] = break_support & recover & low_volume
        
        return df
    
    @staticmethod
    def strategy_pinbar(df):
        """
        Pinbar (长钉 / 单针探底) - 多头长钉
        
        核心逻辑：下影线长度 > 实体 * 3 + 放量
        含义：恐慌盘涌出被主力全盘接下（多头探底神针）
        
        :param df: 包含OHLCV的DataFrame
        :return: 包含Pinbar信号的DataFrame
        """
        df = df.copy()
        
        # 计算K线各部分
        body = abs(df['close'] - df['open'])
        lower_shadow = df[['close', 'open']].min(axis=1) - df['low']
        
        # 成交量放大 (大于20日均量)
        vma20 = df['volume'].rolling(window=20).mean()
        vol_up = df['volume'] > vma20
        
        # 下影线 > 实体 * 3
        pin_shape = lower_shadow > (body * 3)
        
        # 多头长钉信号
        df['Pinbar_Signal'] = pin_shape & vol_up
        
        return df
    
    @staticmethod
    def strategy_money_flow(df):
        """
        Money Flow Divergence (资金背离)
        
        核心逻辑：股价横盘或创新低，但资金流入流出监测器显示净流入
        含义：主力在底部悄悄吸筹
        
        计算公式（来自文档）：
        D = C - REF(C,1)  # 涨跌额
        D1 = D / REF(C,1)  # 涨幅比例
        DT = (V * D1) * 100  # 上涨动能
        KT = (V * K1) * 100  # 下跌动能
        净流入 = SUM(DT - KT, 10)  # 10日累计
        
        :param df: 包含OHLCV的DataFrame
        :return: 包含资金背离信号的DataFrame
        """
        df = df.copy()
        
        # 昨日收盘
        ref_c = df['close'].shift(1)
        
        # 涨跌额
        diff = df['close'] - ref_c
        
        # 上涨部分
        d_part = np.where(diff > 0, diff, 0)
        d1 = d_part / ref_c.replace(0, np.nan)
        dt = (df['volume'] * d1) * 100
        
        # 下跌部分 (取绝对值)
        k_part = np.where(diff < 0, abs(diff), 0)
        k1 = k_part / ref_c.replace(0, np.nan)
        kt = (df['volume'] * k1) * 100
        
        # 10日累计净流入
        net_flow = pd.Series(dt - kt).rolling(window=10).sum()
        df['Money_Flow'] = net_flow
        
        # 背离逻辑：股价创20日新低 + 资金流为正
        price_low = df['close'] == df['close'].rolling(20).min()
        flow_positive = df['Money_Flow'] > 0
        
        df['Money_Flow_Signal'] = price_low & flow_positive
        
        return df
    
    # ========== 第三阶段：买入扳机（确认"有"与"启动"） ==========
    
    @staticmethod
    def strategy_ua(df, period=250):
        """
        UA (Ultimate Amount 天量) - 底部天量突破
        
        核心逻辑：底部出现历史级天量，标记最高价
        买入时机：后续价格有效突破天量日最高价（确认多头获胜）
        
        :param df: 包含OHLCV的DataFrame
        :param period: 天量检测周期，默认250日
        :return: 包含UA信号的DataFrame
        """
        df = df.copy()
        
        # 识别天量（250日内最大成交量）
        df['UA_Is_Max'] = df['volume'] == df['volume'].rolling(period).max()
        
        # 记录天量当日的最高价 (作为突破目标位)
        df['UA_Target_High'] = np.where(df['UA_Is_Max'], df['high'], np.nan)
        df['UA_Target_High'] = df['UA_Target_High'].ffill()  # 向下填充
        
        # UA突破买点：收盘价站上最近一次UA的最高价 (且当日不是UA日)
        df['UA_Breakout_Signal'] = (df['close'] > df['UA_Target_High']) & (~df['UA_Is_Max'])
        
        return df
    
    @staticmethod
    def strategy_double_volume_hold(df):
        """
        倍量不破 (Double Volume Hold)
        
        核心逻辑：今日量 > 昨日量 * 2 (倍量阳线)
        买入时机：回调不破该阳线最低价，再次启动时买入
        
        :param df: 包含OHLCV的DataFrame
        :return: 包含倍量不破信号的DataFrame
        """
        df = df.copy()
        
        # 1. 识别倍量柱
        double_vol = df['volume'] > (df['volume'].shift(1) * 2)
        
        # 2. 标记倍量柱的最低价
        df['Double_Vol_Low'] = np.where(double_vol, df['low'], np.nan)
        df['Double_Vol_Low'] = df['Double_Vol_Low'].ffill()  # 填充最近的倍量低点
        
        # 3. 检查是否守住 (当前收盘价 > 倍量低点)
        df['Is_Holding'] = df['close'] > df['Double_Vol_Low']
        
        # 4. 信号：倍量后守住低点 + 再次放量
        vma20 = df['volume'].rolling(window=20).mean()
        vol_up = df['volume'] > vma20
        
        df['Double_Vol_Signal'] = df['Is_Holding'] & vol_up & (df['close'] > df['open'])
        
        return df
    
    @staticmethod
    def check_all_weak_strategies(df, selected_strategies=None, winner_col='winner_pct'):
        """
        检查所有抄底策略
        
        :param df: 个股数据 DataFrame
        :param selected_strategies: 选中的策略列表
        :param winner_col: 获利盘列名（用于HLP3）
        :return: 包含所有策略信号的 DataFrame
        """
        if selected_strategies is None:
            selected_strategies = ['HLP3', 'Limit', 'RSI_Rev', 'Spring', 
                                  'Pinbar', 'Money_Flow', 'UA', 'Double_Vol']
        
        signals = pd.DataFrame(index=df.index)
        
        # 第一阶段：扫描与初筛
        if 'HLP3' in selected_strategies:
            hlp3_result = WeakStrategies.strategy_hlp3(df, winner_col)
            signals['Signal_HLP3'] = hlp3_result['HLP3_Signal']
            signals['HLP3_Warning'] = hlp3_result['HLP3_Warning']
        
        if 'Limit' in selected_strategies:
            limit_result = WeakStrategies.strategy_limit(df)
            # 使用Limit突破信号作为主信号
            signals['Signal_Limit'] = limit_result['Limit_BO_Signal']
        
        if 'RSI_Rev' in selected_strategies:
            rsi_result = WeakStrategies.strategy_rsi_reversion(df)
            signals['Signal_RSI_Rev'] = rsi_result['RSI_Rev_Signal']
        
        # 第二阶段：形态确认
        if 'Spring' in selected_strategies:
            spring_result = WeakStrategies.strategy_spring(df)
            signals['Signal_Spring'] = spring_result['Spring_Signal']
        
        if 'Pinbar' in selected_strategies:
            pinbar_result = WeakStrategies.strategy_pinbar(df)
            signals['Signal_Pinbar'] = pinbar_result['Pinbar_Signal']
        
        if 'Money_Flow' in selected_strategies:
            flow_result = WeakStrategies.strategy_money_flow(df)
            signals['Signal_Money_Flow'] = flow_result['Money_Flow_Signal']
        
        # 第三阶段：买入扳机
        if 'UA' in selected_strategies:
            ua_result = WeakStrategies.strategy_ua(df)
            signals['Signal_UA'] = ua_result['UA_Breakout_Signal']
        
        if 'Double_Vol' in selected_strategies:
            dv_result = WeakStrategies.strategy_double_volume_hold(df)
            signals['Signal_Double_Vol'] = dv_result['Double_Vol_Signal']
        
        return signals
