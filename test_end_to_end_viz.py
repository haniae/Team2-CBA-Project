"""End-to-end test: chatbot -> chart generation -> web rendering."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.config import Settings
import re

def test_end_to_end():
    """Test complete flow from query to chart rendering."""
    print("=" * 60)
    print("END-TO-END VISUALIZATION TEST")
    print("=" * 60)
    
    settings = Settings()
    bot = FinanlyzeOSChatbot.create(settings)
    
    test_queries = [
        "plot apple microsoft nvidia revenue over time",
        "show me a bar chart of AAPL, MSFT, GOOGL revenue",
        "create a pie chart of tech company revenue"
    ]
    
    all_passed = True
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: {query}")
        print(f"{'='*60}")
        
        try:
            reply = bot.ask(query)
            
            # Check 1: Reply contains chart reference
            chart_match = re.search(r'!\[.*?\]\(([^)]+)\)', reply)
            if not chart_match:
                print(f"[FAIL] No chart URL in reply")
                print(f"Reply: {reply[:200]}...")
                all_passed = False
                continue
            
            chart_url = chart_match.group(1)
            print(f"[OK] Chart URL found: {chart_url}")
            
            # Check 2: URL format is correct
            if not (chart_url.endswith('.html') or chart_url.endswith('.png')):
                print(f"[FAIL] URL format incorrect: {chart_url}")
                all_passed = False
                continue
            print(f"[OK] URL format correct")
            
            # Check 3: Extract chart ID and verify file exists
            chart_id = chart_url.split('/')[-1].replace('.html', '').replace('.png', '')
            chart_path_html = Path('src/charts') / f"{chart_id}.html"
            chart_path_png = Path('src/charts') / f"{chart_id}.png"
            
            if chart_path_html.exists():
                print(f"[OK] HTML chart file exists: {chart_path_html}")
                file_size = chart_path_html.stat().st_size
                print(f"[OK] File size: {file_size} bytes")
                
                # Check content
                content = chart_path_html.read_text(encoding='utf-8')
                if 'plotly' in content.lower():
                    print(f"[OK] File contains Plotly code")
                else:
                    print(f"[WARN] File does not contain Plotly code")
            elif chart_path_png.exists():
                print(f"[OK] PNG chart file exists: {chart_path_png}")
                file_size = chart_path_png.stat().st_size
                print(f"[OK] File size: {file_size} bytes")
            else:
                print(f"[FAIL] Chart file does NOT exist")
                print(f"  Looked for: {chart_path_html} or {chart_path_png}")
                all_passed = False
                continue
            
            # Check 4: Reply has explanation
            if len(reply) > 100:
                print(f"[OK] Reply has explanation (length: {len(reply)})")
            else:
                print(f"[WARN] Reply is short (length: {len(reply)})")
            
            print(f"[PASS] Test passed for: {query}")
            
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print(f"{'='*60}")
    
    return all_passed

if __name__ == "__main__":
    success = test_end_to_end()
    sys.exit(0 if success else 1)

