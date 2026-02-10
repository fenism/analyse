"""
Royal 强势股进攻策略模块
实现 strong.md 中定义的7种强势股筛选策略
"""

import pandas as pd
import numpy as np


class StrongStrategies:
    """强势股进攻策略集合"""
    
    @staticmethod
    def calculate_z_score(df, period=20):
        """
        计算 Z-score 指标
        
        核心逻辑：(收盘价 - 20日均价) / 20日标准差
        强势标准：Z > 1.5
        过热预警：Z > 3
        
        :param df: 包含 'close' 的 DataFrame
        :param period: 周期，默认为20
        :return: 包含 Z-score 及其信号的 DataFrame
        """
        df = df.copy()
        
        # 计算均值和标准差
        df['MA20'] = df['close'].rolling(window=period).mean()
        df['STD20'] = df['close'].rolling(window=period).std()
        
        # 计算 Z-score (防止除以0)
        df['Z_Score'] = (df['close'] - df['MA20']) / df['STD20'].replace(0, np.nan)
        
        # 生成信号
        # 强势信号：1.5 < Z <= 3
        df['Z_Signal'] = np.where((df['Z_Score'] > 1.5) & (df['Z_Score'] <= 3), True, False)
        
        # 过热预警：Z > 3
        df['Z_Overheat'] = np.where(df['Z_Score'] > 3, True, False)
        
        return df
    
    @staticmethod
    def calculate_rs_strategy(stock_df, index_df, period=20, num_std=2):
        """
        计算 RS 相对强弱策略
        
        核心逻辑：(个股收盘 / 大盘收盘) * 1000，并叠加布林带（N=20, Std=2）
        信号：RS 突破 RS布林上轨
        
        :param stock_df: 个股 DataFrame (需包含 'date', 'close')
        :param index_df: 大盘指数 DataFrame (需包含 'date', 'close')
        :param period: 布林带周期，默认20
        :param num_std: 布林带标准差倍数，默认2
        :return: 包含 RS 及其布林带信号的 DataFrame
        """
        stock_df = stock_df.copy()
        
        # 确保两个df都有date列
        if 'date' not in stock_df.columns or 'date' not in index_df.columns:
            # 如果没有date列，返回空信号
            stock_df['RS_Breakout'] = False
            return stock_df
        
        # 按日期合并股票和大盘数据
        merged = pd.merge(
            stock_df[['date', 'close']],
            index_df[['date', 'close']],
            on='date',
            how='left',
            suffixes=('_stock', '_index')
        )
        
        # 前向填充大盘数据（处理缺失日期）
        merged['close_index'] = merged['close_index'].fillna(method='ffill')
        
        # 1. 计算 RS 值 (乘以1000方便显示)
        merged['RS'] = (merged['close_stock'] / merged['close_index']) * 1000
        
        # 2. 计算 RS 的布林带
        merged['RS_MA'] = merged['RS'].rolling(window=period).mean()
        merged['RS_STD'] = merged['RS'].rolling(window=period).std()
        merged['RS_Upper'] = merged['RS_MA'] + (merged['RS_STD'] * num_std)
        merged['RS_Lower'] = merged['RS_MA'] - (merged['RS_STD'] * num_std)
        
        # 3. 信号：RS 突破 RS布林上轨
        # 当日RS > 上轨 且 前一日RS <= 前一日上轨（避免未来函数）
        merged['RS_Breakout'] = (merged['RS'] > merged['RS_Upper']) & \
                                (merged['RS'].shift(1) <= merged['RS_Upper'].shift(1))
        
        # 将结果合并回原始df
        stock_df['RS_Breakout'] = merged['RS_Breakout'].values
        
        return stock_df
    
    @staticmethod
    def calculate_tkos(df):
        """
        计算 TKOS 股王策略
        
        核心逻辑：检测某个月的前5个交易日(近似第一周)累计涨幅是否超过50%
        信号：月涨幅 > 50%
        
        :param df: 包含 'close' 的 DataFrame
        :return: 包含 TKOS 信号的 DataFrame
        """
        df = df.copy()
        
        # 计算5日累计涨幅 (近似一周)
        # (当前收盘 - 5天前收盘) / 5天前收盘
        df['Week_Pct_Change'] = df['close'].pct_change(periods=5)
        
        # 信号：涨幅 > 50%
        df['TKOS_Signal'] = df['Week_Pct_Change'] > 0.50
        
        return df
    
    @staticmethod
    def calculate_dtr_plus(df, ma_period=20, boll_std=2):
        """
        计算 DTR Plus 策略（高胜率共振）
        
        核心逻辑：MACD翻红 + 价格 > MA20 + 价格 >= 布林上轨
        三合一共振信号
        
        :param df: 包含 OHLC 和 volume 的 DataFrame
        :param ma_period: MA周期，默认20
        :param boll_std: 布林带标准差倍数，默认2
        :return: 包含 DTR Plus 信号的 DataFrame
        """
        df = df.copy()
        
        # 1. 计算 MACD (12, 26, 9)
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        diff = ema12 - ema26
        dea = diff.ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = 2 * (diff - dea)
        
        # DTR翻红信号 (当前红柱，昨日绿柱)
        df['DTR_Red'] = (df['MACD_Hist'] > 0) & (df['MACD_Hist'].shift(1) <= 0)
        
        # 2. 计算 MA20
        df['MA20'] = df['close'].rolling(window=ma_period).mean()
        
        # 3. 计算布林上轨
        std20 = df['close'].rolling(window=ma_period).std()
        df['Boll_Upper'] = df['MA20'] + (std20 * boll_std)
        
        # 4. 综合信号 (三合一)
        # MACD是红柱状态，价格在MA20之上，价格触碰或突破上轨
        condition1 = df['MACD_Hist'] > 0
        condition2 = df['close'] > df['MA20']
        condition3 = df['close'] >= df['Boll_Upper']
        
        df['DTR_Plus_Signal'] = condition1 & condition2 & condition3
        
        return df
    
    @staticmethod
    def calculate_fighting_strategy(df, period=52):
        """
        计算 Fighting 策略 (三合一突破)
        
        核心逻辑：DTR翻红 + 突破52日价格新高 + 突破52日成交量新高
        
        :param df: 包含 OHLC 和 volume 的 DataFrame
        :param period: 新高周期，默认52日
        :return: 包含 Fighting 信号的 DataFrame
        """
        df = df.copy()
        
        # 1. MACD DTR
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        diff = ema12 - ema26
        dea = diff.ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = 2 * (diff - dea)
        
        # DTR 红柱状态
        is_dtr_red = df['MACD_Hist'] > 0
        
        # 2. 52日价格新高 (突破前52天的最高价)
        highest_price_52 = df['high'].rolling(window=period).max().shift(1)
        price_breakout = df['close'] > highest_price_52
        
        # 3. 52日成交量新高
        highest_vol_52 = df['volume'].rolling(window=period).max().shift(1)
        vol_breakout = df['volume'] > highest_vol_52
        
        # 4. Fighting 信号
        df['Fighting_Signal'] = is_dtr_red & price_breakout & vol_breakout
        
        return df
    
    @staticmethod
    def calculate_ua_strategy(df, period=250):
        """
        计算 UA 天量策略 (Ultimate Amount)
        
        核心逻辑：出现历史(或250日)天量，标记该日最高价。
        后续突破该最高价为买点。
        
        :param df: 包含 OHLC 和 volume 的 DataFrame
        :param period: 天量检测周期，默认250日
        :return: 包含 UA 信号的 DataFrame
        """
        df = df.copy()
        
        # 1. 定义天量 (250日内最大成交量)
        df['Rolling_Max_Vol'] = df['volume'].rolling(window=period).max()
        df['Is_UA'] = df['volume'] == df['Rolling_Max_Vol']
        
        # 2. 记录天量日的最高价 (UA_High)
        # 如果是UA日，记录High，否则NaN，然后向下填充
        df['UA_Target_Price'] = np.where(df['Is_UA'], df['high'], np.nan)
        df['UA_Target_Price'] = df['UA_Target_Price'].ffill()
        
        # 3. 突破信号
        # 当前收盘价突破最近一次天量的最高价
        # 且当前不是天量当日 (避免当日追高)
        df['UA_Breakout'] = (df['close'] > df['UA_Target_Price']) & (df['Is_UA'] == False)
        
        # 过滤连续信号：只看刚突破的那一天
        df['UA_Buy_Signal'] = df['UA_Breakout'] & (df['UA_Breakout'].shift(1) == False)
        
        return df
    
    @staticmethod
    def calculate_hmc_strategy(df):
        """
        计算 HMC 策略 (High-Momentum Channel)
        
        核心逻辑：
        - 黄线 = 50日最高价 - 收盘价 (越小越好，代表接近新高)
        - 红线 = 收盘价 - EMA200 (越大越好，代表强势)
        - 信号 = 红线上穿黄线 (动能强劲)
        
        :param df: 包含 OHLC 的 DataFrame
        :return: 包含 HMC 信号的 DataFrame
        """
        df = df.copy()
        
        # 1. 黄线: 50日最高价 - 收盘价
        hhv_50 = df['high'].rolling(window=50).max()
        df['HMC_Yellow'] = hhv_50 - df['close']
        
        # 2. 红线: 收盘价 - EMA200
        ema_200 = df['close'].ewm(span=200, adjust=False).mean()
        df['HMC_Red'] = df['close'] - ema_200
        
        # 3. 信号: 红线上穿黄线
        # 今天红 > 黄 且 昨天 红 <= 黄
        df['HMC_Signal'] = (df['HMC_Red'] > df['HMC_Yellow']) & \
                           (df['HMC_Red'].shift(1) <= df['HMC_Yellow'].shift(1))
        
        return df
    
    @staticmethod
    def check_all_strong_strategies(df, index_df=None, selected_strategies=None):
        """
        检查所有强势股策略
        
        :param df: 个股数据 DataFrame
        :param index_df: 大盘指数数据 DataFrame (用于RS策略)
        :param selected_strategies: 选中的策略列表，如 ['Z_Score', 'RS', 'Fighting']
        :return: 包含所有策略信号的 DataFrame
        """
        if selected_strategies is None:
            selected_strategies = ['Z_Score', 'RS', 'TKOS', 'DTR_Plus', 'Fighting', 'UA', 'HMC']
        
        signals = pd.DataFrame(index=df.index)
        
        # Z-score
        if 'Z_Score' in selected_strategies:
            z_result = StrongStrategies.calculate_z_score(df)
            signals['Signal_Z_Score'] = z_result['Z_Signal']
        
        # RS (需要大盘数据)
        if 'RS' in selected_strategies and index_df is not None:
            rs_result = StrongStrategies.calculate_rs_strategy(df, index_df)
            signals['Signal_RS'] = rs_result['RS_Breakout']
        
        # TKOS
        if 'TKOS' in selected_strategies:
            tkos_result = StrongStrategies.calculate_tkos(df)
            signals['Signal_TKOS'] = tkos_result['TKOS_Signal']
        
        # DTR Plus
        if 'DTR_Plus' in selected_strategies:
            dtr_result = StrongStrategies.calculate_dtr_plus(df)
            signals['Signal_DTR_Plus'] = dtr_result['DTR_Plus_Signal']
        
        # Fighting
        if 'Fighting' in selected_strategies:
            fighting_result = StrongStrategies.calculate_fighting_strategy(df)
            signals['Signal_Fighting'] = fighting_result['Fighting_Signal']
        
        # UA
        if 'UA' in selected_strategies:
            ua_result = StrongStrategies.calculate_ua_strategy(df)
            signals['Signal_UA'] = ua_result['UA_Buy_Signal']
        
        # HMC
        if 'HMC' in selected_strategies:
            hmc_result = StrongStrategies.calculate_hmc_strategy(df)
            signals['Signal_HMC'] = hmc_result['HMC_Signal']
        
        return signals
