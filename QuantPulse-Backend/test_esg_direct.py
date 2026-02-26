"""
Test ESG document store directly
"""
import sys
sys.path.insert(0, '.')

from pathway_pipeline import SimpleDocumentStore
import os

# Initialize ESG store
esg_dir = os.path.join(os.path.dirname(__file__), 'pathway_data', 'esg')
esg_store = SimpleDocumentStore(esg_dir, 'esg')

# Scan and index
esg_store.scan_and_index()

print(f"Total documents indexed: {esg_store.get_document_count()}")
print(f"\nFirst 3 documents:")
for i, doc in enumerate(esg_store.documents[:3], 1):
    print(f"\n{i}. Symbol: {doc.get('symbol', 'N/A')}")
    print(f"   Company: {doc.get('company_name', 'N/A')}")
    print(f"   Score: {doc.get('overall_score', 'N/A')}")

# Test search
print(f"\n\nTesting search for 'RELIANCE.NS':")
results = esg_store.search(query="RELIANCE.NS", symbol_filter="RELIANCE.NS", top_k=1)
print(f"Results found: {len(results)}")
if results:
    print(f"Symbol: {results[0].get('symbol')}")
    print(f"Score: {results[0].get('overall_score')}")
