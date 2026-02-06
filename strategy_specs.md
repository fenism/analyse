# 策略逻辑规格说明书 (Strategy Specifications)

基于 `strategy.md` 和 NotebookLM 的回复整理。

## 通用参数
- **N_L**: 长期周期，默认为 52 (周) 或 250 (日)
- **N_S**: 短期周期，默认为 20
- **MA_Vol**: 成交量均线周期，通常为 20

## 一、 强势跟随类 (Strong Follower)

### 1. Fighting / DTR Plus (三合一趋势共振)
- **逻辑**: 趋势+量能+指标共振。
- **公式**:
    1.  `MACD_Red`: `DIF > DEA` (即 MACD翻红/金叉状态)。
    2.  `Price_NewHigh`: `Close >= Max(High, 52)`.
    3.  `Vol_NewHigh`: `Volume >= Max(Volume, 52)`.
    4.  `Boll_Confirm`: `Close > Boll_Upper` (N=20, k=2).
    5.  `Trend_Confirm`: `Close > MA(Close, 20)`.
- **信号**: 满足上述所有条件。

### 2. UA 天量突破 (Ultimate Amount)
- **逻辑**: 突破历史天量高点。
- **公式**:
    1.  `Max_Vol_Day`: 过去 250 天中成交量最大的一天 (High_Vol_Bar)。
    2.  `Breakout`: `Close > High_ref` (High_ref 为 Max_Vol_Day 的最高价)。
    3.  `Filter`: `Close > MA(Close, 20)`.

### 3. CYC MAX / CB 双突
- **逻辑**: 站上无穷成本均线，全获利状态。
- **公式**:
    1.  `CYC_Inf`: 模拟无穷成本均线 (使用 `amount / volume` 的加权移动平均，alpha=1/0, 但实际用 EMA 近似，周期设为 0 或极长如 500)。
        - *近似算法*: `EMA(Amount/Volume, 0)` -> `CumSum(Amount) / CumSum(Volume)` (上市以来均价)。
    2.  `CYC_Short`: `EMA(Amount/Volume, 13)`.
    3.  `Signal`: `Close > CYC_Inf` AND `Close > CYC_Short`.

### 4. Range Breakout (达瓦斯/箱体)
- **公式**:
    1.  `N`: 52.
    2.  `Box_Top`: `Max(High, N)`.
    3.  `Breakout`: `Close > Box_Top`.
    4.  `Volume_Confirm`: `Volume > MA(Volume, 20)`.

### 5. OBO (Open Breakout)
- **公式**:
    1.  `Range`: `High_prev - Low_prev`.
    2.  `Target`: `Open + Range`.
    3.  `Signal`: `Close > Target` AND `Close > MA(Close, 250)`.

### 6. 20VMA 启动
- **公式**:
    1.  `Quiet`: 过去 5 天中至少 4 天 `Volume < MA(Volume, 20)`.
    2.  `Ignition`: 今日 `Volume > MA(Volume, 20)`.
    3.  `Trend`: `Close > Open` AND `Close > Close_prev`.

### 7. LCS 极限策略 (Limit Close Super)
- **公式**:
    1.  `Low_5`: `Min(Low, 5)`.
    2.  `Deviation`: `(Close - Low_5) / Low_5`.
    3.  `Signal`: `Deviation > 0.3` (30% 偏离, A股可能需调低至 20% 或累积涨幅) AND `Close == Max(Close, 250)`.

### 8. Rank 评分
- **公式**: `Z-Score(Returns_20)`.
    - `Score = (Ret_20 - Mean_Ret_Market) / Std_Ret_Market`.
    - `Signal`: `Score > 1.5`.

---

### 9. RS 相对强弱策略 (Relative Strength)
- **逻辑**: 个股/大盘指数 的比值曲线。
- **公式**:
    1.  `RS_Ratio`: `Close_Stock / Close_Index` (需加载沪深300指数数据).
    2.  `Signal`: `RS_Ratio > MA(RS_Ratio, 20)` AND `RS_Ratio` 创 50日新高.

