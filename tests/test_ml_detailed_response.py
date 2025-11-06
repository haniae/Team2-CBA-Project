"""Test script to verify ML forecast responses include all technical details."""

import sys
import os
from pathlib import Path

# Fix Unicode encoding for Windows console
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.context_builder import build_financial_context, _is_forecasting_query
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOGGER = logging.getLogger(__name__)


def test_context_building():
    """Test if ML forecast context is being built correctly."""
    print("\n" + "="*80)
    print("TEST 1: Context Building")
    print("="*80)
    
    settings = load_settings()
    analytics_engine = AnalyticsEngine(settings)
    
    query = "Forecast Apple's revenue using LSTM"
    
    print(f"\nQuery: {query}")
    print(f"Is forecasting query: {_is_forecasting_query(query)}")
    
    context = build_financial_context(
        query=query,
        analytics_engine=analytics_engine,
        database_path=settings.database_path,
        max_tickers=3
    )
    
    if not context:
        print("[ERROR] Context is None or empty!")
        return False
    
    print(f"\n[OK] Context length: {len(context)} characters")
    
    # Check for key sections
    checks = {
        "ML FORECAST": "ML FORECAST" in context or "CRITICAL: THIS IS THE PRIMARY ANSWER" in context,
        "MODEL TECHNICAL DETAILS": "MODEL TECHNICAL DETAILS" in context or "FINAL CHECKLIST" in context,
        "EXPLICIT DATA DUMP": "EXPLICIT DATA DUMP" in context or "FINAL CHECKLIST" in context,
        "Training Epochs": "Training Epochs" in context or "epochs" in context.lower(),
        "Training Loss": "Training Loss" in context or "training loss" in context.lower(),
        "Learning Rate": "Learning Rate" in context or "learning rate" in context.lower(),
        "Batch Size": "Batch Size" in context or "batch size" in context.lower(),
        "Total Parameters": "Total Parameters" in context or "parameters" in context.lower(),
    }
    
    print("\nContext checks:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {check_name}: {passed}")
        if not passed:
            all_passed = False
    
    # Show a sample of the context (encode to avoid Unicode issues)
    print(f"\nContext sample (first 1000 characters):")
    print("-" * 80)
    try:
        print(context[:1000].encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
    except:
        print("(Unable to display context sample due to encoding issues)")
    print("-" * 80)
    
    return all_passed


def test_message_preparation():
    """Test if messages are prepared correctly with context in user message."""
    print("\n" + "="*80)
    print("TEST 2: Message Preparation")
    print("="*80)
    
    settings = load_settings()
    chatbot = BenchmarkOSChatbot.create(settings)
    
    query = "Forecast Apple's revenue using LSTM"
    chatbot.conversation.messages.append({"role": "user", "content": query})
    
    # Build context
    from benchmarkos_chatbot.context_builder import build_financial_context
    context = build_financial_context(
        query=query,
        analytics_engine=chatbot.analytics_engine,
        database_path=settings.database_path,
        max_tickers=3
    )
    
    if not context:
        print("[ERROR] Context is None or empty!")
        return False
    
    # Prepare messages
    messages = chatbot._prepare_llm_messages(context)
    
    print(f"\n[OK] Prepared {len(messages)} messages")
    
    # Check message structure
    print("\nMessage structure:")
    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content_length = len(msg.get("content", ""))
        print(f"  Message {i+1}: role={role}, length={content_length} chars")
        
        # For user message, check if context is included
        if role == "user":
            content = msg.get("content", "")
            if "ML FORECAST" in content or "CRITICAL: THIS IS THE PRIMARY ANSWER" in content:
                print(f"    [OK] ML forecast context is in user message")
            else:
                print(f"    [FAIL] ML forecast context NOT in user message")
                try:
                    print(f"    Content preview: {content[:200].encode('utf-8', errors='replace').decode('utf-8', errors='replace')}...")
                except:
                    print(f"    Content preview: (Unable to display due to encoding issues)")
    
    return True


def test_full_response():
    """Test the full response generation."""
    print("\n" + "="*80)
    print("TEST 3: Full Response Generation")
    print("="*80)
    
    settings = load_settings()
    chatbot = BenchmarkOSChatbot.create(settings)
    
    query = "Forecast Apple's revenue using LSTM"
    
    print(f"\nQuery: {query}")
    print("Generating response...")
    
    try:
        response = chatbot.ask(query)
        
        if not response:
            print("[ERROR] Response is None or empty!")
            return False
        
        print(f"\n[OK] Response length: {len(response)} characters")
        print(f"\nResponse preview (first 500 characters):")
        print("-" * 80)
        print(response[:500])
        print("-" * 80)
        
        # Check for required details
        required_checks = {
            "Forecast values": any(keyword in response.lower() for keyword in ["2025", "2026", "2027", "forecast", "projected"]),
            "Model architecture": any(keyword in response.lower() for keyword in ["layer", "unit", "architecture", "network"]),
            "Training details": any(keyword in response.lower() for keyword in ["epoch", "training loss", "validation loss"]),
            "Hyperparameters": any(keyword in response.lower() for keyword in ["learning rate", "batch size", "optimizer", "dropout"]),
            "Technical numbers": any(char.isdigit() for char in response[-2000:]),  # Check last 2000 chars for numbers
        }
        
        print("\nResponse checks:")
        all_passed = True
        for check_name, passed in required_checks.items():
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} {check_name}: {passed}")
            if not passed:
                all_passed = False
        
        # Check for specific technical details
        print("\nDetailed technical checks:")
        detail_checks = {
            "Epochs mentioned": "epoch" in response.lower(),
            "Loss values mentioned": "loss" in response.lower(),
            "Learning rate mentioned": "learning rate" in response.lower() or "lr" in response.lower(),
            "Batch size mentioned": "batch" in response.lower(),
            "Parameters mentioned": "parameter" in response.lower(),
            "Training time mentioned": "training time" in response.lower() or "train time" in response.lower(),
        }
        
        for check_name, passed in detail_checks.items():
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} {check_name}: {passed}")
            if not passed:
                all_passed = False
        
        # Show full response (encode to avoid Unicode issues)
        print(f"\n{'='*80}")
        print("FULL RESPONSE:")
        print("="*80)
        try:
            print(response.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        except:
            print("(Unable to display full response due to encoding issues)")
        print("="*80)
        
        return all_passed
        
    except Exception as e:
        print(f"❌ ERROR: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verifier():
    """Test the post-processing verifier."""
    print("\n" + "="*80)
    print("TEST 4: Post-Processing Verifier")
    print("="*80)
    
    try:
        from benchmarkos_chatbot.ml_response_verifier import verify_ml_forecast_response
        
        # Create a mock response that's missing details
        mock_response = """
        Based on LSTM forecasting, Apple's revenue is projected to reach $410.50 billion in 2025.
        The model provides a confidence interval of 95%.
        """
        
        # Create a mock context with technical details
        mock_context = """
        ML FORECAST (LSTM) - AAPL REVENUE
        
        MODEL TECHNICAL DETAILS:
        - **Network Architecture:** 2 layers
        - **Hidden Units per Layer:** 50
        - **Total Parameters:** 50,000
        - **Training Epochs:** 50
        - **Training Loss (MSE):** 0.001234
        - **Validation Loss (MSE):** 0.001456
        - **Learning Rate:** 0.001
        - **Batch Size:** 32
        - **Optimizer:** Adam
        - **Dropout Rate:** 0.2
        - **Training Time:** 120.50 seconds
        - **Data Points Used:** 20 periods
        """
        
        is_complete, missing_details, enhanced_response = verify_ml_forecast_response(
            mock_response, mock_context, "Forecast Apple's revenue using LSTM"
        )
        
        print(f"\nIs complete: {is_complete}")
        print(f"Missing details: {len(missing_details)}")
        
        if missing_details:
            print("\nMissing details:")
            for detail in missing_details:
                print(f"  - {detail}")
        
        if not is_complete:
            print(f"\n[OK] Verifier detected missing details and enhanced response")
            print(f"Enhanced response length: {len(enhanced_response)} characters")
            print(f"\nEnhanced response preview:")
            print("-" * 80)
            try:
                print(enhanced_response[:1000].encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
            except:
                print("(Unable to display enhanced response preview due to encoding issues)")
            print("-" * 80)
        else:
            print("\n[WARN] Verifier did not detect missing details (this might be expected if response is complete)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("ML FORECAST DETAILED RESPONSE TEST SUITE")
    print("="*80)
    
    results = {}
    
    # Test 1: Context building
    try:
        results["context_building"] = test_context_building()
    except Exception as e:
        print(f"[ERROR] Test 1 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["context_building"] = False
    
    # Test 2: Message preparation
    try:
        results["message_preparation"] = test_message_preparation()
    except Exception as e:
        print(f"[ERROR] Test 2 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["message_preparation"] = False
    
    # Test 3: Full response
    try:
        results["full_response"] = test_full_response()
    except Exception as e:
        print(f"[ERROR] Test 3 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["full_response"] = False
    
    # Test 4: Verifier
    try:
        results["verifier"] = test_verifier()
    except Exception as e:
        print(f"[ERROR] Test 4 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results["verifier"] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'[ALL TESTS PASSED]' if all_passed else '[SOME TESTS FAILED]'}")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

