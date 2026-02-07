
import sys
import os
import time
sys.path.append(os.getcwd())

from stock_app.data_loader import DataLoader
from stock_app.indicators import Indicators
from stock_app.strategies import Strategies    

from stock_app.scanner import scan_single_stock

print("Starting debug...")
code = "000001"
name = "PingAn"
# Load: 400 days before 
load_start = "2024-01-01"
load_end = "2025-02-07"
# Scan: Recent window
scan_start = "2025-01-01"
scan_end = "2025-02-07"

# Check config: Fighting strategy
checks_config = [(True, 'Signal_Fighting', 'Fighting')]

args = (code, name, load_start, load_end, scan_start, scan_end, checks_config)

print(f"Scanning {code}...")
t0 = time.time()
res = scan_single_stock(args)
print(f"Scan finished in {time.time()-t0:.4f}s.")
print("Result:", res)
