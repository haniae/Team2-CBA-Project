"""Extract all tickers from database to create S&P 1500 file."""

import sys
from pathlib import Path
import sqlite3

def find_database():
    """Find the database file."""
    project_root = Path(__file__).parent
    possible_dbs = [
        project_root / "data" / "financials.db",
        project_root / "financials.db",
        project_root / "data" / "*.db",
    ]
    
    # Search for .db files
    db_files = list(project_root.rglob("*.db"))
    
    if db_files:
        print("Found database files:")
        for db in db_files[:5]:
            print(f"  - {db}")
        return db_files[0] if db_files else None
    
    return None

def extract_tickers_from_db(db_path):
    """Extract all unique tickers from database."""
    if not db_path or not db_path.exists():
        return []
    
    print(f"\nExtracting tickers from: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all unique tickers
        cursor.execute("SELECT DISTINCT ticker FROM financial_facts WHERE ticker IS NOT NULL ORDER BY ticker")
        tickers = [row[0].upper() for row in cursor.fetchall() if row[0]]
        
        conn.close()
        
        print(f"Found {len(tickers)} unique tickers in database")
        return sorted(tickers)
    except Exception as e:
        print(f"Error reading database: {e}")
        return []

def create_sp1500_file(tickers, output_path):
    """Create S&P 1500 file from tickers."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for ticker in tickers:
            f.write(f"{ticker}\n")
    
    print(f"\nCreated S&P 1500 file: {output_path}")
    print(f"Total tickers: {len(tickers)}")

def main():
    """Main function."""
    print("=" * 80)
    print("Extract Tickers from Database")
    print("=" * 80)
    
    # Find database
    db_path = find_database()
    
    if not db_path:
        print("\n[INFO] No database file found")
        print("If you have S&P 1500 ticker list file, place it at:")
        print("  data/tickers/universe_sp1500.txt")
        return
    
    # Extract tickers
    tickers = extract_tickers_from_db(db_path)
    
    if not tickers:
        print("\n[INFO] No tickers found in database")
        return
    
    # Check if it's S&P 1500
    if len(tickers) >= 1400:
        print(f"\n[SUCCESS] Found {len(tickers)} tickers - looks like S&P 1500!")
        
        # Create file
        output_path = Path(__file__).parent / "data" / "tickers" / "universe_sp1500.txt"
        create_sp1500_file(tickers, output_path)
        
        print("\n[SUCCESS] S&P 1500 file created!")
        print("Now run: python test_all_sp1500_tickers.py")
    else:
        print(f"\n[INFO] Found {len(tickers)} tickers (less than 1500)")
        print("This might be S&P 500 or a subset")
        print("\nIf you want to create S&P 1500 file anyway, uncomment the code below")

if __name__ == "__main__":
    main()

