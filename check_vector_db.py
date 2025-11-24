"""Check vector database contents"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.rag_retriever import VectorStore

db_path = Path("data/financial.db")
print(f"Checking vector database for: {db_path}\n")

try:
    vector_store = VectorStore(db_path)
    if vector_store._available:
        sec_count = vector_store.sec_collection.count()
        uploaded_count = vector_store.uploaded_collection.count()
        print(f"✅ SEC narratives: {sec_count:,} documents")
        print(f"✅ Uploaded documents: {uploaded_count:,} documents")
        print(f"✅ Total: {sec_count + uploaded_count:,} documents")
        
        # Get sample metadata
        if sec_count > 0:
            try:
                sample = vector_store.sec_collection.peek(limit=3)
                if sample.get('metadatas'):
                    print(f"\n📄 Sample documents:")
                    for i, meta in enumerate(sample['metadatas'][:3], 1):
                        print(f"  {i}. {meta.get('ticker', 'N/A')} - {meta.get('section', 'N/A')} ({meta.get('filing_type', 'N/A')})")
            except:
                pass
    else:
        print("⚠️  Vector store not available")
except Exception as e:
    print(f"❌ Error: {e}")

