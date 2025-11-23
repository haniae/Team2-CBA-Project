#!/usr/bin/env python3
"""
Team Embedding Model Setup Script

This script creates a shareable embedding model package for your team
and provides multiple options for sharing it via GitHub.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.shared_embeddings import create_team_embedding_package, setup_shared_embeddings, verify_shared_embeddings


def main():
    """Main setup script for team embeddings."""
    print("🤖 Team Embedding Model Setup")
    print("=" * 40)
    
    print("\nThis script will help you share embedding models across your team")
    print("for consistent chatbot behavior on all laptops.")
    
    choice = input("\nWhat would you like to do?\n"
                  "1. Create shareable package (for sharing with team)\n"
                  "2. Setup from existing package (after receiving from team)\n"
                  "3. Verify current setup\n"
                  "Enter choice (1-3): ").strip()
    
    if choice == "1":
        create_package()
    elif choice == "2":
        setup_from_package()
    elif choice == "3":
        verify_setup()
    else:
        print("Invalid choice. Please run again and select 1, 2, or 3.")


def create_package():
    """Create a shareable embedding package."""
    print("\n📦 Creating Team Embedding Package...")
    print("-" * 40)
    
    try:
        package_path = create_team_embedding_package()
        
        print(f"\n✅ Package created successfully at: {package_path}")
        print("\n🚀 Sharing Options:")
        print("\n**Option A: Git LFS (Recommended for GitHub)**")
        print("1. Install Git LFS: https://git-lfs.github.io/")
        print("2. Run these commands:")
        print("   git lfs install")
        print("   git lfs track 'team_embeddings_package/model/**/*'")
        print("   git add .gitattributes")
        print("   git add team_embeddings_package/")
        print("   git commit -m 'Add shared embedding model'")
        print("   git push")
        
        print("\n**Option B: External Storage (Google Drive/Dropbox)**")
        print("1. Zip the 'team_embeddings_package' folder")
        print("2. Upload to Google Drive/Dropbox")
        print("3. Share the link with your team")
        print("4. Team members download and run setup_shared_embeddings.py")
        
        print("\n**Option C: Release Assets (GitHub Releases)**")
        print("1. Zip the 'team_embeddings_package' folder")
        print("2. Go to your GitHub repo → Releases → Create new release")
        print("3. Upload the zip as a release asset")
        print("4. Team members download from releases")
        
        print(f"\n📋 Package Info:")
        print(f"   Size: ~90MB")
        print(f"   Files: Model weights, config, setup script")
        print(f"   Compatible: All team members")
        
    except Exception as e:
        print(f"❌ Failed to create package: {e}")
        print("Make sure you have sentence-transformers installed:")
        print("pip install sentence-transformers")


def setup_from_package():
    """Setup embeddings from an existing package."""
    print("\n⚙️ Setting Up From Package...")
    print("-" * 40)
    
    # Check for package
    package_dir = Path("team_embeddings_package")
    if package_dir.exists():
        print("📦 Found local package, setting up...")
        try:
            setup_shared_embeddings()
            print("✅ Setup complete!")
        except Exception as e:
            print(f"❌ Setup failed: {e}")
    else:
        print("📥 Package not found locally. Please:")
        print("1. Download the team_embeddings_package from your team")
        print("2. Extract it to this directory")
        print("3. Run this script again")
        print("\nOr if you received a setup script, run:")
        print("python setup_shared_embeddings.py")


def verify_setup():
    """Verify the current embedding setup."""
    print("\n🔍 Verifying Embedding Setup...")
    print("-" * 40)
    
    success = verify_shared_embeddings()
    
    if success:
        print("\n🎉 Your embedding setup is working correctly!")
        print("All team members with this setup will have consistent behavior.")
    else:
        print("\n⚠️ Setup needs attention. Try:")
        print("1. Run option 2 to setup from package")
        print("2. Or contact your team for the shared package")


if __name__ == "__main__":
    main()
