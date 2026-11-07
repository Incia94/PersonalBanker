# Agentic Ai personal Finance Advisor

A prototype solution for AI based banking assistant for a National Bank. It analyses the financial health of the account holder accross multiple transactions and autonomously and proactively gives alerts, suggestions, personalized recommendations and financial insights for better financial health.

## Tech Stack 

Streamlit for NLP Conversations through CLI
FastApi for Mock API data
SQlLite Memory Handling
Langraph - Agent Orchaestator

## Run

Install the packages from the project directory:

```sh
python3 -m pip install -r requirements.txt
```

Use Python 3.10 or newer. Install Ollama and pull the tool-capable default model:

```sh
ollama pull qwen3:8b
```

In the first terminal, start the mock FastAPI service:

```sh
uvicorn backend.api:app --reload
```

In a second terminal, start the Streamlit chat:

```sh
streamlit run streamlit_app.py
```

Open the Streamlit URL shown in your terminal. Set `OLLAMA_MODEL`,
`OLLAMA_BASE_URL`, or `BANK_API_URL` to use different local model settings or
an API endpoint.

## Commands

Start a conversation with **“Help me save Rs15000 next month.”** The planner
uses the mock monthly income, recurring expenses, and recent transactions to
estimate the available amount, savings gap, and suggested reductions in
flexible spending. It saves the requested target in SQLite. Chat history and
goals are stored in `data/ledgerly.sqlite`; the sidebar can start a separate
conversation. The sample profile assumes ₹100,000 monthly income and ₹36,000
in recurring commitments. These are demo assumptions and can be changed in
`backend/mock_api.py`.

## Prototype architecture

`streamlit_app.py` provides conversational UI. `backend/api.py` serves mock
bank data and `agents/planner_agent.py` builds the LangGraph tool-calling
orchestrator. The Ollama model chooses and combines specialist tools:

1. **Spending Agent** — categorizes and totals transactions and compares periods.
2. **Recommendation Agent** — provides optional, explainable spending ideas.
3. **Alerting Agent** — flags monthly limit breaches, spending increases,
   duplicate-looking transactions, and large or unfamiliar charges to review.
   These are review signals, not fraud determinations.
4. **Planner Agent** — routes questions, combines specialist responses, and
   creates goal-based savings plans.

FastAPI endpoints include `/account`, `/transactions`, `/spending/summary`,
`/spending/recommendations`, `/spending/alerts`, and `/savings/plan`. Input
transactions are in `data/transactions.json`. `backend/memory.py` uses SQLite
to persist conversations and requested goals.

The income and recurring commitments are fictional assumptions, displayed in
the app. Savings plans are estimates, not guarantees or financial advice. Unit
tests use a fake tool-calling model and FastAPI's in-process test client; a
running Ollama instance is not needed to run tests.

## Documentation

See the [documentation index](docs/README.md) for the architecture, API
reference, prototype behavior, and a step-by-step demo walkthrough.
