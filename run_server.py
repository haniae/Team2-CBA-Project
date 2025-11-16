#!/usr/bin/env python3
"""
Simple server launcher for BenchmarkOS Chatbot UI
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("🚀 Starting BenchmarkOS Chatbot Server")
    print("=" * 80)
    print()
    print("Server will be available at: http://localhost:8000")
    print("Press Ctrl+C to stop")
    print()
    print("=" * 80)
    print()
    
    uvicorn.run(
        "finanlyzeos_chatbot.web:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

