#!/usr/bin/env python3
"""
Test the complete file upload to chat flow.
This verifies that files can be uploaded, retrieved, and included in chat context.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.finanlyzeos_chatbot.config import load_settings
from src.finanlyzeos_chatbot import database
from src.finanlyzeos_chatbot.document_context import build_uploaded_document_context

def test_file_upload_flow():
    """Test the complete file upload to chat flow."""
    
    print("\n" + "="*80)
    print("TESTING FILE UPLOAD TO CHAT FLOW")
    print("="*80 + "\n")
    
    # Load settings to get database path
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
    
    # Test 1: Check if documents exist in database (direct SQL query)
    print("="*80)
    print("TEST 1: Check documents in database")
    print("="*80)
    
    try:
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT document_id, filename, LENGTH(content) as content_len FROM uploaded_documents ORDER BY created_at DESC LIMIT 10"
            )
            rows = cursor.fetchall()
            
        print(f"📋 Found {len(rows)} documents in database (direct query)")
        
        if not rows:
            print("⚠️ No documents found in database")
            print("   Upload a file first, then run this test again")
            return False
        
        # Show recent documents
        print("\n📄 Recent documents:")
        for i, row in enumerate(rows[:5], 1):
            print(f"   {i}. {row[0]}: {row[1]} ({row[2]} chars)")
        
        # Use the most recent document for testing
        test_doc_id = rows[0][0]
        print(f"\n✅ Using document '{test_doc_id}' for testing")
        
    except Exception as e:
        print(f"❌ Error fetching documents: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Fetch document by ID
    print("\n" + "="*80)
    print("TEST 2: Fetch document by ID")
    print("="*80)
    
    try:
        documents = database.fetch_uploaded_documents_by_ids(
            db_path,
            [test_doc_id]
        )
        
        if not documents:
            print(f"❌ Document {test_doc_id} not found when fetching by ID")
            return False
        
        doc = documents[0]
        content_len = len(doc.content) if doc.content else 0
        print(f"✅ Document found:")
        print(f"   - ID: {doc.document_id}")
        print(f"   - Filename: {doc.filename}")
        print(f"   - Content length: {content_len} characters")
        
        if content_len == 0:
            print(f"⚠️ WARNING: Document has no content!")
            return False
        
        print(f"   - Content preview (first 200 chars):")
        print(f"     {doc.content[:200]}...")
        
    except Exception as e:
        print(f"❌ Error fetching document by ID: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Build document context
    print("\n" + "="*80)
    print("TEST 3: Build document context")
    print("="*80)
    
    try:
        user_query = "What is this document about?"
        doc_context = build_uploaded_document_context(
            user_query,
            conversation_id=None,
            database_path=db_path,
            file_ids=[test_doc_id],
            max_chars=10000,
            max_snippet_per_doc=5000,
        )
        
        if not doc_context:
            print(f"❌ Document context is None or empty")
            return False
        
        print(f"✅ Document context built successfully:")
        print(f"   - Length: {len(doc_context)} characters")
        print(f"   - Contains 'UPLOADED FILES': {'UPLOADED FILES' in doc_context}")
        print(f"   - Contains filename: {doc.filename in doc_context}")
        print(f"   - Contains content: {doc.content[:100] in doc_context}")
        
        print(f"\n📝 Context preview (first 500 chars):")
        print("-" * 80)
        print(doc_context[:500])
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ Error building document context: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Verify context would be included in LLM prompt
    print("\n" + "="*80)
    print("TEST 4: Verify context format for LLM")
    print("="*80)
    
    if doc_context:
        # Check for required markers
        has_markers = (
            "UPLOADED FILES" in doc_context or 
            "UPLOADED FINANCIAL DOCUMENTS" in doc_context
        )
        has_content = len(doc_context) > 100
        has_filename = doc.filename in doc_context
        
        print(f"✅ Context checks:")
        print(f"   - Has file markers: {has_markers}")
        print(f"   - Has substantial content: {has_content}")
        print(f"   - Contains filename: {has_filename}")
        
        if has_markers and has_content and has_filename:
            print(f"\n✅ ALL TESTS PASSED!")
            print(f"   The file upload system is working correctly.")
            print(f"   Document context will be included in LLM prompts.")
            return True
        else:
            print(f"\n⚠️ Some checks failed - context may not be properly formatted")
            return False
    
    print("\n❌ TEST FAILED: No document context generated")
    return False

if __name__ == "__main__":
    success = test_file_upload_flow()
    sys.exit(0 if success else 1)

