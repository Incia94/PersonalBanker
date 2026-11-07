"""Streamlit conversational front end for the Ledgerly banking prototype."""

import uuid
from pathlib import Path

import httpx
import streamlit as st

from backend.api_client import MockBankClient
from backend.main import AgentOrchestrator
from backend.memory import SQLiteMemory


ROOT_DIR = Path(__file__).resolve().parent
DATABASE_PATH = ROOT_DIR / "data" / "ledgerly.sqlite"

st.set_page_config(
    page_title="Ledgerly | Banking assistant",
    page_icon="💸",
    layout="centered",
)


@st.cache_resource
def get_services() -> tuple[SQLiteMemory, MockBankClient, AgentOrchestrator]:
    memory = SQLiteMemory(DATABASE_PATH)
    api = MockBankClient()
    return memory, api, AgentOrchestrator(memory, api)


memory, api, orchestrator = get_services()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
thread_id = st.session_state.thread_id

st.title("💸 Ledgerly")
st.caption("Your personal banking assistant · fictional demo data · INR")

with st.sidebar:
    st.subheader("Your demo profile")
    try:
        profile = api.get("/account")
        st.metric("Mock monthly income", f"₹{profile['monthly_income']:,.0f}")
        st.caption("Recurring commitments")
        for expense in profile["fixed_expenses"]:
            st.write(f"{expense['name']}: ₹{expense['amount']:,.0f}")
        active_goal = memory.get_active_goal(thread_id)
        if active_goal:
            st.divider()
            st.metric(
                f"Savings goal · {active_goal['target_month']}",
                f"₹{active_goal['target_amount']:,.0f}",
            )
        if st.button("Start a new conversation", use_container_width=True):
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()
    except httpx.HTTPError as exc:
        st.error(f"Cannot load the mock Banking API: {exc}")

st.info(
    "Try: **Help me save ₹15,000 next month.** "
    "The Planner will use recent transactions, mock income and recurring bills "
    "to build a concrete plan."
)

history = memory.get_messages(thread_id)
for message in history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about spending, alerts, or a savings goal…"):
    prior_history = history
    memory.add_message(thread_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Planner is checking with the specialist agents…"):
            try:
                agent, answer = orchestrator.answer(
                    prompt,
                    thread_id,
                    prior_history,
                )
                st.markdown(answer)
                st.caption(f"Coordinated by {agent}")
                memory.add_message(thread_id, "assistant", answer)
            except (RuntimeError, httpx.HTTPError, ValueError) as exc:
                st.error(f"The assistant could not complete this request: {exc}")

if orchestrator.last_workflow:
    with st.expander("Agent orchestration"):
        for step in orchestrator.last_workflow:
            st.write(f"• {step}")
