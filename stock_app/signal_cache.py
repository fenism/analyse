"""
信号缓存管理模块
用于预计算和缓存所有股票的策略信号，提升筛选性能
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from typing import List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

from data_loader import DataLoader
from strong_strategies import StrongStrategies
from weak_strategies import WeakStrategies


class SignalCacheBuilder:
    """信号缓存构建器"""
    
    def __init__(self, data_dir="stock_app/data/market_data", cache_dir="stock_app/data/signal_cache"):
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        self.loader = DataLoader(data_dir)
        
        # 确保缓存目录存在
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def build_all_signals(self, start_date: str = None, end_date: str = None, 
                         progress_callback=None) -> bool:
        """
        构建所有股票的信号缓存
        
        :param start_date: 开始日期（默认从一年前开始）
        :param end_date: 结束日期（默认到今天）
        :param progress_callback: 进度回调函数 callback(current, total, message)
        :return: 是否成功
        """
        try:
            # 1. 获取股票列表
            stock_list = self.loader.get_stock_list()
            if stock_list.empty:
                print("❌ 股票列表为空，请先下载数据")
                return False
            
            total_stocks = len(stock_list)
            print(f"📊 开始构建信号缓存，共 {total_stocks} 只股票...")
            
            # 2. 确定日期范围
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                # 默认从一年半前开始（确保有足够数据计算指标）
                start_date = (datetime.now() - pd.Timedelta(days=550)).strftime("%Y-%m-%d")
            
            # 3. 加载上证指数数据（用于RS策略）
            index_df = None
            index_path = os.path.join(self.data_dir, "000001.SH.csv")
            if os.path.exists(index_path):
                try:
                    index_df = pd.read_csv(index_path)
                    index_df['date'] = pd.to_datetime(index_df['date'])
                    print("✅ 上证指数数据加载成功")
                except:
                    print("⚠️ 上证指数数据加载失败，RS策略将跳过")
            
            # 4. 遍历计算
            strong_records = []
            weak_records = []
            
            for idx, row in stock_list.iterrows():
                code = row['code']
                name = row.get('name', '')
                
                # 进度回调
                if progress_callback:
                    progress_callback(idx + 1, total_stocks, f"正在处理: {code} - {name}")
                
                if (idx + 1) % 100 == 0:
                    print(f"进度: {idx + 1}/{total_stocks}")
                
                # 加载股票数据
                df = self.loader.get_k_data(code, start_date, end_date)
                if df.empty or len(df) < 100:  # 至少需要100天数据
                    continue
                
                # 计算强势策略信号
                try:
                    strong_signals = StrongStrategies.check_all_strong_strategies(
                        df, index_df=index_df
                    )
                    
                    # 添加股票代码和名称
                    strong_signals['code'] = code
                    strong_signals['name'] = name
                    strong_signals['date'] = df['date'].values
                    
                    strong_records.append(strong_signals)
                except Exception as e:
                    print(f"⚠️ {code} 强势策略计算失败: {e}")
                
                # 计算弱势策略信号
                try:
                    weak_signals = WeakStrategies.check_all_weak_strategies(df)
                    
                    # 添加股票代码和名称
                    weak_signals['code'] = code
                    weak_signals['name'] = name
                    weak_signals['date'] = df['date'].values
                    
                    weak_records.append(weak_signals)
                except Exception as e:
                    print(f"⚠️ {code} 弱势策略计算失败: {e}")
            
            # 5. 合并所有数据
            if strong_records:
                strong_df = pd.concat(strong_records, ignore_index=True)
                strong_path = os.path.join(self.cache_dir, "strong_signals.parquet")
                strong_df.to_parquet(strong_path, index=False, compression='snappy')
                print(f"✅ 强势信号缓存已保存: {len(strong_df)} 条记录")
            
            if weak_records:
                weak_df = pd.concat(weak_records, ignore_index=True)
                weak_path = os.path.join(self.cache_dir, "weak_signals.parquet")
                weak_df.to_parquet(weak_path, index=False, compression='snappy')
                print(f"✅ 弱势信号缓存已保存: {len(weak_df)} 条记录")
            
            # 6. 保存元数据
            metadata = {
                "cache_version": "1.0",
                "last_build_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_date_range": [start_date, end_date],
                "total_stocks": total_stocks,
                "strong_strategies": ["Z_Score", "RS", "TKOS", "DTR_Plus", "Fighting", "UA", "HMC"],
                "weak_strategies": ["HLP3", "Limit", "RSI_Rev", "Spring", "Pinbar", "Money_Flow", "UA", "DBL_VOL"]
            }
            
            metadata_path = os.path.join(self.cache_dir, "cache_metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print("🎉 信号缓存构建完成！")
            return True
            
        except Exception as e:
            print(f"❌ 缓存构建失败: {e}")
            import traceback
            traceback.print_exc()
            return False


class SignalCacheReader:
    """信号缓存读取器"""
    
    def __init__(self, cache_dir="stock_app/data/signal_cache"):
        self.cache_dir = cache_dir
    
    def is_cache_valid(self) -> Tuple[bool, str]:
        """
        检查缓存是否有效
        
        :return: (是否有效, 提示信息)
        """
        metadata_path = os.path.join(self.cache_dir, "cache_metadata.json")
        strong_path = os.path.join(self.cache_dir, "strong_signals.parquet")
        weak_path = os.path.join(self.cache_dir, "weak_signals.parquet")
        
        # 检查文件是否存在
        if not os.path.exists(metadata_path):
            return False, "缓存元数据不存在"
        if not os.path.exists(strong_path):
            return False, "强势信号缓存不存在"
        if not os.path.exists(weak_path):
            return False, "弱势信号缓存不存在"
        
        # 读取元数据
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            build_time = metadata.get('last_build_time', 'Unknown')
            date_range = metadata.get('data_date_range', [])
            
            return True, f"缓存有效 | 构建时间: {build_time} | 数据范围: {date_range[0]} ~ {date_range[1]}"
        except:
            return False, "缓存元数据损坏"
    
    def get_metadata(self) -> Optional[dict]:
        """获取缓存元数据"""
        metadata_path = os.path.join(self.cache_dir, "cache_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def filter_strong_stocks(self, selected_strategies: List[str], 
                            start_date: str, end_date: str) -> pd.DataFrame:
        """
        筛选符合强势策略的股票
        
        :param selected_strategies: 选中的策略列表，如 ['Z_Score', 'DTR_Plus']
        :param start_date: 筛选开始日期
        :param end_date: 筛选结束日期
        :return: 符合条件的股票DataFrame
        """
        strong_path = os.path.join(self.cache_dir, "strong_signals.parquet")
        
        if not os.path.exists(strong_path):
            raise FileNotFoundError("强势信号缓存不存在，请先构建缓存")
        
        # 读取缓存
        df = pd.read_parquet(strong_path)
        df['date'] = pd.to_datetime(df['date'])
        
        # 日期过滤
        mask_date = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
        df = df[mask_date]
        
        # 策略过滤
        signal_cols = [f'Signal_{s}' for s in selected_strategies]
        
        # 确保所有信号列都存在
        available_cols = [col for col in signal_cols if col in df.columns]
        if not available_cols:
            return pd.DataFrame(columns=['code', 'name', 'date', 'triggered_strategies'])
        
        # 筛选：至少触发一个策略
        mask_signal = df[available_cols].any(axis=1)
        result = df[mask_signal].copy()
        
        # 添加触发的策略列表
        def get_triggered(row):
            triggered = []
            for col in available_cols:
                if row[col]:
                    triggered.append(col.replace('Signal_', ''))
            return ', '.join(triggered)
        
        result['triggered_strategies'] = result.apply(get_triggered, axis=1)
        
        # 返回关键列
        return result[['code', 'name', 'date', 'triggered_strategies'] + available_cols]
    
    def filter_weak_stocks(self, selected_strategies: List[str], 
                          start_date: str, end_date: str) -> pd.DataFrame:
        """
        筛选符合弱势策略的股票
        
        :param selected_strategies: 选中的策略列表，如 ['HLP3', 'Limit']
        :param start_date: 筛选开始日期
        :param end_date: 筛选结束日期
        :return: 符合条件的股票DataFrame
        """
        weak_path = os.path.join(self.cache_dir, "weak_signals.parquet")
        
        if not os.path.exists(weak_path):
            raise FileNotFoundError("弱势信号缓存不存在，请先构建缓存")
        
        # 读取缓存
        df = pd.read_parquet(weak_path)
        df['date'] = pd.to_datetime(df['date'])
        
        # 日期过滤
        mask_date = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
        df = df[mask_date]
        
        # 策略过滤
        signal_cols = [f'Signal_{s}' for s in selected_strategies]
        
        # 确保所有信号列都存在
        available_cols = [col for col in signal_cols if col in df.columns]
        if not available_cols:
            return pd.DataFrame(columns=['code', 'name', 'date', 'triggered_strategies'])
        
        # 筛选：至少触发一个策略
        mask_signal = df[available_cols].any(axis=1)
        result = df[mask_signal].copy()
        
        # 添加触发的策略列表
        def get_triggered(row):
            triggered = []
            for col in available_cols:
                if row[col]:
                    triggered.append(col.replace('Signal_', ''))
            return ', '.join(triggered)
        
        result['triggered_strategies'] = result.apply(get_triggered, axis=1)
        
        # 返回关键列
        return result[['code', 'name', 'date', 'triggered_strategies'] + available_cols]
