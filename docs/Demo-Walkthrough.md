# Demo walkthrough

This walkthrough demonstrates the local app, specialist routing, spending
analysis, alerts, and a savings goal. It uses only fictional sample data.

## 1. Start the services

Make sure Python 3.10 or newer and Ollama are installed. From the project root,
install the packages and download the default model:

```sh
python3 -m pip install -r requirements.txt
ollama pull qwen3:8b
```

Start the API in terminal one:

```sh
uvicorn backend.api:app --reload
```

Start Streamlit in terminal two:

```sh
streamlit run streamlit_app.py
```

Open the local Streamlit address shown in terminal two. The sidebar should
display the demo profile with ₹100,000 monthly income and recurring expenses.

## 2. Explore spending

Ask:

> How did I spend in October, and what changed from September?

The Planner should call the spending analysis tool. The API summarizes the
October sample transactions and compares them with September. For example,
Dining totals ₹6,013 in October and ₹4,398 in September, an increase of ₹1,615
(about 37%).

Expand **Agent orchestration** below the conversation to see the tool call used
for the response.

## 3. Ask for recommendations

Ask:

> How can I reduce my spending next month?

The Planner can call the recommendation tool. Suggestions are based on the
largest categories and their recent changes. They are optional ideas, not
financial advice.

## 4. Review alerts

Ask:

> Are there any unusual transactions or spending alerts?

The Planner can call the alerting tool. The API checks the sample spending
limits and transaction patterns. Treat any “possible” duplicate, unfamiliar
merchant, or fraud-related language as a prompt to review the mock transaction,
not as evidence of actual fraud.

## 5. Create a ₹15,000 savings plan

Ask:

> Help me save Rs15000 next month.

The Planner should call the savings-plan tool, which asks the API to estimate a
plan using the latest transaction month (October 2026 in the included data).
The sample calculation is:

| Item | Amount |
|---|---:|
| Monthly income | ₹100,000 |
| Fixed expenses | ₹36,000 |
| October variable spending | ₹51,183 |
| Estimated available before suggested cuts | ₹12,817 |
| Additional reduction needed for ₹15,000 | ₹2,183 |
| Weekly target for ₹15,000 | ₹3,750 |

The suggested flexible-category cuts cover the initial ₹2,183 gap for the
sample data. The Planner explains the assumptions and feasibility; it should
not promise that the goal is guaranteed.

After the tool call, the active goal should appear in the sidebar. It is also
stored in `data/ledgerly.sqlite` with the conversation's ID.

## 6. Verify the API directly (optional)

With the API running, open `http://127.0.0.1:8000/docs` or run:

```sh
curl http://127.0.0.1:8000/health
curl 'http://127.0.0.1:8000/spending/summary?month=2026-10'
```

## Troubleshooting

- **Cannot reach the API:** confirm `uvicorn backend.api:app --reload` is still
  running and `BANK_API_URL` points to it.
- **Cannot reach Ollama:** start Ollama, check `OLLAMA_BASE_URL`, and confirm
  `qwen3:8b` is available with `ollama list`.
- **Model does not call tools as expected:** verify that the selected Ollama
  model supports tool calling; try the default `qwen3:8b`.
- **Need a clean conversation:** select **Start a new conversation** in the
  sidebar. Existing messages and goals remain associated with their original
  conversation.
