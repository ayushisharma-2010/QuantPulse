"""
Test script for Pathway RAG endpoint - ESG query
"""
import requests
import json

# Test RAG query about ESG
url = "http://localhost:8090/v1/rag/query"
payload = {
    "query": "What is the ESG score for ICICI Bank and what are their environmental initiatives?",
    "symbols": ["ICICIBANK.NS"]
}

print("Testing RAG endpoint with ESG query...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\nSending request...\n")

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"\nResponse:")
    result = response.json()
    print(f"Answer: {result['answer']}")
    print(f"\nCitations: {len(result['citations'])} documents")
    for i, citation in enumerate(result['citations'], 1):
        print(f"  {i}. {citation['title']} ({citation['source']})")
except Exception as e:
    print(f"Error: {e}")
