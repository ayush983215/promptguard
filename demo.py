"""Fill the audit log with sample traffic so the dashboard has something to show.
Usage:  python demo.py"""
from pathlib import Path

from pguard import AuditLog, Guard, load_policy
from pguard.samples import SAMPLES

if __name__ == "__main__":
    root = Path(__file__).parent
    g = Guard(load_policy(root / "policy.yaml"), AuditLog(root / "audit.db"))
    for user, text in SAMPLES:
        r = g.check(text, user)
        print(f"{user:6s} {r.decision:7s} {[f.type for f, _ in r.findings]}")
