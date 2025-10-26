"""Test that sources are now MANDATORY in every response."""

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot

settings = load_settings()
chatbot = BenchmarkOSChatbot.create(settings)

print("=" * 80)
print("TESTING MANDATORY SOURCES & DEPTH - AFTER FIX")
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
print("QUALITY CHECKS:")
print("-" * 80)

# Check if the response meets requirements
checks = {
    "Has Sources section (📊 Sources:)": "📊 Sources:" in response or "Sources:" in response,
    "Has clickable markdown links []()": "](" in response,
    "Has SEC.gov URLs": "sec.gov" in response.lower(),
    "Has at least 2 links": response.count("](") >= 2,
    "Links are NOT placeholders": "[URL]" not in response and "[insert" not in response.lower(),
    "Has comprehensive depth": len(response) > 800,  # Substantial analysis
    "Has section headers (###)": "###" in response or "**" in response,
    "Mentions WHY (not just WHAT)": any(word in response.lower() for word in ["driven", "because", "due to", "growth", "reason", "driver"]),
    "Has historical perspective": any(word in response for word in ["FY20", "FY19", "year", "trend"]),
    "Has forward outlook": any(word in response.lower() for word in ["expect", "future", "will", "outlook", "forecast"]),
}

passed_count = 0
for check, passed in checks.items():
    status = "[✓]" if passed else "[✗]"
    print(f"  {status} {check}")
    if passed:
        passed_count += 1

print()
print(f"RESULT: {passed_count}/{len(checks)} checks passed")

if passed_count >= 9:
    print()
    print("[SUCCESS] ✓ Response has MANDATORY sources and comprehensive depth!")
elif passed_count >= 7:
    print()
    print("[GOOD] Most requirements met, but some improvements needed")
else:
    print()
    print("[FAIL] Response still missing critical requirements")

# Show the sources section explicitly
if "Sources:" in response:
    print()
    print("-" * 80)
    print("SOURCES SECTION EXTRACTED:")
    print("-" * 80)
    sources_start = response.find("Sources:")
    sources_section = response[sources_start:]
    try:
        print(sources_section[:500])  # First 500 chars of sources
    except UnicodeEncodeError:
        print(sources_section[:500].encode('ascii', 'replace').decode('ascii'))
else:
    print()
    print("-" * 80)
    print("[ERROR] NO SOURCES SECTION FOUND!")
    print("-" * 80)

# Test a few more queries
print()
print()
print("=" * 80)
print("ADDITIONAL TEST QUERIES")
print("=" * 80)

additional_queries = [
    "What is Microsoft's profit margin?",
    "Is Tesla profitable?",
]

for query in additional_queries:
    print()
    print(f"\nQ: {query}")
    response = chatbot.ask(query)
    
    has_sources = "Sources:" in response and "sec.gov" in response.lower()
    has_depth = len(response) > 600
    has_links = response.count("](") >= 2
    
    status = "[✓ COMPLETE]" if (has_sources and has_depth and has_links) else "[✗ INCOMPLETE]"
    print(f"   {status} Length: {len(response)} chars, Links: {response.count('](')} , Sources: {'Yes' if has_sources else 'NO'}")

