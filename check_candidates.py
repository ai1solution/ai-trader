
import requests

# Potential candidates to check
CANDIDATES = [
    # AI / Data
    "FET", "RNDR", "WLD", "GRT", "TAO", "ARKM", "AI", "NFP", "PHB", "AGIX", "OCEAN", "NEAR",
    # Meme
    "DOGE", "SHIB", "PEPE", "BONK", "WIF", "FLOKI", "MEME", "ORDI", "1000SATS", "BOME"
]

def check_candidates():
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url)
        data = response.json()
        all_symbols = set([s['symbol'] for s in data['symbols']])
        
        valid = []
        for base in CANDIDATES:
            symbol = f"{base}USDT"
            if symbol in all_symbols:
                valid.append(base)
                
        print("VALID_BINANCE_COINS_FOUND:")
        print(", ".join(valid))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_candidates()
