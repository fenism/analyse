
import pandas as pd
import os
import datetime

class DataLoader:
    def __init__(self, data_dir="stock_app/data/market_data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            print(f"Warning: Data directory {data_dir} does not exist. Please run download_data.py first.")

    def get_stock_list(self, date=None):
        """Fetch stock list from local warehouse."""
        list_path = os.path.join(self.data_dir, "stock_list.csv")
        if os.path.exists(list_path):
            return pd.read_csv(list_path, dtype={'code': str})
        else:
            return pd.DataFrame(columns=['code', 'name'])

    def get_k_data(self, code, start_date, end_date):
        """
        Fetch K-line data from local CSV.
        """
        # Ensure code is 6 digits string
        code = str(code).zfill(6)
        file_path = os.path.join(self.data_dir, f"{code}.csv")
        
        if not os.path.exists(file_path):
            print(f"[DataLoader] File not found: {file_path}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(file_path)
            
            # Standardize dates
            if 'date' not in df.columns:
                print(f"[DataLoader] 'date' column missing in {file_path}")
                return pd.DataFrame()
            
            df['date'] = pd.to_datetime(df['date'])
            
            # Ensure start_date/end_date are pd.Timestamp
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            # Filter
            mask = (df['date'] >= start_dt) & (df['date'] <= end_dt)
            res = df.loc[mask].copy()
            
            if res.empty:
                print(f"[DataLoader] Data empty after filtering. Range: {start_dt} - {end_dt}. File Range: {df['date'].min()} - {df['date'].max()}")
                
            return res
            
        except Exception as e:
            print(f"[DataLoader] Error reading {code}: {e}")
            return pd.DataFrame()
