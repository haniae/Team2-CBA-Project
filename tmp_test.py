from benchmarkos_chatbot import web
from fastapi.testclient import TestClient

client = TestClient(web.app)
for prompt in [
    'compare AAPL MSFT',
    'table AAPL MSFT metrics revenue net_income',
    'scenario TSLA bull rev=+10% margin=+2%'
]:
    resp = client.post('/chat', json={'prompt': prompt})
    print(prompt, resp.status_code)
    print(resp.json())
