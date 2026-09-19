"""
Seed Vector Database with Common Incident Patterns

This script loads incident templates and stores them in ChromaDB
for RAG-based similar incident search.
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("ERROR: chromadb not installed. Run: pip install chromadb")
    sys.exit(1)

print("=" * 80)
print("VECTOR DATABASE SEEDING SCRIPT")
print("=" * 80)
print()

# Load incident templates
templates_file = Path(__file__).parent.parent / "data" / "incident_templates.json"

if not templates_file.exists():
    print(f"ERROR: Templates file not found: {templates_file}")
    sys.exit(1)

print(f"Loading templates from: {templates_file}")
with open(templates_file, 'r') as f:
    data = json.load(f)
    templates = data.get("incident_templates", [])

print(f"Loaded {len(templates)} incident templates")
print()

# Initialize ChromaDB
print("Initializing ChromaDB...")
chroma_client = chromadb.Client(Settings(
    anonymized_telemetry=False,
    allow_reset=True
))

# Create or get collection
collection_name = "incident_history"
print(f"Creating collection: {collection_name}")

# Reset collection if exists
try:
    chroma_client.delete_collection(collection_name)
    print("  Deleted existing collection")
except:
    pass

collection = chroma_client.create_collection(
    name=collection_name,
    metadata={"description": "Historical incident data for RAG search"}
)
print(f"  Collection created successfully")
print()

# Prepare documents for insertion
documents = []
metadatas = []
ids = []

print("Processing incident templates...")
for idx, template in enumerate(templates, 1):
    # Create document text (what will be embedded)
    doc_text = f"""
Incident: {template['title']}
Category: {template['category']}
Severity: {template['severity']}
Description: {template['description']}
Root Cause: {template['root_cause']}
Affected Service: {template['affected_service']}
Tags: {', '.join(template.get('tags', []))}

Recommendations:
"""

    # Add recommendations
    for rec in template.get('recommendations', []):
        doc_text += f"\n- {rec['action']}: {rec['reasoning']} (Criticality: {rec['criticality']})"

    documents.append(doc_text.strip())

    # Store metadata
    metadata = {
        "incident_id": template['id'],
        "title": template['title'],
        "category": template['category'],
        "severity": template['severity'],
        "service": template['affected_service'],
        "timestamp": datetime.utcnow().isoformat(),
        "template": "true",
        "tags": ",".join(template.get('tags', []))
    }
    metadatas.append(metadata)

    # Generate unique ID
    ids.append(f"template-{template['id']}")

    print(f"  [{idx}/{len(templates)}] {template['title']}")

print()
print("Inserting into ChromaDB...")

# Insert all documents
collection.add(
    documents=documents,
    metadatas=metadatas,
    ids=ids
)

print(f"[SUCCESS] Successfully inserted {len(documents)} incident templates")
print()

# Verify insertion
count = collection.count()
print(f"Collection '{collection_name}' now contains {count} documents")
print()

# Test query
print("Testing RAG search...")
test_query = "high memory usage causing pod crashes"
print(f"Query: '{test_query}'")
print()

results = collection.query(
    query_texts=[test_query],
    n_results=3
)

print("Top 3 similar incidents:")
for i, (doc, metadata, distance) in enumerate(zip(
    results['documents'][0],
    results['metadatas'][0],
    results['distances'][0]
), 1):
    print(f"\n{i}. {metadata['title']}")
    print(f"   Category: {metadata['category']}")
    print(f"   Severity: {metadata['severity']}")
    print(f"   Similarity Score: {1 - distance:.2%}")
    print(f"   Preview: {doc[:150]}...")

print()
print("=" * 80)
print("[SUCCESS] VECTOR DATABASE SEEDING COMPLETE")
print("=" * 80)
print()
print("Next steps:")
print("  1. Restart analyzer-agent to use seeded data")
print("  2. Test similar incident search via API")
print("  3. Monitor RAG search in logs (should return results now)")
print()
print("To test RAG search:")
print("  curl -X POST http://localhost:8000/api/v1/rag/query \\")
print("    -H 'Content-Type: application/json' \\")
print("    -d '{\"query\": \"high memory usage\", \"top_k\": 5}'")
print()
