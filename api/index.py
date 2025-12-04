"""
Vercel serverless function entrypoint for FastAPI application.
This file is required by Vercel to locate the FastAPI app.
"""

import sys
from pathlib import Path

# Add src directory to Python path so we can import the chatbot module
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import the FastAPI app from the web module
from finanlyzeos_chatbot.web import app

# Export the app variable - Vercel will look for 'app' specifically
__all__ = ["app"]

