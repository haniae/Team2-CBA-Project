"""Check JPM source attribution in detail."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import Settings

settings = Settings(database_path=Path("data/sqlite/benchmarkos_chatbot.sqlite3"))
chatbot = BenchmarkOSChatbot.create(settings)

query = "show comprehensive financial summary for JPMorgan Chase & Co"
chatbot.last_structured_response = {}
response = chatbot.ask(query)

dashboard = chatbot.last_structured_response.get("dashboard")
payload = dashboard.get("payload", {})
sources = payload.get("sources", [])

print("JPM - Sources without URLs or calculations:")
print("="*80)

for s in sources:
    has_url = bool(s.get("url") or s.get("urls"))
    has_calc = bool(s.get("calculation"))
    source_type = s.get("source")
    
    if not has_url and not has_calc and source_type not in ["IMF", "derived"]:
        print(f"\nMetric: {s.get('metric')}")
        print(f"  Label: {s.get('label')}")
        print(f"  Source: {source_type}")
        print(f"  Value: {s.get('value')}")
        print(f"  Has URL: {has_url}")
        print(f"  Has Calculation: {has_calc}")

print("\n" + "="*80)
print("Checking if these should be 'derived':")
print("="*80)

# Check actual source types
import sqlite3
conn = sqlite3.connect('data/sqlite/benchmarkos_chatbot.sqlite3')
for metric in ['net_margin', 'profit_margin', 'revenue_cagr']:
    cursor = conn.execute("""
        SELECT source, value
        FROM metric_snapshots
        WHERE ticker = 'JPM' AND metric = ?
        ORDER BY end_year DESC
        LIMIT 1
    """, (metric,))
    row = cursor.fetchone()
    if row:
        print(f"{metric:20} -> source={row[0]}, value={row[1]}")
conn.close()

