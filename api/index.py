"""
Vercel serverless function entrypoint for FastAPI application.
This file is required by Vercel to locate the FastAPI app.

Vercel's Python runtime expects either:
1. An 'app' variable (FastAPI/Flask instance), OR
2. A 'handler' function that takes (event, context) parameters

For FastAPI, we export the app directly, and Vercel's @vercel/python adapter
will automatically wrap it in an ASGI handler.
"""

import sys
import os
import logging
from pathlib import Path

# Set up basic logging for debugging import issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Add src directory to Python path so we can import the chatbot module
    project_root = Path(__file__).parent.parent
    src_path = project_root / "src"
    
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    logger.info(f"Added {src_path} to Python path")
    logger.info(f"Python path: {sys.path[:3]}...")  # Log first 3 entries
    
    # Import the FastAPI app from the web module
    # This import may fail if there are import-time errors in web.py
    logger.info("Importing FastAPI app from finanlyzeos_chatbot.web...")
    from finanlyzeos_chatbot.web import app
    
    logger.info("Successfully imported FastAPI app")
    
    # Verify app is a FastAPI instance
    if not hasattr(app, 'router'):
        raise TypeError("Imported 'app' is not a FastAPI instance")
    
    logger.info("FastAPI app validated successfully")
    
except ImportError as e:
    logger.error(f"Import error: {e}", exc_info=True)
    # Re-raise with more context
    raise ImportError(
        f"Failed to import FastAPI app from finanlyzeos_chatbot.web: {e}\n"
        f"Python path: {sys.path}\n"
        f"Project root: {project_root}\n"
        f"Source path: {src_path}\n"
        f"Source exists: {src_path.exists() if 'src_path' in locals() else 'N/A'}"
    ) from e
except Exception as e:
    logger.error(f"Unexpected error during import: {e}", exc_info=True)
    raise

# Export the app variable - Vercel will look for 'app' specifically
# The @vercel/python adapter will automatically create an ASGI handler
__all__ = ["app"]

