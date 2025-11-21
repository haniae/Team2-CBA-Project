"""
Shared embedding model management for team consistency.

This module ensures all team members use the same embedding model
for consistent behavior across different environments.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Any
import json

LOGGER = logging.getLogger(__name__)

# Team-wide embedding model configuration
TEAM_EMBEDDING_CONFIG = {
    "model_name": "all-MiniLM-L6-v2",
    "model_version": "v1.0",
    "expected_hash": "sha256:placeholder",  # Will be updated with actual hash
    "download_url": None,  # Will be set to your shared location
    "local_cache_dir": ".embeddings_cache",
    "description": "Team-shared embedding model for consistent behavior"
}


class SharedEmbeddingManager:
    """Manages shared embedding models for team consistency."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or TEAM_EMBEDDING_CONFIG
        self.cache_dir = Path(self.config["local_cache_dir"])
        self.cache_dir.mkdir(exist_ok=True)
        
        # Model storage paths
        self.model_path = self.cache_dir / f"{self.config['model_name']}-{self.config['model_version']}"
        self.config_file = self.cache_dir / "embedding_config.json"
        
    def get_model_path(self) -> Path:
        """Get the path to the shared embedding model."""
        if not self.is_model_available():
            self.download_or_setup_model()
        
        return self.model_path
    
    def is_model_available(self) -> bool:
        """Check if the shared model is available locally."""
        return (
            self.model_path.exists() and 
            self.model_path.is_dir() and
            (self.model_path / "config.json").exists()
        )
    
    def download_or_setup_model(self) -> None:
        """Download or setup the shared embedding model."""
        if self.config.get("download_url"):
            self._download_from_url()
        else:
            self._setup_from_huggingface()
    
    def _setup_from_huggingface(self) -> None:
        """Setup model from Hugging Face (fallback)."""
        try:
            from sentence_transformers import SentenceTransformer
            
            LOGGER.info(f"Setting up shared embedding model: {self.config['model_name']}")
            
            # Download model to temporary location
            temp_model = SentenceTransformer(self.config['model_name'])
            
            # Save to our shared location
            temp_model.save(str(self.model_path))
            
            # Save configuration
            self._save_model_config()
            
            LOGGER.info(f"Shared embedding model ready at: {self.model_path}")
            
        except Exception as e:
            LOGGER.error(f"Failed to setup shared embedding model: {e}")
            raise
    
    def _download_from_url(self) -> None:
        """Download model from shared URL (when available)."""
        # This would be implemented when you have a shared storage solution
        LOGGER.info("Downloading from shared URL not yet implemented")
        self._setup_from_huggingface()  # Fallback for now
    
    def _save_model_config(self) -> None:
        """Save model configuration for verification."""
        config_data = {
            **self.config,
            "setup_timestamp": str(Path().cwd()),
            "model_files": list(self.model_path.glob("**/*")) if self.model_path.exists() else []
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
    
    def verify_model_integrity(self) -> bool:
        """Verify the model integrity (placeholder for hash checking)."""
        if not self.is_model_available():
            return False
        
        # TODO: Implement hash verification when we have the shared model
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the shared model."""
        if not self.config_file.exists():
            return {"status": "not_setup"}
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            return {"status": "error", "error": str(e)}


def create_team_embedding_package() -> Path:
    """
    Create a shareable embedding package for the team.
    
    This function prepares the embedding model for sharing via:
    1. Git LFS (Large File Storage)
    2. External storage (Google Drive, Dropbox, etc.)
    3. Package registry
    
    Returns:
        Path to the created package
    """
    manager = SharedEmbeddingManager()
    
    # Ensure model is available
    if not manager.is_model_available():
        manager.download_or_setup_model()
    
    # Create package directory
    package_dir = Path("team_embeddings_package")
    package_dir.mkdir(exist_ok=True)
    
    # Copy model files
    model_package_dir = package_dir / "model"
    if model_package_dir.exists():
        shutil.rmtree(model_package_dir)
    
    shutil.copytree(manager.model_path, model_package_dir)
    
    # Create package metadata
    package_info = {
        "model_name": manager.config["model_name"],
        "model_version": manager.config["model_version"],
        "description": "Team-shared embedding model for consistent behavior",
        "created_by": os.getenv("USER", "unknown"),
        "instructions": {
            "setup": "Run: python -m finanlyzeos_chatbot.shared_embeddings setup",
            "verify": "Run: python -m finanlyzeos_chatbot.shared_embeddings verify"
        },
        "files": [str(f.relative_to(package_dir)) for f in package_dir.rglob("*") if f.is_file()]
    }
    
    with open(package_dir / "package_info.json", 'w') as f:
        json.dump(package_info, f, indent=2)
    
    # Create setup script
    setup_script = package_dir / "setup_shared_embeddings.py"
    setup_script.write_text('''#!/usr/bin/env python3
"""Setup script for shared team embeddings."""

import shutil
from pathlib import Path

def main():
    """Setup shared embeddings from package."""
    package_dir = Path(__file__).parent
    model_dir = package_dir / "model"
    
    if not model_dir.exists():
        print("❌ Model directory not found in package")
        return
    
    # Setup target directory
    target_dir = Path(".embeddings_cache") / "all-MiniLM-L6-v2-v1.0"
    target_dir.parent.mkdir(exist_ok=True)
    
    if target_dir.exists():
        print("🔄 Removing existing model...")
        shutil.rmtree(target_dir)
    
    print("📦 Installing shared embedding model...")
    shutil.copytree(model_dir, target_dir)
    
    print("✅ Shared embedding model installed successfully!")
    print(f"📍 Location: {target_dir}")

if __name__ == "__main__":
    main()
''')
    
    # Create README
    readme_content = f"""# Team Shared Embedding Model

This package contains the shared embedding model for consistent behavior across all team members.

## Model Information
- **Model**: {manager.config['model_name']}
- **Version**: {manager.config['model_version']}
- **Size**: ~90MB

## Quick Setup

### Option 1: Automatic Setup
```bash
python setup_shared_embeddings.py
```

### Option 2: Manual Setup
1. Copy the `model/` directory to `.embeddings_cache/all-MiniLM-L6-v2-v1.0/`
2. Verify the setup by running your chatbot

## Verification
The model should be automatically detected and used by the chatbot.

## Sharing Options

### Option A: Git LFS (Recommended)
```bash
# Install Git LFS
git lfs install

# Track the model files
git lfs track "team_embeddings_package/model/**/*"
git add .gitattributes
git add team_embeddings_package/
git commit -m "Add shared embedding model via Git LFS"
git push
```

### Option B: External Storage
1. Upload `team_embeddings_package/` to Google Drive/Dropbox
2. Share the link with team members
3. Team members download and run `setup_shared_embeddings.py`

### Option C: Package Registry (Advanced)
Create a private package and distribute via pip/conda.

## File Structure
```
team_embeddings_package/
├── model/                  # The actual embedding model files
├── package_info.json      # Package metadata
├── setup_shared_embeddings.py  # Setup script
└── README.md              # This file
```
"""
    
    (package_dir / "README.md").write_text(readme_content)
    
    # Create .gitattributes for Git LFS
    gitattributes_content = """# Git LFS tracking for embedding model files
team_embeddings_package/model/**/* filter=lfs diff=lfs merge=lfs -text
*.bin filter=lfs diff=lfs merge=lfs -text
*.safetensors filter=lfs diff=lfs merge=lfs -text
*.pt filter=lfs diff=lfs merge=lfs -text
*.pth filter=lfs diff=lfs merge=lfs -text
"""
    
    (package_dir / ".gitattributes").write_text(gitattributes_content)
    
    print(f"📦 Team embedding package created at: {package_dir}")
    print(f"📊 Package size: ~90MB")
    print("\n🚀 Next steps:")
    print("1. Choose a sharing method from the README")
    print("2. Share with your team")
    print("3. Team members run the setup script")
    
    return package_dir


def setup_shared_embeddings() -> None:
    """Setup shared embeddings on this machine."""
    manager = SharedEmbeddingManager()
    
    if manager.is_model_available():
        print("✓ Shared embedding model already available")
        info = manager.get_model_info()
        print(f"Model: {info.get('model_name', 'unknown')}")
        print(f"Version: {info.get('model_version', 'unknown')}")
        return
    
    print("Setting up shared embedding model...")
    manager.download_or_setup_model()
    
    if manager.verify_model_integrity():
        print("✓ Shared embedding model setup complete!")
    else:
        print("✗ Model setup failed verification")


def verify_shared_embeddings() -> bool:
    """Verify shared embeddings are working correctly."""
    manager = SharedEmbeddingManager()
    
    if not manager.is_model_available():
        print("✗ Shared embedding model not found")
        return False
    
    try:
        # Test loading the model
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(str(manager.model_path))
        
        # Test encoding
        test_text = "Apple revenue growth"
        embedding = model.encode([test_text])
        
        print("✓ Shared embedding model verification successful")
        print(f"Model path: {manager.model_path}")
        print(f"Embedding dimension: {embedding.shape[1]}")
        print(f"Test encoding: {embedding[0][:5]}...")  # First 5 dimensions
        
        return True
        
    except Exception as e:
        print(f"✗ Shared embedding model verification failed: {e}")
        return False


# Integration with existing RAG system
def get_shared_embedding_model():
    """Get the shared embedding model for use in RAG system."""
    manager = SharedEmbeddingManager()
    
    if not manager.is_model_available():
        print("⚠️ Shared embedding model not found, setting up...")
        manager.download_or_setup_model()
    
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(str(manager.model_path))
    except Exception as e:
        LOGGER.warning(f"Failed to load shared embedding model: {e}")
        # Fallback to default behavior
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python shared_embeddings.py [setup|verify|package]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        setup_shared_embeddings()
    elif command == "verify":
        verify_shared_embeddings()
    elif command == "package":
        create_team_embedding_package()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: setup, verify, package")
