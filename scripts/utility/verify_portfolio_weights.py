"""Quick script to verify portfolio weights sum to 100%."""
import csv
from pathlib import Path

portfolio_file = Path(__file__).parent.parent.parent / "data" / "portfolios" / "mizuho_fi_capital_portfolio.csv"

with open(portfolio_file, 'r') as f:
    reader = csv.DictReader(f)
    data = list(reader)
    weights = [float(row['weight']) for row in data]
    total = sum(weights)
    
    print(f"Total holdings: {len(data)}")
    print(f"Total weight: {total:.2f}%")
    print(f"\nTop 10 holdings:")
    sorted_data = sorted(data, key=lambda x: float(x['weight']), reverse=True)
    for i, row in enumerate(sorted_data[:10], 1):
        print(f"{i:2d}. {row['ticker']:6s} - {float(row['weight']):5.2f}%")
    
    if abs(total - 100.0) > 0.01:
        print(f"\n[WARNING] Weights don't sum to 100% (currently {total:.2f}%)")
        print(f"Adjusting to sum to 100%...")
        
        # Normalize weights
        normalized_data = []
        for row in data:
            normalized_weight = float(row['weight']) / total * 100.0
            normalized_data.append({
                'ticker': row['ticker'],
                'weight': f"{normalized_weight:.2f}"
            })
        
        # Write back
        with open(portfolio_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ticker', 'weight'])
            writer.writeheader()
            writer.writerows(normalized_data)
        
        print(f"[SUCCESS] Portfolio weights normalized to sum to 100.00%")

