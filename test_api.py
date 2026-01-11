import urllib.request
import json
import time

def test_endpoint(url, method="GET", data=None):
    try:
        req = urllib.request.Request(url, method=method)
        if data:
            req.add_header('Content-Type', 'application/json')
            req.data = json.dumps(data).encode('utf-8')
            
        with urllib.request.urlopen(req) as response:
            print(f"[{method}] {url} -> {response.status}")
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error hitting {url}: {e}")
        return None

base = "http://localhost:8000"

# 1. Root
print("Testing Root...")
res = test_endpoint(f"{base}/")
print(res)

# 2. V4 Status (Should be stopped)
print("\nTesting V4 Status...")
res = test_endpoint(f"{base}/v4/status")
print(res)

# 3. Analyze Regime (BTC)
# This might take a few seconds as it fetches data
print("\nTesting Analyze Regime (BTC)...")
res = test_endpoint(f"{base}/analyze/regime", "POST", {
    "symbol": "BTC/USDT",
    "date": "2024-01-01T00:00:00"
})
print(res)

print("\nTests Complete.")
