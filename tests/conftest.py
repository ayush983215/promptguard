import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pguard import AuditLog, Guard, load_policy  # noqa: E402


@pytest.fixture
def policy():
    return load_policy(ROOT / "policy.yaml")


@pytest.fixture
def guard(policy):
    return Guard(policy)


@pytest.fixture
def audited(policy, tmp_path):
    audit = AuditLog(tmp_path / "audit.db")
    return Guard(policy, audit), audit, tmp_path
