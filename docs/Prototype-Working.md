# Prototype working

## What is implemented

- A Streamlit chat interface accepts conversational questions and displays
  responses from a banking assistant.
- A LangGraph Planner backed by a local Ollama model selects tools for
  transaction analysis, recommendations, alerts, or savings planning.
- Specialist calculations are deterministic Python code and operate on
  fictional INR transaction and account data.
- The FastAPI service exposes mock banking endpoints for profile information,
  transactions, spending analysis, recommendations, alerts, and savings plans.
- SQLite stores conversation messages and savings goals. A new conversation in
  the UI gets a separate conversation ID.
- The UI can show the tools selected during the most recent orchestration.

## Requirements

- Python 3.10 or newer.
- Ollama running locally with a tool-capable model available. The default is
  `qwen3:8b`.
- Dependencies listed in the repository's `requirements.txt`.

## Run locally

From the project root:

```sh
python3 -m pip install -r requirements.txt
ollama pull qwen3:8b
```

Start the mock API in one terminal:

```sh
uvicorn backend.api:app --reload
```

Start the chat UI in another terminal:

```sh
streamlit run streamlit_app.py
```

Open the Streamlit URL printed in the terminal. The API's interactive
documentation is at `http://127.0.0.1:8000/docs`.

## Configuration

The application supports these environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `qwen3:8b` | Local Ollama model used by the Planner. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL. |
| `BANK_API_URL` | `http://127.0.0.1:8000` | FastAPI base URL used by the client. |

For example, set an alternative model before starting Streamlit:

```sh
export OLLAMA_MODEL=qwen3:8b
```

## Mock profile and goal calculation

The sample profile in `backend/mock_api.py` has monthly income of ₹100,000 and
fixed expenses totaling ₹36,000. The transaction history in
`data/transactions.json` includes September and October 2026. A savings plan
uses the chosen reference month's variable spending to estimate available
funds:

```text
estimated available = monthly income - fixed expenses - observed variable spend
```

For the October 2026 sample and a ₹15,000 target, estimated available funds are
₹12,817, so the initial gap is ₹2,183. The planner suggests cuts to selected
flexible categories and reports whether those cuts cover the gap. These are
estimates based on mock data, not a guarantee of savings.

## Memory

The Streamlit app writes conversation messages and the Planner's savings-plan
tool writes goals to `data/ledgerly.sqlite`. The database is created
automatically. Chat history is loaded for the current conversation and passed
to the Planner on the next turn. Graph checkpoint state is not persisted.

## Tests

Run the offline unit tests with Python 3.10 or newer:

```sh
python3 -m unittest discover -s tests -v
```

The tests use a fake tool-calling chat model and FastAPI's in-process test
client, so they do not require a running Ollama server or FastAPI process.

## Prototype limitations

- The account, recurring expenses, limits, and transactions are sample data;
  no real banking system is connected.
- Tool choice and conversational wording depend on the configured local model.
- Alert outputs are review prompts, not confirmed fraud findings.
- Savings calculations use recent historical spending and simplified
  assumptions; they are not financial advice.
- SQLite transcript persistence does not provide durable LangGraph checkpoints.
