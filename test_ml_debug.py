"""Quick debug test to see what responses we're actually getting."""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.config import load_settings

# Test a few key prompts
TEST_PROMPTS = [
    "Forecast Apple's revenue",
    "Forecast Apple's revenue using LSTM",
    "Predict Microsoft's revenue using Prophet",
    "What's Tesla's revenue forecast?",
    "Forecast Apple's revenue using GRU",
    "Forecast Apple's revenue using Transformer",
    "Forecast Apple's revenue using ETS",
    "Forecast Apple's revenue using ensemble methods",
    "Forecast Apple's revenue using the best ML model",
]

def main():
    print("=" * 80)
    print("ML FORECAST DEBUG TEST")
    print("=" * 80)
    
    settings = load_settings()
    bot = FinanlyzeOSChatbot.create(settings)
    
    for prompt in TEST_PROMPTS:
        print(f"\n{'='*80}")
        print(f"PROMPT: {prompt}")
        print(f"{'='*80}\n")
        
        try:
            response = bot.ask(prompt)
            
            if response:
                print(f"Response Length: {len(response)} chars")
                print(f"\nResponse Preview (first 1000 chars):")
                print("-" * 80)
                print(response[:1000])
                print("-" * 80)
                
                # Check for key indicators
                response_lower = response.lower()
                has_forecast = "forecast" in response_lower or "predict" in response_lower
                has_model = any(m in response_lower for m in ['prophet', 'arima', 'lstm', 'gru', 'transformer', 'ets', 'ensemble'])
                has_values = "$" in response and any(c in response for c in ['B', 'M', 'K'])
                has_snapshot = "growth snapshot" in response_lower or "margin snapshot" in response_lower
                
                print(f"\nIndicators:")
                print(f"  Has 'forecast'/'predict': {has_forecast}")
                print(f"  Has model name: {has_model}")
                print(f"  Has $ values: {has_values}")
                print(f"  Has snapshot (BAD): {has_snapshot}")
            else:
                print("[ERROR] No response generated")
        except Exception as e:
            print(f"[ERROR] Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

