"""Streamlit dashboard:  streamlit run dashboard.py   (reads audit.db directly)"""
import os
from pathlib import Path

import streamlit as st

from dashboard_view import render

st.set_page_config(page_title="PromptGuard", layout="wide")
st.title("PromptGuard: audit dashboard")
st.caption("Shows decisions and masked previews only. Raw secrets and prompt text are never stored.")
render(Path(os.environ.get("PG_DB", Path(__file__).parent / "audit.db")))
