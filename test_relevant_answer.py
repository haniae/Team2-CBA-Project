"""Test that the chatbot now gives relevant answers to specific questions."""

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot

settings = load_settings()
chatbot = BenchmarkOSChatbot.create(settings)

print("=" * 80)
print("TESTING RELEVANT ANSWERS - AFTER FIX")
print("=" * 80)
print()

# The exact query from the user's screenshot
query = "How has Apple's revenue changed over time?"

print(f"QUESTION: {query}")
print()
print("-" * 80)
print()

response = chatbot.ask(query)

try:
    print(response)
except UnicodeEncodeError:
    print(response.encode('ascii', 'replace').decode('ascii'))

print()
print()
print("-" * 80)
print("ANALYSIS:")
print("-" * 80)

# Check if the response is relevant
checks = {
    "Mentions revenue specifically": "revenue" in response.lower(),
    "Mentions growth/change": any(word in response.lower() for word in ["growth", "grew", "increased", "decreased", "changed", "cagr", "%"]),
    "NOT a full KPI dump": response.count("$") < 8,  # Full dump has 9+ dollar amounts
    "Has proper formatting": "**" in response or "##" in response,
    "Has sources": "sec.gov" in response.lower(),
    "Focuses on answer": len(response) < 2000,  # Not a massive data dump
}

for check, passed in checks.items():
    status = "[✓]" if passed else "[✗]"
    print(f"  {status} {check}")

passed_count = sum(1 for p in checks.values() if p)
total_count = len(checks)

print()
if passed_count >= 5:
    print(f"[SUCCESS] {passed_count}/{total_count} checks passed - Answer is relevant!")
elif passed_count >= 3:
    print(f"[PARTIAL] {passed_count}/{total_count} checks passed - Some improvement needed")
else:
    print(f"[FAIL] {passed_count}/{total_count} checks passed - Still not relevant")

# Also test a few more queries
print()
print()
print("=" * 80)
print("ADDITIONAL TEST QUERIES")
print("=" * 80)

additional_queries = [
    "What is Microsoft's profit margin?",
    "Is Tesla profitable?",
    "How much cash does Amazon have?",
]

for query in additional_queries:
    print()
    print(f"\nQ: {query}")
    response = chatbot.ask(query)
    
    # Check if it's focused
    is_focused = (
        response.count("$") < 5 and  # Not dumping all metrics
        len(response) < 1500 and  # Not too long
        any(word in query.lower() for word in response.lower().split())  # Mentions something from query
    )
    
    status = "[FOCUSED]" if is_focused else "[DUMP]"
    print(f"   {status} Response length: {len(response)} chars, $ signs: {response.count('$')}")

