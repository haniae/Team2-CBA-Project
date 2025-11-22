#!/usr/bin/env python3
"""
Test if files uploaded to a conversation are being fetched correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.finanlyzeos_chatbot.config import load_settings
from src.finanlyzeos_chatbot import database
from src.finanlyzeos_chatbot.document_context import build_uploaded_document_context

def test_conversation_files():
    """Test fetching files from a conversation."""
    
    print("\n" + "="*80)
    print("TESTING CONVERSATION FILE FETCHING")
    print("="*80 + "\n")
    
    # Load settings
    try:
        settings = load_settings()
        db_path = settings.database_path
        print(f"✅ Settings loaded")
        print(f"📁 Database path: {db_path}")
        print(f"📁 Database exists: {db_path.exists()}\n")
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        return False
    
    if not db_path.exists():
        print(f"❌ Database file does not exist: {db_path}")
        return False
    
    # Get all conversations with files
    print("="*80)
    print("STEP 1: Find conversations with uploaded files")
    print("="*80)
    
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("""
            SELECT DISTINCT conversation_id, COUNT(*) as file_count
            FROM uploaded_documents
            WHERE conversation_id IS NOT NULL
            GROUP BY conversation_id
            ORDER BY file_count DESC
            LIMIT 10
        """)
        conversations = cursor.fetchall()
    
    if not conversations:
        print("❌ No conversations with files found")
        print("   Upload a file first, then run this test")
        return False
    
    print(f"✅ Found {len(conversations)} conversations with files:")
    for conv_id, file_count in conversations:
        print(f"   - {conv_id}: {file_count} files")
    
    # Test with the first conversation
    test_conv_id = conversations[0][0]
    print(f"\n✅ Testing with conversation: {test_conv_id}")
    
    # Step 2: Check what files are in the database for this conversation
    print("\n" + "="*80)
    print("STEP 2: Check files in database for this conversation")
    print("="*80)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("""
            SELECT document_id, filename, LENGTH(content) as content_len, conversation_id
            FROM uploaded_documents
            WHERE conversation_id = ?
            ORDER BY created_at DESC
        """, (test_conv_id,))
        db_files = cursor.fetchall()
    
    print(f"📋 Found {len(db_files)} files in database:")
    for doc_id, filename, content_len, conv_id in db_files:
        print(f"   - {doc_id}: {filename} ({content_len} chars, conv: {conv_id})")
    
    # Step 3: Test database.fetch_uploaded_documents
    print("\n" + "="*80)
    print("STEP 3: Test database.fetch_uploaded_documents()")
    print("="*80)
    
    try:
        fetched_docs = database.fetch_uploaded_documents(
            db_path,
            test_conv_id,
            limit=10,
            include_unscoped=False,
        )
        
        print(f"📋 fetch_uploaded_documents returned {len(fetched_docs)} documents")
        if fetched_docs:
            for i, doc in enumerate(fetched_docs, 1):
                content_len = len(doc.content) if doc.content else 0
                print(f"   {i}. {doc.document_id}: {doc.filename} ({content_len} chars)")
        else:
            print("   ⚠️ No documents returned!")
            print("   This is the problem - database function returned empty list")
            return False
    except Exception as e:
        print(f"❌ Error calling fetch_uploaded_documents: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Test build_uploaded_document_context
    print("\n" + "="*80)
    print("STEP 4: Test build_uploaded_document_context()")
    print("="*80)
    
    try:
        user_query = "What is this document about?"
        context = build_uploaded_document_context(
            user_query,
            test_conv_id,
            db_path,
            file_ids=None,  # Don't provide file_ids - should auto-fetch from conversation
            max_documents=10,
            max_chars=10000,
        )
        
        if context:
            print(f"✅ Context built successfully: {len(context)} characters")
            print(f"📝 Preview (first 500 chars):")
            print("-" * 80)
            print(context[:500])
            print("-" * 80)
            return True
        else:
            print("❌ Context is None or empty")
            print("   This means build_uploaded_document_context failed")
            return False
    except Exception as e:
        print(f"❌ Error building context: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_conversation_files()
    sys.exit(0 if success else 1)

