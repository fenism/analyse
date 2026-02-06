
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
        file_path = os.path.join(self.data_dir, f"{code}.csv")
        
        if not os.path.exists(file_path):
            return pd.DataFrame()

        try:
            df = pd.read_csv(file_path)
            
            # Ensure filtering by date
            # Assuming format YYYY-MM-DD in file
            # But akshare might save YYYY-MM-DD or YYYYMMDD depending on source?
            # Akshare usually returns YYYY-MM-DD or datetime. 
            # In download script I didn't change format. Let's check format.
            # Usually string YYYY-MM-DD.
            
            # Simple string comparison works for ISO dates
            # Standardize input
            s_date = str(start_date).replace("-", "")
            e_date = str(end_date).replace("-", "")
            
            # Convert file date column to string YYYYMMDD for comparison if needed
            # Or just convert to datetime
            df['date'] = pd.to_datetime(df['date'])
            
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            mask = (df['date'] >= start_dt) & (df['date'] <= end_dt)
            return df.loc[mask].copy()
            
        except Exception as e:
            print(f"Error reading {code}: {e}")
            return pd.DataFrame()
