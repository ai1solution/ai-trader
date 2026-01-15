import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from v1_legacy.trading_engine import format_price as v1_fmt
from v3.utils import format_price_str as v3_fmt
from v4.common.types import format_price as v4_fmt

# V2 is harder to import due to structure, but we can check logic or try import
try:
    from v2_modern.src.engine import format_price as v2_fmt
except ImportError:
    # Define it as it was implemented in V2
    def v2_fmt(price):
        return f"{price:.8f}".rstrip('0').rstrip('.')

prices = [0.00001234, 100.50000000, 95000.1, 1.23456789]

print("V1:")
for p in prices: print(f"{p} -> {v1_fmt(p)}")
print("\nV2 (Logic Check):")
for p in prices: print(f"{p} -> {v2_fmt(p)}")
print("\nV3:")
for p in prices: print(f"{p} -> {v3_fmt(p)}")
print("\nV4:")
for p in prices: print(f"{p} -> {v4_fmt(p)}")
