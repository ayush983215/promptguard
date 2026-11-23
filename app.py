"""Hosted demo:  streamlit run app.py
One page with a live 'try it' box, the audit dashboard, and the known limits."""
import tempfile
from pathlib import Path

import streamlit as st

from dashboard_view import render
from pguard import AuditLog, Guard, load_policy
from pguard.samples import EXAMPLES, seed

ROOT = Path(__file__).parent
# Hosted filesystems are ephemeral, so the demo keeps its log in a temp folder.
DB = Path(tempfile.gettempdir()) / "promptguard_demo" / "audit.db"
DB.parent.mkdir(exist_ok=True)

COLOURS = {"block": "red", "redact": "orange", "warn": "blue", "allow": "green"}


@st.cache_resource
def get_guard() -> Guard:
    fresh = not DB.exists()
    guard = Guard(load_policy(ROOT / "policy.yaml"), AuditLog(DB))
    if fresh:                               # hosted disk is empty on first start: show sample traffic
        seed(guard)
    return guard


st.set_page_config(page_title="PromptGuard", layout="wide")
st.title("PromptGuard")
st.caption("A DLP gateway for LLM prompts: detect, then block / redact / warn, with an audit log that never stores the secret.")
st.warning("Demo only. Do NOT paste real secrets or personal data here. Use the placeholder examples.", icon="⚠️")

guard = get_guard()
tab_try, tab_dash, tab_about = st.tabs(["Try it", "Audit dashboard", "How it works and limits"])

with tab_try:
    choice = st.selectbox("Example prompts", ["(write your own)"] + list(EXAMPLES))
    default = EXAMPLES.get(choice, "")
    prompt = st.text_area("Prompt to check", value=default, height=120, key=f"p-{choice}")
    if st.button("Check prompt", type="primary") and prompt.strip():
        r = guard.check(prompt, user="demo-visitor")
        d = r.to_dict()
        st.markdown(f"### Decision: :{COLOURS[d['decision']]}[{d['decision'].upper()}]")
        st.write(d["explanation"])
        if d["text"] is not None:
            st.caption("Text that would be forwarded to the AI tool:")
            st.code(d["text"], language=None)
        else:
            st.caption("Nothing is forwarded when a prompt is blocked.")
        if d["findings"]:
            st.caption("Findings (masked, this is also all the audit log keeps):")
            st.dataframe(d["findings"], width="stretch")

with tab_dash:
    render(DB)

with tab_about:
    readme = (ROOT / "README.md").read_text()
    st.markdown("**Status" + readme.split("**Status", 1)[1].split("## Run it")[0])
    st.markdown("### Known limits")
    st.markdown(readme.split("## Known limits (measured by `eval/run_eval.py`)")[1])
