"""Show an actual chatbot response for demonstration."""

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot

settings = load_settings()
chatbot = BenchmarkOSChatbot.create(settings)

print("=" * 80)
print("EXAMPLE: Natural Language Question")
print("=" * 80)
print()
print("Question: What is Microsoft's revenue and how has it grown?")
print()
print("-" * 80)
print()

response = chatbot.ask("What is Microsoft's revenue and how has it grown?")
print(response)

print()
print()
print("=" * 80)
print("EXAMPLE: Comparison Question")
print("=" * 80)
print()
print("Question: Is Tesla more profitable than Ford?")
print()
print("-" * 80)
print()

response = chatbot.ask("Is Tesla more profitable than Ford?")
try:
    print(response)
except UnicodeEncodeError:
    print(response.encode('ascii', 'replace').decode('ascii'))

