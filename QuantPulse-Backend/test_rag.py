"""
Test script for Pathway RAG endpoint
"""
import requests
import json

# Test RAG query
url = "http://localhost:8090/v1/rag/query"
payload = {
    "query": "What is the latest news about Reliance?",
    "symbols": ["RELIANCE.NS"]
}

print("Testing RAG endpoint...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\nSending request...\n")

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"\nResponse:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
