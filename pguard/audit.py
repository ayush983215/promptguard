"""Audit log (SQLite). The raw secret and the prompt text are NEVER stored.

For each finding we keep: its type, the action taken, a masked preview, and a
keyed hash (HMAC). The HMAC lets us notice "the same key was pasted three
times" without being able to recover the key. A plain hash would be unsafe for
low-entropy values such as phone numbers (anyone could brute-force it), so the
hash is keyed with a random secret kept in a separate file.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL, user TEXT NOT NULL,
  decision TEXT NOT NULL, rule_decision TEXT NOT NULL,
  agent_used INTEGER NOT NULL DEFAULT 0,
  agent_tightened INTEGER NOT NULL DEFAULT 0,
  agent_loosen_attempt INTEGER NOT NULL DEFAULT 0,
  prompt_chars INTEGER NOT NULL, n_findings INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL REFERENCES events(id),
  type TEXT NOT NULL, action TEXT NOT NULL, confidence TEXT NOT NULL,
  masked TEXT NOT NULL, hmac TEXT NOT NULL);
"""
# Credential-like types reveal nothing but their length.
_HIDE_ENTIRELY = {"private_key", "aws_access_key", "aws_secret_key", "github_token",
                  "slack_token", "jwt", "encoded_secret", "high_entropy", "credit_card"}


def mask(finding_type: str, value: str) -> str:
    if finding_type in _HIDE_ENTIRELY or len(value) <= 8:
        return f"[{finding_type} len={len(value)}]"
    return f"{value[:2]}***{value[-2:]}"


class AuditLog:
    def __init__(self, db_path: str | Path = "audit.db", key_path: str | Path | None = None):
        self.db_path = Path(db_path)
        self.key_path = Path(key_path) if key_path else self.db_path.with_suffix(".key")
        self._key = self._load_key()
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _load_key(self) -> bytes:
        if not self.key_path.exists():
            fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(os.urandom(32))
        return self.key_path.read_bytes()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def fingerprint(self, value: str) -> str:
        return hmac.new(self._key, value.encode(), hashlib.sha256).hexdigest()[:16]

    def record(self, *, user, decision, rule_decision, prompt_chars, findings,
               agent_used=False, agent_tightened=False, agent_loosen_attempt=False) -> int:
        """findings: iterable of (Finding, action). Only masked data is written."""
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO events (ts,user,decision,rule_decision,agent_used,agent_tightened,"
                "agent_loosen_attempt,prompt_chars,n_findings) VALUES (?,?,?,?,?,?,?,?,?)",
                (time.time(), user, decision, rule_decision, int(agent_used), int(agent_tightened),
                 int(agent_loosen_attempt), prompt_chars, len(findings)))
            eid = cur.lastrowid
            c.executemany(
                "INSERT INTO findings (event_id,type,action,confidence,masked,hmac) VALUES (?,?,?,?,?,?)",
                [(eid, f.type, act, f.confidence, mask(f.type, f.value), self.fingerprint(f.value))
                 for f, act in findings])
        return eid

    # ---- read side (used by the API and the dashboard) ----
    def stats(self) -> dict:
        with self._conn() as c:
            decisions = dict(c.execute("SELECT decision, COUNT(*) FROM events GROUP BY decision"))
            types = c.execute("SELECT type, COUNT(*) n FROM findings GROUP BY type ORDER BY n DESC").fetchall()
            repeats = c.execute(
                "SELECT type, COUNT(*) n FROM findings GROUP BY hmac HAVING n > 1 ORDER BY n DESC LIMIT 10").fetchall()
            agent = c.execute("SELECT COALESCE(SUM(agent_tightened),0), COALESCE(SUM(agent_loosen_attempt),0) FROM events").fetchone()
        return {"decisions": decisions, "top_types": types, "repeated_values": repeats,
                "agent_tightened": agent[0], "agent_loosen_attempts_blocked": agent[1]}

    def recent(self, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["findings"] = [dict(f) for f in c.execute(
                    "SELECT type,action,confidence,masked FROM findings WHERE event_id=?", (r["id"],))]
                out.append(d)
        return out
