"""
Alternative Vercel entrypoint (root level).
Vercel checks multiple locations - this serves as a fallback.
"""

import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import the FastAPI app
from finanlyzeos_chatbot.web import app

__all__ = ["app"]

