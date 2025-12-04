#!/usr/bin/env python3
"""
FRED API Setup Script

This script helps you set up the FRED API key for the FinanlyzeOS chatbot.
It will:
1. Check if fredapi is installed
2. Guide you to get an API key
3. Test the API connection
4. Save the key to .env file
"""

import os
import sys
from pathlib import Path

def check_fredapi_installed():
    """Check if fredapi package is installed."""
    try:
        import fredapi
        print("✅ fredapi package is installed")
        return True
    except ImportError:
        print("❌ fredapi package is not installed")
        print("   Installing...")
        os.system(f"{sys.executable} -m pip install fredapi>=0.5.0")
        try:
            import fredapi
            print("✅ fredapi package installed successfully")
            return True
        except ImportError:
            print("❌ Failed to install fredapi")
            return False

def get_api_key_from_user():
    """Prompt user for FRED API key."""
    print("\n" + "="*60)
    print("FRED API Key Setup")
    print("="*60)
    print("\nTo get a free FRED API key:")
    print("1. Visit: https://fred.stlouisfed.org/docs/api/api_key.html")
    print("2. Click 'Request API Key'")
    print("3. Fill out the form (takes ~2 minutes)")
    print("4. Copy the API key from your email")
    print("\n" + "-"*60)
    
    api_key = input("\nEnter your FRED API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("\n⚠️  No API key provided. FRED data will not be available.")
        print("   You can set it later by:")
        print("   1. Creating a .env file with: FRED_API_KEY=your_key")
        print("   2. Or setting environment variable: export FRED_API_KEY=your_key")
        return None
    
    return api_key

def test_fred_connection(api_key: str) -> bool:
    """Test FRED API connection with the provided key."""
    print("\n" + "="*60)
    print("Testing FRED API Connection...")
    print("="*60)
    
    try:
        from fredapi import Fred
        
        print("Initializing FRED client...")
        fred = Fred(api_key=api_key)
        
        print("Fetching test data (GDP)...")
        # Try to fetch a simple series
        gdp_data = fred.get_series('GDP', limit=1)
        
        if gdp_data is not None and not gdp_data.empty:
            latest_value = gdp_data.iloc[-1]
            latest_date = gdp_data.index[-1]
            print(f"✅ Connection successful!")
            print(f"   Latest GDP: ${latest_value:,.0f}B (as of {latest_date})")
            return True
        else:
            print("⚠️  Connection successful but no data returned")
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nPossible issues:")
        print("  - Invalid API key")
        print("  - Network connectivity")
        print("  - FRED API service temporarily unavailable")
        return False

def save_to_env_file(api_key: str):
    """Save API key to .env file."""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    # Read existing .env if it exists
    existing_content = ""
    if env_path.exists():
        existing_content = env_path.read_text()
    
    # Check if FRED_API_KEY already exists
    if "FRED_API_KEY" in existing_content:
        print("\n⚠️  .env file already contains FRED_API_KEY")
        response = input("   Do you want to update it? (y/n): ").strip().lower()
        if response != 'y':
            print("   Skipping .env update")
            return
        
        # Update existing key
        lines = existing_content.split('\n')
        updated_lines = []
        for line in lines:
            if line.startswith('FRED_API_KEY='):
                updated_lines.append(f'FRED_API_KEY={api_key}')
            else:
                updated_lines.append(line)
        env_path.write_text('\n'.join(updated_lines))
    else:
        # Append to existing .env or create new
        if existing_content and not existing_content.endswith('\n'):
            existing_content += '\n'
        existing_content += f'\n# FRED API Key (added by setup_fred_api.py)\nFRED_API_KEY={api_key}\n'
        env_path.write_text(existing_content)
    
    print(f"✅ API key saved to {env_path.absolute()}")
    print("   Make sure .env is in .gitignore (it should be by default)")

def main():
    """Main setup function."""
    print("="*60)
    print("FRED API Setup for FinanlyzeOS Chatbot")
    print("="*60)
    
    # Check if fredapi is installed
    if not check_fredapi_installed():
        print("\n❌ Setup failed: fredapi package not available")
        sys.exit(1)
    
    # Get API key from user
    api_key = get_api_key_from_user()
    
    if not api_key:
        print("\n⚠️  Setup incomplete - no API key provided")
        print("   FRED data will not be available until you set FRED_API_KEY")
        sys.exit(0)
    
    # Test connection
    if not test_fred_connection(api_key):
        print("\n❌ Setup failed: Could not connect to FRED API")
        print("   Please check your API key and try again")
        sys.exit(1)
    
    # Save to .env file
    save_to_env_file(api_key)
    
    # Set environment variable for current session
    os.environ['FRED_API_KEY'] = api_key
    
    print("\n" + "="*60)
    print("✅ FRED API Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Restart your chatbot server to load the new API key")
    print("2. Test with a query like: 'What is Apple's revenue?'")
    print("3. You should see economic context from FRED in responses")
    print("\nFor more information, see: docs/guides/ENABLE_FRED_GUIDE.md")

if __name__ == "__main__":
    main()

