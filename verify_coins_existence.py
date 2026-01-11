
import requests
import sys

# List provided by user (formatted)
COINS_TO_CHECK = [
    "AIatMeta", "RedBul", "SpaceXI", "Shitcoin", "CRANS", 
    "TSLAx", "Silver", "MEZO", "GoogolAI", "Rockstar", 
    "SKR", "ztc", "FOgo", "Sent", "dn", "inx"
]

def check_binance():
    print("Fetching Binance exchange info...")
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url)
        data = response.json()
        
        all_symbols = [s['symbol'] for s in data['symbols']]
        quote_assets = set([s['quoteAsset'] for s in data['symbols']])
        
        print(f"Total symbols on Binance: {len(all_symbols)}")
        
        valid = []
        invalid = []
        
        for coin in COINS_TO_CHECK:
            # Check with USDT
            symbol_usdt = f"{coin.upper()}USDT"
            # Check with BUSD (legacy) or USDC
            
            if symbol_usdt in all_symbols:
                valid.append(symbol_usdt)
                print(f"[OK] {symbol_usdt} found.")
            else:
                # Try simple matching
                found = False
                for s in all_symbols:
                    if s.startswith(coin.upper()) and s.endswith("USDT"):
                        print(f"[MATCH?] {coin} -> {s}")
                        found = True
                
                if not found:
                    invalid.append(coin)
                    print(f"[MISSING] {coin} (checked {symbol_usdt})")

        print("\nSummary:")
        print(f"Valid: {len(valid)}")
        print(f"Invalid/Missing: {len(invalid)}")
        print(f"Invalid list: {invalid}")

    except Exception as e:
        print(f"Error checking Binance: {e}")

if __name__ == "__main__":
    check_binance()
