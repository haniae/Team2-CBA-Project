#!/usr/bin/env python3
"""
Test FRED API Connection

Quick script to test if FRED API is working correctly.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not required, but helpful

def test_fred_api():
    """Test FRED API connection and fetch sample data."""
    print("="*60)
    print("FRED API Connection Test")
    print("="*60)
    
    # Check if fredapi is installed
    try:
        from fredapi import Fred
    except ImportError:
        print("❌ fredapi package not installed")
        print("   Install with: pip install fredapi>=0.5.0")
        return False
    
    # Get API key from environment
    api_key = os.getenv('FRED_API_KEY')
    
    if not api_key:
        print("❌ FRED_API_KEY not set in environment")
        print("\nTo set it:")
        print("  1. Run: python scripts/setup_fred_api.py")
        print("  2. Or set: export FRED_API_KEY=your_key")
        print("  3. Or add to .env file: FRED_API_KEY=your_key")
        return False
    
    print(f"✅ FRED_API_KEY found: {api_key[:10]}...{api_key[-4:]}")
    
    # Test connection
    try:
        print("\nInitializing FRED client...")
        fred = Fred(api_key=api_key)
        
        # Test indicators
        test_indicators = [
            ('GDP', 'Gross Domestic Product'),
            ('UNRATE', 'Unemployment Rate'),
            ('FEDFUNDS', 'Federal Funds Rate'),
            ('CPIAUCSL', 'Consumer Price Index'),
            ('DGS10', '10-Year Treasury Rate'),
        ]
        
        print("\nFetching test indicators...")
        print("-"*60)
        
        success_count = 0
        for series_id, description in test_indicators:
            try:
                # Get the latest data (no limit, then take last value)
                data = fred.get_series(series_id)
                if data is not None and not data.empty:
                    # Get the most recent value (last in series)
                    latest_value = data.iloc[-1]
                    latest_date = data.index[-1]
                    info = fred.get_series_info(series_id)
                    units = info.get('units', 'N/A')
                    
                    print(f"✅ {description} ({series_id})")
                    print(f"   Value: {latest_value:,.2f} {units}")
                    print(f"   Date: {latest_date}")
                    success_count += 1
                else:
                    print(f"⚠️  {description} ({series_id}): No data")
            except Exception as e:
                print(f"❌ {description} ({series_id}): {e}")
        
        print("-"*60)
        print(f"\n✅ Successfully fetched {success_count}/{len(test_indicators)} indicators")
        
        if success_count > 0:
            print("\n🎉 FRED API is working correctly!")
            print("\nThe chatbot will now include economic context in responses.")
            return True
        else:
            print("\n⚠️  FRED API connection works but no data retrieved")
            return False
            
    except Exception as e:
        print(f"\n❌ FRED API connection failed: {e}")
        print("\nPossible issues:")
        print("  - Invalid API key")
        print("  - Network connectivity")
        print("  - FRED API service temporarily unavailable")
        return False

if __name__ == "__main__":
    success = test_fred_api()
    sys.exit(0 if success else 1)

