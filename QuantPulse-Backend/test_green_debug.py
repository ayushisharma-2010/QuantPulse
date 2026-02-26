"""
Debug green score endpoint
"""
import requests

symbols_to_test = [
    "RELIANCE",
    "RELIANCE.NS",
    "TCS",
    "TCS.NS",
    "ICICIBANK",
    "ICICIBANK.NS"
]

for symbol in symbols_to_test:
    print(f"\nTesting: {symbol}")
    r = requests.get(f"http://localhost:8090/v1/green-score/{symbol}")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"✓ Score: {data.get('score')}/100 ({data.get('category')})")
    else:
        print(f"✗ Error: {r.json().get('detail')}")
