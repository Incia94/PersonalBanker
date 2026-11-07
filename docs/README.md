# Ledgerly documentation

Ledgerly is a local banking-assistant prototype using fictional INR account and
transaction data. Start at the guide that matches what you need:

- [Architecture](Architecture.md) — components, agent routing, tool calls, and
  memory flow.
- [API endpoints](API-Endpoints.md) — mock FastAPI routes, parameters, and
  request/response examples.
- [Prototype working](Prototype-Working.md) — setup, configuration, current
  capabilities, limitations, and tests.
- [Demo walkthrough](Demo-Walkthrough.md) — a practical run-through, including
  the ₹15,000 savings-goal example.

The project [README](../README.md) is the quick start. From the project root,
install dependencies, start Ollama and FastAPI, and then launch Streamlit:

```sh
python3 -m pip install -r requirements.txt
ollama pull qwen3:8b
uvicorn backend.api:app --reload
```

In another terminal, run:

```sh
streamlit run streamlit_app.py
```

Use Python 3.10 or newer. The mock API's interactive OpenAPI page is available
at `http://127.0.0.1:8000/docs` while the API is running.
