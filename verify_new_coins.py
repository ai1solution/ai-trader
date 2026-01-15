
import requests
import sys

# List extracted from user text
COINS_TO_CHECK = [
    "AIA", "BOT", "DOLO", "DAM", "AIX", "CC", 
    "GOATS", "BFI", "DDOYR", "BBI", "OMNIA", "TTBK",
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE"
]

def check_binance():
    print("Fetching Binance exchange info...")
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url)
        data = response.json()
        
        all_symbols = [s['symbol'] for s in data['symbols']]
        
        print(f"Total symbols on Binance: {len(all_symbols)}")
        
        valid = []
        invalid = []
        
        for coin in COINS_TO_CHECK:
            # Check with USDT
            symbol_usdt = f"{coin.upper()}USDT"
            
            if symbol_usdt in all_symbols:
                valid.append(symbol_usdt)
                print(f"[OK] {symbol_usdt} found.")
            else:
                invalid.append(coin)
                print(f"[MISSING] {coin} ({symbol_usdt} not found)")

        print("\nSummary:")
        print(f"Valid: {len(valid)}")
        print(f"Invalid/Missing: {len(invalid)}")
        print(f"Valid list for config: {[s.replace('USDT', '/USDT') for s in valid]}")

    except Exception as e:
        print(f"Error checking Binance: {e}")

if __name__ == "__main__":
    check_binance()
