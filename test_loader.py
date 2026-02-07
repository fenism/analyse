
from stock_app.data_loader import DataLoader
import datetime

loader = DataLoader()
print("Testing DataLoader...")
df = loader.get_k_data("000001", datetime.date(2023, 1, 1), datetime.date(2024, 1, 1))

if not df.empty:
    print(f"Success! Loaded {len(df)} rows.")
    print(df.head())
else:
    print("Failed to load data.")