### 10. HMC / MTA (动量通道)
- **逻辑**: 动量强劲。
- **公式** (参考 MTA):
    1.  `MACD_Bar`: `2 * (DIF - DEA)`.
    2.  `Signal`: `MACD_Bar > MA(MACD_Bar, 5)` (柱状图乖离) AND `MACD_Bar > 0`.

### 11. HPS 趋势系统
- **公式**:
    1.  `Trend`: `Close > EMA(Close, 200)`.
    2.  `Channel`: `EMA(High, 15)`.
    3.  `Breakout`: `Close > Channel`.

### 12. TKOS 股王 (月线动量)
- **公式**:
    1.  `Month_Ret`: 上月涨幅 > 50%. (由于数据获取限制，可用 20日涨幅 > 30%近似).

---

## 二、 超跌底部类 (Oversold Bottom)

### 1. Limit 极致缩量
- **公式**:
    1.  `Vol_Ratio`: `Volume / MA(Volume, 20)`.
    2.  `Signal`: `Vol_Ratio < 0.5`.

### 2. Wyckoff 吸筹 & Effort vs Result
- **公式**:
    1.  `Accumulation`: 过去60天中 `Volume < MA(Volume, 20)` 天数 > 70%.
    2.  `Effort`: 今日 `Volume > MA(Volume, 20) * 1.5`.
    3.  `Result_Fail`: `(High - Low) < Avg(High-Low, 14) * 0.8`. (努力无结果，顶部信号；底部反转看 Spring).

### 3. 量比历史新低
- **公式**:
    1.  `Vol_Ratio`: `Volume / MA(Volume, 5)`.
    2.  `Signal`: `Vol_Ratio == Min(Vol_Ratio, 120)`.

### 4. HLP3 / Zero-Profit (获利盘策略)
- **筹码分布估算 (Chip Distribution)**:
    - 假设每日成交量在 High-Low 之间均匀分布 (或正态分布)。
    - 随着时间推移，旧筹码按换手率衰减。
    - `Winner_Ratio`: 当前收盘价下方的筹码比例。
- **HLP3 信号**:
    - `Winner_Prev < 1%` AND `Winner_Curr > 35%`.
- **Zero-Profit 信号**:
    - `Winner < 1%`.

### 5. Spring 弹簧效应
- **公式**:
    1.  `Support`: `Min(Low, 20)` (前20天低点).
    2.  `Break`: `Low < Support` (当天曾经跌破).
    3.  `Reclaim`: `Close > Support` (收盘收回).
    4.  `Volume`: `Volume < MA(Volume, 20)` (缩量更好).

### 6. 布林长中下
- **公式**:
    1.  `Weak_Zone`: 过去 60 天 `Close < Boll_Mid`.
    2.  `Signal`: `Close > Boll_Mid` AND `High >= Boll_Upper` (触碰上轨).

### 7. RSI(2) 均值回归
- **公式**:
    1.  `Trend`: `Close > MA(Close, 250)`.
    2.  `Oversold`: `RSI(2) < 10` (A股调整阈值, 原文25可能太高) 连续 2 天.
    3.  `Enter`: 第 3 天开盘. (回测中可用 `Open` 买入).

### 8. 2B 法则
- **公式**:
    1.  `Prev_Low`: `Min(Low, 20)` (不含今日).
    2.  `Signal`: `Low < Prev_Low` AND `Close > Prev_Low`.

### 9. Pinbar 探底神针
- **公式**:
    1.  `Body`: `Abs(Open - Close)`.
    2.  `Lower_Shadow`: `Min(Open, Close) - Low`.
    3.  `Signal`: `Lower_Shadow > 3 * Body` AND `Lower_Shadow > (High - Low) * 0.6` (长下影占比).

### 10. ES 波动率压缩
- **公式**:
    1.  `Std_20`: `Std(Close, 20)`.
    2.  `Std_Long`: `Min(Std(Close, 60), Std(Close, 120))`.
    3.  `Signal`: `Std_20 < Std_Long` (且处于低位).
