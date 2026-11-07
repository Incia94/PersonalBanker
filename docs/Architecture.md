# Architecture

## Overview

```text
Customer
   |
   v
Streamlit chat (streamlit_app.py)
   |  conversation history from SQLite
   v
AgentOrchestrator (backend/main.py)
   |
   v
Planner Agent / LangGraph (agents/planner_agent.py)
   |  local Ollama chat model selects one or more tools
   +----------------------+----------------------+----------------------+
   |                      |                      |                      |
   v                      v                      v                      v
Spending tool        Recommendation tool     Alerting tool       Savings-plan tool
   |                      |                      |                      |
   +----------------------+----------------------+----------------------+
                          |
                          v
                FastAPI mock bank API
                (backend/api.py)
                          |
             +------------+------------+
             |                         |
             v                         v
    Specialist calculations     Fictional profile and
    in agents/                  transactions in data/
             |
             v
       Tool results returned to the Planner
             |
       +-----+----------------+
       |                      |
       v                      v
  Chat response        Savings goal saved
                       to SQLite
```

## Components and responsibilities

- **Streamlit UI** — accepts natural-language questions, displays responses and
  the agent workflow, and loads the selected conversation's history.
- **Planner Agent** — a LangGraph agent backed by the locally configured Ollama
  chat model. It chooses the specialist tools based on the request and
  synthesizes their results into a response.
- **Spending specialist** — categorizes transaction amounts, totals spending,
  compares months, and creates category insights.
- **Recommendation specialist** — generates optional suggestions from current
  totals and month-over-month changes.
- **Alerting specialist** — produces review signals for configured category
  limits, spending spikes, possible duplicates, and large or unfamiliar
  transactions. Signals are not fraud determinations.
- **Savings-plan tool** — asks the API to estimate a plan for a requested INR
  amount, then persists the goal for the current conversation.
- **FastAPI mock bank API** — exposes the fictional account, transactions,
  summaries, recommendations, alerts, and savings-plan calculations.
- **SQLite memory** — stores chat messages and savings goals in
  `data/ledgerly.sqlite` by default.
- **Ollama** — runs the default `qwen3:8b` model locally; no hosted model
  service is configured by default.

## Conversation and tool-call flow

1. The UI loads messages for its conversation ID from SQLite and sends the
   history plus the new question to `AgentOrchestrator`.
2. The Planner receives the conversation and the available tools. Its model
   selects the tool or tools that suit the question.
3. Each tool calls the local FastAPI service, which reads the fictional data
   and invokes the deterministic specialist calculations.
4. The tool results return to LangGraph. The Planner writes a customer-facing
   answer using those results.
5. The UI displays the answer and stores the user and assistant messages in
   SQLite. When a savings-plan tool runs, it also stores the goal and its plan.

## Memory scope

The prototype persists conversation messages and savings goals in SQLite.
Streamlit passes the stored conversation history into each new Planner
invocation. The LangGraph agent does not currently have a durable SQLite
checkpointer; SQLite persistence here is application transcript/goal storage,
not persisted graph execution state.

## Data flow and boundaries

All account details and transactions are fictional and local to the project.
The API is a mock service, not a connection to a bank. Specialist calculations
are deterministic; the local model handles tool selection and response
synthesis. Savings estimates depend on the sample profile and observed
transactions, and are not guarantees or financial advice.
