"""Lightweight sanity check for the chat API without running uvicorn."""

from __future__ import annotations

from fastapi.testclient import TestClient

from benchmarkos_chatbot import web


def main() -> None:
    """Issue a handful of representative prompts against the chat endpoint."""
    client = TestClient(web.app)
    prompts = [
        "compare AAPL MSFT",
        "table AAPL MSFT metrics revenue net_income",
        "scenario TSLA bull rev=+10% margin=+2%",
    ]
    for prompt in prompts:
        response = client.post("/chat", json={"prompt": prompt})
        print(prompt, response.status_code)
        print(response.json())


if __name__ == "__main__":
    main()

client = TestClient(web.app)
for prompt in [
    'compare AAPL MSFT',
    'table AAPL MSFT metrics revenue net_income',
    'scenario TSLA bull rev=+10% margin=+2%'
]:
    resp = client.post('/chat', json={'prompt': prompt})
    print(prompt, resp.status_code)
    print(resp.json())
