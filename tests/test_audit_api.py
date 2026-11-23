import sqlite3

from fastapi.testclient import TestClient

from pguard.api import create_app

SECRETS = ["AKIAIOSFODNN7EXAMPLE", "jane.doe@example.com", "+91 98765 43210"]


def test_audit_never_stores_raw_values_or_prompt(audited):
    guard, audit, tmp = audited
    guard.check("hello team, key AKIAIOSFODNN7EXAMPLE and jane.doe@example.com and +91 98765 43210", user="u1")
    blob = b"".join(p.read_bytes() for p in tmp.iterdir() if p.suffix == ".db")
    for s in SECRETS + ["hello team"]:
        assert s.encode() not in blob
    rows = audit.recent()
    assert rows[0]["decision"] == "block" and {f["type"] for f in rows[0]["findings"]} >= {"aws_access_key", "email"}


def test_same_secret_gets_same_fingerprint(audited):
    guard, audit, _ = audited
    guard.check("AKIAIOSFODNN7EXAMPLE")
    guard.check("again AKIAIOSFODNN7EXAMPLE")
    assert audit.stats()["repeated_values"][0][1] == 2


def test_key_file_is_private(audited):
    _, audit, _ = audited
    assert oct(audit.key_path.stat().st_mode & 0o777) == "0o600"


def _client(audited, upstream=None):
    guard, _, _ = audited
    return TestClient(create_app(guard, upstream or (lambda text: f"echo:{text}")))


def test_check_endpoint(audited):
    r = _client(audited).post("/check", json={"prompt": "AKIAIOSFODNN7EXAMPLE", "user": "a"})
    assert r.status_code == 200 and r.json()["decision"] == "block"
    assert "AKIAIOSFODNN7EXAMPLE" not in r.text


def test_chat_blocks_before_upstream(audited):
    called = []
    c = _client(audited, lambda t: called.append(t) or "x")
    assert c.post("/chat", json={"prompt": "AKIAIOSFODNN7EXAMPLE"}).status_code == 403
    assert called == []


def test_chat_forwards_only_redacted_text(audited):
    r = _client(audited).post("/chat", json={"prompt": "mail jane.doe@example.com"})
    assert r.status_code == 200
    assert "jane.doe@example.com" not in r.json()["reply"]


def test_admin_endpoints_closed_by_default(audited, monkeypatch):
    monkeypatch.delenv("PG_ADMIN_TOKEN", raising=False)
    c = _client(audited)
    assert c.get("/stats").status_code == 403
    monkeypatch.setenv("PG_ADMIN_TOKEN", "s3cret")
    assert c.get("/stats").status_code == 403
    assert c.get("/stats", headers={"X-Admin-Token": "s3cret"}).status_code == 200
