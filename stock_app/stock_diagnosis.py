
import requests
import json
import pandas as pd
import datetime

class StockDiagnoser:
    def __init__(self, api_key):
        self.api_key = api_key
        # Gemini 3 Pro endpoint (Preview)
        # Fallback list: gemini-3-pro-preview, gemini-2.5-pro, gemini-1.5-pro-latest
        self.model = "gemini-3-pro-preview" 
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
    def generate_report(self, df, code, name, strategy_signals):
        """
        Generate a comprehensive analysis report using Gemini.
        """
        if df.empty:
            return "数据为空，无法分析。"
            
        # 1. Prepare Data Summary
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else last_row
        
        # Trend
        ma20_trend = "Up" if last_row['MA20'] > prev_row['MA20'] else "Down"
        price_trend = "Bullish" if last_row['close'] > last_row['MA20'] else "Bearish"
        
        # Recent 5 days
        recent_data = df.tail(5)[['date', 'open', 'high', 'low', 'close', 'volume', 'MA20']].to_string()
        
        # Strategy Signals Summary
        active_strategies = []
        if strategy_signals is not None and not strategy_signals.empty:
            # Check last row signals
            last_sig = strategy_signals.iloc[-1]
            for col in last_sig.index:
                if last_sig[col]:
                    active_strategies.append(col)
        
        strategies_text = ", ".join(active_strategies) if active_strategies else "None"
        
        # Detailed Indicators
        indicators_info = f"""
        - MACD: DIF={last_row.get('DIF',0):.3f}, DEA={last_row.get('DEA',0):.3f}, Hist={last_row.get('MACD_Hist',0):.3f}
        - KDJ: K={last_row.get('K',0):.1f}, D={last_row.get('D',0):.1f}, J={last_row.get('J',0):.1f}
        - RSI: RSI6={last_row.get('RSI6',0):.1f}
        - WR: {last_row.get('WR',0):.1f}
        - CCI: {last_row.get('CCI',0):.1f}
        - Volume: Current={last_row['volume']:.0f}, MA20={last_row.get('Vol_MA20',0):.0f}
        - Position: Close={last_row['close']}, MA20={last_row['MA20']:.2f}, EMA200={last_row.get('EMA200',0):.2f}
        - RKing State: {last_row.get('RKing_State', 0)} (1=Long, -1=Short)
        """

        # 2. Construct Prompt
        prompt_text = f"""
        你是一个专业的A股量化交易分析师。请根据以下提供的股票数据，对 [{code}] {name} 进行一份详细的 **个股诊断报告**。
        
        ### 1. 基础数据
        - **代码**: {code} - {name}
        - **最新日期**: {last_row['date']}
        - **现价**: {last_row['close']} (涨跌幅: {(last_row['close']/prev_row['close']-1)*100:.2f}%)
        - **趋势状态**: MA20 {ma20_trend}, Price vs MA20: {price_trend}
        
        ### 2. 近期行情 (最后5日)
        {recent_data}
        
        ### 3. 技术指标详情
        {indicators_info}
        
        ### 4. 量化策略信号触发 (今日)
        - **触发策略**: {strategies_text}
        
        ### 分析要求
        请基于以上数据，从以下几个维度进行深度分析 (使用Markdown格式):
        1.  **趋势研判**: 判断当前是处于上涨、下跌还是震荡阶段？均线系统和趋势指标 (RKing, EMA200) 指向什么方向？
        2.  **资金面分析**: 通过成交量和量价关系 (Volume, OBV等概念)，判断资金是在流入还是流出？是否有背离？
        3.  **技术面信号**: 解读 KDJ, MACD, RSI, WR, CCI 等指标的状态（超买/超卖/背离/金叉死叉）。
        4.  **策略验证**: 结合触发的量化策略 (如 {strategies_text})，评估其有效性和当前信号的可靠性。如果不涉及策略，请说明当前形态。
        5.  **综合操作建议**: 
            -   **评分**: 0-100分
            -   **建议**: 买入 / 增持 / 持有 / 减仓 / 卖出 / 观望
            -   **止损位/支撑位**: 给出具体的参考价格。
            -   **止盈位/压力位**: 给出具体的参考价格。
        
        **风格要求**: 专业、客观、逻辑清晰，避免模棱两可的废话。
        """
        
        # 3. Call API
        payload = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }]
        }
        
        headers = {'Content-Type': 'application/json'}
        
        try:
            # Gemini 3 Pro might be slow, increase timeout
            response = requests.post(self.url, headers=headers, data=json.dumps(payload), timeout=90)
            
            if response.status_code == 200:
                result = response.json()
                try:
                    return result['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    return f"API 返回结构异常: {result}"
            else:
                return f"API 请求失败 (Code {response.status_code}): {response.text}"
                
        except Exception as e:
            return f"请求发生错误: {str(e)}"
