"""HTTP service. Run:  uvicorn pguard.api:app --port 8000

POST /check  -> decision only (use it to gate any tool)
POST /chat   -> check, then forward the safe text to the upstream LLM
GET  /stats, /events -> audit data; need X-Admin-Token == $PG_ADMIN_TOKEN
                        (if the variable is unset these endpoints stay closed)
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import AuditLog, Guard, load_policy
from .advisor import LLMAdvisor
from .llm import LLMConfig, chat
from .samples import EXAMPLES, seed

ROOT = Path(__file__).resolve().parent.parent


class CheckIn(BaseModel):
    prompt: str = Field(max_length=2_000_000)   # hard cap before our own policy limit
    user: str = Field(default="anonymous", max_length=100)


def build_guard() -> Guard:
    cfg = LLMConfig.from_env()
    advisor = LLMAdvisor(cfg) if cfg and os.environ.get("PG_USE_AGENT") == "1" else None
    db = Path(os.environ.get("PG_DB", ROOT / "audit.db"))
    fresh = not db.exists()
    guard = Guard(load_policy(ROOT / "policy.yaml"), AuditLog(db), advisor)
    if fresh and os.environ.get("PG_SEED_DEMO") == "1":     # hosted demo: start with sample traffic
        seed(guard)
    return guard


def create_app(guard: Guard | None = None, upstream=None) -> FastAPI:
    """upstream(text) -> str; injectable so tests need no network."""
    app = FastAPI(title="PromptGuard")
    g = guard or build_guard()

    def admin(x_admin_token: str = Header(default="")):
        expected = os.environ.get("PG_ADMIN_TOKEN", "")
        if not expected or not secrets.compare_digest(x_admin_token, expected):
            raise HTTPException(403, "admin token required")

    def default_upstream(text: str) -> str:
        cfg = LLMConfig.from_env()
        if not cfg:
            raise HTTPException(503, "no upstream LLM configured (set PG_LLM_MODEL)")
        return chat(cfg, [{"role": "user", "content": text}])

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/examples")
    def examples():
        return [{"label": k, "prompt": v} for k, v in EXAMPLES.items()]

    @app.post("/check")
    def check(body: CheckIn):
        return g.check(body.prompt, body.user).to_dict()

    @app.post("/chat")
    def chat_endpoint(body: CheckIn):
        result = g.check(body.prompt, body.user)
        if result.decision == "block":
            raise HTTPException(403, {"blocked": True, "explanation": result.explanation})
        reply = (upstream or default_upstream)(result.redacted_text)
        return {"guard": result.to_dict(), "reply": reply}

    @app.get("/stats", dependencies=[Depends(admin)])
    def stats():
        return g.audit.stats()

    @app.get("/events", dependencies=[Depends(admin)])
    def events(limit: int = 50):
        return g.audit.recent(min(limit, 500))

    return app


app = create_app() if os.environ.get("PG_AUTOSTART", "1") == "1" else None
