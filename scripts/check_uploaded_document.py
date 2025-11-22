#!/usr/bin/env python3
"""
Quick diagnostic script to check if an uploaded document exists in the database.
Usage: python scripts/check_uploaded_document.py doc_e66ec000
"""

import sys
import sqlite3
from pathlib import Path

def check_document(document_id: str, db_path: Path, check_all_dbs: bool = False):
    """Check if a document exists in the database."""
    print(f"\n{'='*80}")
    print(f"CHECKING DOCUMENT: {document_id}")
    print(f"{'='*80}\n")
    
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return
    
    if check_all_dbs:
        # Check all database files
        all_dbs = [
            Path("data/sqlite/finanlyzeos_chatbot.sqlite3"),
            Path("data/sqlite/finalyzeos_chatbot.sqlite3"),
            Path("finanlyzeos_chatbot.sqlite3"),
            Path("finalyzeos_chatbot.sqlite3"),
        ]
        for db in all_dbs:
            if db.exists() and db != db_path:
                print(f"\n🔍 Also checking: {db}")
                check_document(document_id, db, check_all_dbs=False)
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT document_id, conversation_id, filename, file_type, file_size,
                       LENGTH(content) as content_len, created_at
                FROM uploaded_documents
                WHERE document_id = ?
                """,
                (document_id,)
            )
            row = cursor.fetchone()
            
            if row:
                print(f"✅ Document FOUND in database:")
                print(f"   - Document ID: {row['document_id']}")
                print(f"   - Filename: {row['filename']}")
                print(f"   - Conversation ID: {row['conversation_id']}")
                print(f"   - File Type: {row['file_type']}")
                print(f"   - File Size: {row['file_size']} bytes")
                print(f"   - Content Length: {row['content_len']} characters")
                print(f"   - Created At: {row['created_at']}")
                
                if row['content_len'] == 0:
                    print(f"\n⚠️ WARNING: Document has NO CONTENT (0 characters)")
                    print(f"   This means text extraction failed or file was empty")
                else:
                    print(f"\n✅ Document has content ({row['content_len']} chars) - should work!")
                    
                    # Show first 200 chars of content
                    content_cursor = conn.execute(
                        "SELECT content FROM uploaded_documents WHERE document_id = ?",
                        (document_id,)
                    )
                    content_row = content_cursor.fetchone()
                    if content_row and content_row[0]:
                        print(f"\n📝 Content preview (first 200 chars):")
                        print(f"   {content_row[0][:200]}...")
            else:
                print(f"❌ Document NOT FOUND in database!")
                print(f"\n📋 Checking all documents in database...")
                all_docs = conn.execute(
                    "SELECT document_id, filename FROM uploaded_documents ORDER BY created_at DESC LIMIT 10"
                ).fetchall()
                if all_docs:
                    print(f"   Found {len(all_docs)} documents:")
                    for doc in all_docs:
                        print(f"   - {doc['document_id']}: {doc['filename']}")
                else:
                    print(f"   No documents found in database!")
                    
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_uploaded_document.py <document_id>")
        print("Example: python scripts/check_uploaded_document.py doc_e66ec000")
        sys.exit(1)
    
    document_id = sys.argv[1]
    
    # Try to find database path - check all possible locations
    possible_paths = [
        Path("data/sqlite/finanlyzeos_chatbot.sqlite3"),
        Path("data/sqlite/finalyzeos_chatbot.sqlite3"),
        Path("finanlyzeos_chatbot.sqlite3"),
        Path("finalyzeos_chatbot.sqlite3"),
        Path("data/financial.db"),
    ]
    
    print("🔍 Searching for database files...")
    found_dbs = []
    for path in possible_paths:
        if path.exists():
            found_dbs.append(path)
            print(f"   ✅ Found: {path}")
    
    if not found_dbs:
        print("❌ Could not find any database files in standard locations")
        db_path = Path(input("Please enter database path: "))
    elif len(found_dbs) == 1:
        db_path = found_dbs[0]
        print(f"\n✅ Using database: {db_path}")
    else:
        print(f"\n⚠️ Found {len(found_dbs)} database files. Checking all...")
        db_path = found_dbs[0]  # Check first one, then others if needed
    
    check_document(document_id, db_path)

