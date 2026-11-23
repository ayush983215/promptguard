"""Command line: python -m pguard.cli "text"   or   echo text | python -m pguard.cli"""
import json
import sys
from pathlib import Path

from . import AuditLog, Guard, load_policy

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    guard = Guard(load_policy(ROOT / "policy.yaml"), AuditLog(ROOT / "audit.db"))
    result = guard.check(prompt, user="cli")
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.decision != "block" else 2    # non-zero exit lets scripts/CI gate on it


if __name__ == "__main__":
    raise SystemExit(main())
