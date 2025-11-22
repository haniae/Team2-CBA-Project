#!/usr/bin/env python3
"""
Quick diagnostic script to test if a document exists in the database.
Run this to verify file uploads are being stored correctly.
"""

import sqlite3
from pathlib import Path
import sys

# Get database path from settings or use default
try:
    from src.finanlyzeos_chatbot.settings import Settings
    settings = Settings()
    db_path = Path(settings.database_path)
except:
    # Try common locations
    db_path = Path("data/sqlite/finalyzeos_chatbot.sqlite3")
    if not db_path.exists():
        db_path = Path("finalyzeos_chatbot.sqlite3")

print(f"Checking database: {db_path}")
print(f"Database exists: {db_path.exists()}")

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    print("Please provide the correct database path.")
    sys.exit(1)

# Test document ID from the user's request
test_doc_id = "doc_3f19c11f"

print(f"\n{'='*80}")
print(f"TESTING DOCUMENT QUERY")
print(f"{'='*80}")
print(f"Document ID to find: {test_doc_id}")

try:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='uploaded_documents'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        print("❌ Table 'uploaded_documents' does not exist!")
        conn.close()
        sys.exit(1)
    
    print("✅ Table 'uploaded_documents' exists")
    
    # Get all document IDs
    cursor.execute("SELECT document_id, filename, LENGTH(content) as content_len FROM uploaded_documents LIMIT 20")
    all_docs = cursor.fetchall()
    
    print(f"\n📋 Found {len(all_docs)} documents in database:")
    for doc in all_docs:
        print(f"   - ID: {doc['document_id']}, Filename: {doc['filename']}, Content: {doc['content_len']} chars")
    
    # Try exact match
    cursor.execute(
        "SELECT document_id, filename, file_type, LENGTH(content) as content_len, content FROM uploaded_documents WHERE document_id = ?",
        (test_doc_id,)
    )
    result = cursor.fetchone()
    
    if result:
        print(f"\n✅ FOUND DOCUMENT:")
        print(f"   ID: {result['document_id']}")
        print(f"   Filename: {result['filename']}")
        print(f"   Type: {result['file_type']}")
        print(f"   Content length: {result['content_len']} characters")
        if result['content']:
            print(f"   Content preview (first 300 chars):\n{result['content'][:300]}")
        else:
            print(f"   ⚠️ Content is EMPTY!")
    else:
        print(f"\n❌ Document NOT FOUND with exact ID: {test_doc_id}")
        print(f"\n💡 Trying partial match...")
        # Try partial match
        cursor.execute(
            "SELECT document_id, filename FROM uploaded_documents WHERE document_id LIKE ?",
            (f"%{test_doc_id[-8:]}%",)
        )
        similar = cursor.fetchall()
        if similar:
            print(f"   Found similar IDs:")
            for doc in similar:
                print(f"   - {doc['document_id']} ({doc['filename']})")
        else:
            print(f"   No similar IDs found")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n{'='*80}")

