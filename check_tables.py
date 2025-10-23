import sqlite3
conn = sqlite3.connect("data/sqlite/benchmarkos_chatbot.sqlite3")
print("Tables in database:")
for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
    print(f"  - {row[0]}")
conn.close()

