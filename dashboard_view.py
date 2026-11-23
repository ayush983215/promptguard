"""Shared dashboard rendering, used by dashboard.py (local) and app.py (hosted demo)."""
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


def render(db: Path) -> None:
    if not Path(db).exists():
        st.info("No audit data yet. Send a prompt through the API or CLI first.")
        return
    with sqlite3.connect(db) as c:
        events = pd.read_sql("SELECT * FROM events ORDER BY id DESC", c)
        findings = pd.read_sql(
            "SELECT f.*, e.user, e.ts FROM findings f JOIN events e ON e.id=f.event_id ORDER BY f.id DESC", c)
    if events.empty:
        st.info("No events yet.")
        return

    a, b, c3, d = st.columns(4)
    a.metric("Prompts checked", len(events))
    b.metric("Blocked", int((events.decision == "block").sum()))
    c3.metric("Redacted", int((events.decision == "redact").sum()))
    d.metric("Agent loosen attempts ignored", int(events.agent_loosen_attempt.sum()))

    left, right = st.columns(2)
    left.subheader("Decisions")
    left.bar_chart(events.decision.value_counts())
    right.subheader("Most common leak types")
    if findings.empty:
        right.write("No findings yet.")
    else:
        right.bar_chart(findings.type.value_counts())

    st.subheader("Repeat offenders (same secret value seen more than once)")
    rep = findings.groupby(["hmac", "type"]).size().reset_index(name="times")
    st.dataframe(rep[rep.times > 1].sort_values("times", ascending=False), width="stretch")

    st.subheader("Recent events")
    events["time"] = pd.to_datetime(events.ts, unit="s")
    st.dataframe(events[["time", "user", "decision", "rule_decision", "n_findings", "agent_tightened"]].head(50),
                 width="stretch")
    st.subheader("Recent findings (masked)")
    st.dataframe(findings[["user", "type", "action", "masked"]].head(50), width="stretch")
