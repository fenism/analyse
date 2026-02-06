
import pandas as pd
import numpy as np

class Strategies:
    @staticmethod
    def check_all(df):
        """
        Apply all strategies to the dataframe.
        Returns a dataframe with boolean columns 'Signal_StrategyName'.
        """
        signals = pd.DataFrame(index=df.index)
        
        # --- Strong Follower ---
        
        # 1. Fighting / DTR Plus
        # MACD Red + New Highs + Trend
        cond_macd = df['DIF'] > df['DEA']
        cond_price = df['close'] >= df['High_52']
        # cond_vol = df['volume'] >= df['Max_Vol_250'] # Strict condition
        # Relaxed version: Price high is enough or Volume high match
        cond_trend = df['close'] > df['MA20']
        signals['Signal_Fighting'] = cond_macd & cond_price & cond_trend
        
        # 2. UA (Ultimate Amount)
        # Breakout of Max Volume Day High
        # Need to find Max Vol Day in window, get its high. 
        # This is path dependent. Simplified: Current Vol is Max? No.
        # We need Rolling Max Vol Day High.
        # Rolling Max Volume
        max_vol = df['volume'].rolling(250).max()
        # If today is max vol? No, breakout of PAST max vol day.
        # This is complex to vectorise perfectly without custom apply.
        # Simplified: Price > High_52 AND Vol > Vol_MA20 * 2?
        # Let's use simplified "Price > High_52" for now as UA proxy or skip.
        # Implementation of proper UA needs locating the bar.
        # We skip UA in this vectorised interaction for speed, or use simple breakout.
        signals['Signal_UA'] = (df['close'] >= df['High_52']) & (df['volume'] > df['Vol_MA20']*1.5)
        
        # 3. CYC MAX / CB
        # Price > CYC_Inf & CYC_13
        signals['Signal_CYC_MAX'] = (df['close'] > df['CYC_Inf']) & (df['close'] > df['CYC_13'])
        
        # 4. Range Breakout
        # Close > High_52
        signals['Signal_RangeBreak'] = df['close'] > df['High_52'].shift(1)
        
        # 6. 20VMA Start
        # Quiet: 4 of last 5 days Vol < MA20.
        # Vectorizing "4 of 5":
        vol_below = (df['volume'] < df['Vol_MA20']).rolling(5).sum() >= 4
        ignition = df['volume'] > df['Vol_MA20']
        signals['Signal_20VMA'] = vol_below.shift(1) & ignition & (df['close'] > df['open'])
        
        # --- Oversold Bottom ---
        
        # 1. Limit (Extreme Shrink)
        # Vol < 0.5 * MA20
        signals['Signal_Limit'] = df['volume'] < (0.5 * df['Vol_MA20'])
        
        # 6. Boll Mean Reversion
        # Weak Zone: Close < Mid for long time (e.g. 60 days). 
        # Check if rolling sum of (Close < Mid) == 60? Too strict.
        # Check if MA60 < Mid?
        # Signal: Cross Mid and touch Upper.
        # Simplified: Close crosses Mid upwards, and High >= Upper.
        cross_mid = (df['close'] > df['Boll_Mid']) & (df['close'].shift(1) <= df['Boll_Mid'].shift(1))
        touch_upper = df['high'] >= df['Boll_Upper']
        signals['Signal_Boll_Rev'] = cross_mid & touch_upper
        
        # 7. RSI2 Reversion
        # Trend: Close > MA250
        # Oversold: RSI2 < 10 for 2 days. 
        # Signal: Today is 3rd day (we mark signal on 2nd day end or 3rd day open?)
        # We mark on 3rd day if RSI condition met previously?
        # Spec: "Enter on 3rd day open". So signal is when prev 2 days < 10.
        rsi_low = (df['RSI2'] < 10) & (df['RSI2'].shift(1) < 10)
        trend = df['close'] > df['MA250'] # Or MA200
        signals['Signal_RSI2_Rev'] = rsi_low.shift(1) & trend
        
        # 8. 2B (False Breakout)
        # Low < Prev_Low_20, Close > Prev_Low_20
        prev_low = df['low'].rolling(20).min().shift(1)
        signals['Signal_2B'] = (df['low'] < prev_low) & (df['close'] > prev_low)
        
        # --- Expanded Strategies ---
        
        # 9. HMC (High Momentum Channel)
        # MACD_Hist > MA5 & MACD_Hist > 0
        signals['Signal_HMC'] = (df['MACD_Hist'] > df['MACD_Hist_MA5']) & (df['MACD_Hist'] > 0)
        
        # 10. HPS (Trend System)
        # Close > EMA200 (Bull Trend) AND Breakout Channel (EMA15 High? Use EMA15 Close for now)
        # Spec says "Breakout EMA15 (High) Channel". Let's assume Close > EMA15 * 1.02? Or just Close > EMA15
        # Simplified: Price > EMA200 AND Price > EMA15 AND Price > MA20
        signals['Signal_HPS'] = (df['close'] > df['EMA200']) & (df['close'] > df['EMA15'])
        
        # 11. TKOS (Monthly Momentum)
        # Ret_20 > 30% (Proxy for month > 50%)
        signals['Signal_TKOS'] = df['Ret_20'] > 0.30
        
        # 12. Wyckoff Accumulation (Simplified)
        # Volume < MA20 for 70% of last 60 days.
        # Rolling count of (Vol < Vol_MA20)
        vol_shrink = (df['volume'] < df['Vol_MA20']).rolling(60).sum()
        is_accumulation = vol_shrink > (60 * 0.7)
        # Breakout: High > Max(High, 20)? Or Close > Max(High, 20)
        breakout_20 = df['close'] > df['high'].rolling(20).max().shift(1)
        signals['Signal_Wyckoff'] = is_accumulation & breakout_20
        
        # 13. Spring
        # Low < Support20 & Close > Support20 & Vol < MA20
        # Support20 is Min(Low, 20) excl today? 
        support_20 = df['low'].rolling(20).min().shift(1)
        signals['Signal_Spring'] = (df['low'] < support_20) & (df['close'] > support_20) & (df['volume'] < df['Vol_MA20'])

        # 14. Pinbar
        # Lower Shadow > 3 * Body AND Lower Shadow > 0.6 * Range
        cond_pin = (df['Lower_Shadow'] > 3 * df['Body']) & (df['Lower_Shadow'] > 0.6 * df['Range'])
        signals['Signal_Pinbar'] = cond_pin
        
        # 15. ES (Volatility Compression)
        # Std20 < Std60 and Std20 < Std120
        signals['Signal_ES'] = (df['Std20'] < df['Std60']) & (df['Std20'] < df['Std120']) & (df['Ret_20'].abs() < 0.1) # Low movement
        
        return signals

