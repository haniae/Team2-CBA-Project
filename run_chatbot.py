#!/usr/bin/env python3
"""
BenchmarkOS Chatbot Runner
Starts the chatbot server with proper configuration
"""

import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_environment():
    """Check if environment is properly configured."""
    print("🔍 Checking environment...")
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("❌ .env file not found")
        print("Please copy env.example to .env and configure it")
        return False
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Virtual environment not activated")
        print("Please activate virtual environment first:")
        if os.name == 'nt':  # Windows
            print("   venv\\Scripts\\activate")
        else:  # Unix/Linux/macOS
            print("   source venv/bin/activate")
        return False
    
    print("✅ Environment check passed")
    return True


def check_dependencies():
    """Check if required dependencies are installed."""
    print("📦 Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "openai",
        "sqlalchemy",
        "requests"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install missing packages:")
        print("   pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies are installed")
    return True


def start_chatbot():
    """Start the chatbot server."""
    print("🚀 Starting BenchmarkOS Chatbot...")
    
    try:
        # Import and start the chatbot
        from finanlyzeos_chatbot.web import app
        
        import uvicorn
        
        # Get configuration from environment
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        debug = os.getenv("DEBUG", "True").lower() == "true"
        reload = os.getenv("RELOAD", "True").lower() == "true"
        
        print(f"🌐 Starting server on {host}:{port}")
        print(f"🔧 Debug mode: {debug}")
        print(f"🔄 Auto-reload: {reload}")
        print(f"📱 Access the chatbot at: http://localhost:{port}")
        
        # Start the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            debug=debug,
            reload=reload,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please make sure all dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Error starting chatbot: {e}")
        return False


def main():
    """Main function."""
    print("🤖 BenchmarkOS Chatbot")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Start chatbot
    start_chatbot()


if __name__ == "__main__":
    main()