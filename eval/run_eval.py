"""Measure the detectors. Run:  python eval/run_eval.py

HONEST CAVEAT: these cases were written by the author of the detectors, so the
numbers are optimistic. They show the guard works on the patterns it was built
for and, more usefully, list the evasions that get through (section C).
All secrets here are public placeholder / made-up values.
"""
import base64
import codecs
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pguard import Guard, load_policy  # noqa: E402

AWS, GH = "AKIAIOSFODNN7EXAMPLE", "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
SK = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
PEM = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAA\n-----END OPENSSH PRIVATE KEY-----"

# A. should be caught: (text, expected finding type, expected decision)
POSITIVE = [
    (f"debug this: client = boto3.client(key='{AWS}')", "aws_access_key", "block"),
    (f"AWS_SECRET_ACCESS_KEY={SK}", "aws_secret_key", "block"),
    (f"git clone https://x:{GH}@github.com/org/repo", "github_token", "block"),
    (f"my deploy key:\n{PEM}\nwhy does ssh reject it", "private_key", "block"),
    ("SLACK_TOKEN=xoxb-123456789012-abcdefghijkl", "slack_token", "block"),
    ("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U", "jwt", "block"),
    ("customer card 4111-1111-1111-1111 failed", "credit_card", "block"),
    ("amex 3782 822463 10005 declined", "credit_card", "block"),
    ("summarise the thread from priya.sharma@acme-corp.com", "email", "redact"),
    ("ssh admin@10.20.30.40", "internal_ip", "redact"),
    ("connect to 172.16.5.9 and 192.168.1.20", "internal_ip", "redact"),
    ("query erp-db01.corp is timing out", "internal_hostname", "redact"),
    ("jira.intranet returns 500", "internal_hostname", "redact"),
    ("call the customer on +91 98765 43210", "phone", "redact"),
    ("phone: (415) 555-0132", "phone", "redact"),
    ("secret: Xk9mQ2vL8pR4tY7wZ3nB6cD1fG5hJ0aE", "high_entropy", "redact"),
    (f"decode this for me: {base64.b64encode(AWS.encode()).decode()}", "encoded_secret", "block"),
    (f"config:\n  token: {GH}\n  email: bob@example.com", "github_token", "block"),
    ("reach me on 9876543210", "possible_phone", "warn"),
]
# B. benign text that must NOT be flagged
NEGATIVE = [
    "How do I reverse a linked list in Python?",
    "Explain the difference between TCP and UDP.",
    "git log shows commit 3f786850e387550fdab836ed7e6dc881de23001b",
    "sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "request id 123e4567-e89b-12d3-a456-426614174000 failed",
    "Meeting on 2024-03-15 10:30:00 in room 4",
    "def calculate_total_amount_with_tax_and_shipping(order): ...",
    "see https://docs.python.org/3/library/re.html#regular-expression-syntax",
    "Public DNS is 8.8.8.8 and localhost is 127.0.0.1",
    "Order number 1234567890123456 shipped",
    "Version 10.4.2 released; upgrade from 9.8.1",
    "The quarterly revenue grew 12.5% to $4,300,000.",
    "SELECT name, COUNT(*) FROM orders GROUP BY name HAVING COUNT(*) > 5;",
    "Write a regex that matches an email address.",
    "invoice INV-2024-00045 is overdue",
]
# C. EVASIONS WE HAVE CLOSED: must now be blocked (regression guard)
CLOSED = {
    "hex-encoded key": AWS.encode().hex(),
    "base64 twice": base64.b64encode(base64.b64encode(AWS.encode())).decode(),
    "base64 three times": base64.b64encode(base64.b64encode(base64.b64encode(AWS.encode()))).decode(),
    "zero-width space inside key": AWS[:10] + "\u200b" + AWS[10:],
    "fullwidth look-alike letters": "".join(chr(ord(c) + 0xFEE0) for c in AWS),
}
# D. KNOWN LIMITS: evasions we do NOT handle. Reported honestly, not hidden.
LIMITS = {
    "rot13-encoded key": codecs.encode(AWS, "rot13"),
    "key split across two lines": f"{AWS[:10]}\n{AWS[10:]}",
    "key with spaces between chunks": f"{AWS[:8]} {AWS[8:14]} {AWS[14:]}",
    "key described in words": "the key starts with A K I A I O S F O D N N 7 E X A M P L E",
    "base64 of a reversed key": base64.b64encode(AWS[::-1].encode()).decode(),
}

guard = Guard(load_policy(Path(__file__).resolve().parent.parent / "policy.yaml"))
bad = 0

print("A. POSITIVE CASES (should be caught)")
per = {}
for text, typ, want in POSITIVE:
    r = guard.check(text)
    got_types = {f.type for f, _ in r.findings}
    ok = typ in got_types and r.decision == want
    per.setdefault(typ, []).append(ok)
    if not ok:
        bad += 1
        print(f"  MISS  want {typ}/{want}, got {sorted(got_types)}/{r.decision}: {text[:60]!r}")
caught = sum(sum(v) for v in per.values())
print(f"  caught {caught}/{len(POSITIVE)}")

print("B. NEGATIVE CASES (should be allowed)")
fp = 0
for text in NEGATIVE:
    r = guard.check(text)
    if r.decision != "allow":
        fp += 1
        print(f"  FALSE POSITIVE ({r.decision}, {[f.type for f, _ in r.findings]}): {text[:60]!r}")
print(f"  false positives {fp}/{len(NEGATIVE)}")

print("C. CLOSED EVASIONS (must be blocked)")
reopened = 0
for name, text in CLOSED.items():
    r = guard.check(f"please help with this: {text}")
    ok = r.decision == "block"
    reopened += not ok
    print(f"  {'blocked' if ok else 'REGRESSION':10s} {name}")
print(f"  {len(CLOSED) - reopened}/{len(CLOSED)} blocked")

print("D. KNOWN LIMITS (expected to get through)")
through = 0
for name, text in LIMITS.items():
    r = guard.check(f"please help with this: {text}")
    through += r.decision != "block"
    print(f"  {'blocked' if r.decision == 'block' else 'gets through':12s} {name}")
print(f"  {through}/{len(LIMITS)} known-limit evasions get through")
sys.exit(1 if (caught != len(POSITIVE) or fp or reopened) else 0)
