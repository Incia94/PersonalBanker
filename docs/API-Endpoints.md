# API endpoints

The FastAPI mock banking service runs locally at `http://127.0.0.1:8000` by
default. Its interactive OpenAPI documentation is available at
`http://127.0.0.1:8000/docs`.

All data is fictional. Monetary values are INR. The transaction endpoints
accept an optional `month` query parameter in `YYYY-MM` format. If omitted,
the latest month in the sample data is used.

## `GET /health`

Check that the service is responding.

```sh
curl http://127.0.0.1:8000/health
```

Example response:

```json
{"status":"ok","service":"mock-banking-api"}
```

## `GET /account`

Return the sample account profile and recurring expenses.

```sh
curl http://127.0.0.1:8000/account
```

The response contains `customer_name`, `account_name`, `currency`,
`monthly_income`, and `fixed_expenses` (a list of names and amounts). The sample
income is ₹100,000 per month and the listed fixed expenses total ₹36,000.

## `GET /transactions`

Return fictional transactions, optionally filtered by month.

```sh
curl 'http://127.0.0.1:8000/transactions?month=2026-10'
```

Response shape:

```json
{
  "month": "2026-10",
  "currency": "INR",
  "transactions": [
    {
      "id": "txn-001",
      "date": "2026-10-29",
      "merchant": "The Daily Grind",
      "description": "Coffee and pastry",
      "amount": 425,
      "currency": "INR",
      "category": "Dining"
    }
  ]
}
```

The example shows one item; the actual response includes all transactions for
the requested month.

## `GET /spending/summary`

Return a categorized summary, month-over-month insights, and the top merchants.

```sh
curl 'http://127.0.0.1:8000/spending/summary?month=2026-10'
```

Response fields include `month`, `currency`, `summary` (transaction count,
total, category totals, and merchant totals), `insights`, and `top_merchants`.
The comparison uses the preceding calendar month.

## `GET /spending/recommendations`

Return optional suggestions based on the selected month's spending and its
comparison with the preceding month.

```sh
curl 'http://127.0.0.1:8000/spending/recommendations?month=2026-10'
```

Response shape:

```json
{
  "month": "2026-10",
  "recommendations": [
    "Example optional suggestion based on the mock spending data."
  ]
}
```

## `GET /spending/alerts`

Return review signals from the selected month's transactions. The prototype
checks configured category limits, significant month-over-month increases,
large transactions, unfamiliar merchants, and possible duplicate transactions.
These are not fraud determinations.

```sh
curl 'http://127.0.0.1:8000/spending/alerts?month=2026-10'
```

Response shape:

```json
{
  "month": "2026-10",
  "alerts": [
    "Example transaction review signal."
  ]
}
```

## `POST /savings/plan`

Build an estimated savings plan using the requested amount, sample monthly
income, recurring expenses, and spending in a reference month. The amount must
be greater than zero and no more than ₹10,000,000.

```sh
curl -X POST http://127.0.0.1:8000/savings/plan \
  -H 'Content-Type: application/json' \
  -d '{
    "target_amount": 15000,
    "thread_id": "demo",
    "reference_month": "2026-10"
  }'
```

Request fields:

| Field | Type | Required | Behavior |
|---|---|---:|---|
| `target_amount` | number | Yes | INR target; must be greater than zero and at most 10,000,000. |
| `thread_id` | string | No | Conversation ID; defaults to `demo`. |
| `reference_month` | string or null | No | Spending month in `YYYY-MM`; defaults to the latest available month. |

The response includes the target month, target amount, income and expense
assumptions, observed variable spending, estimated available amount, additional
reduction needed, suggested flexible-category cuts, weekly savings target, and
whether the goal is feasible with the suggested cuts. The API calculates the
plan; the Planner tool is responsible for saving the goal to SQLite.

## Validation and errors

- Invalid calendar months and invalid savings amounts are rejected with HTTP
  `422`.
- If there is no transaction history available for determining the default
  month, the API responds with HTTP `404`.
- The savings-plan endpoint does not itself persist a goal when called
  directly; goal persistence is performed by the Planner's
  `create_savings_plan` tool.
