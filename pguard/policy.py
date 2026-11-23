"""Policy: maps each finding type to an action. Validated at load time."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .detectors import ALL_TYPES, DEFAULT_INTERNAL_SUFFIXES

# Weakest to strongest. The final decision is the max rank over all findings.
RANK = {"allow": 0, "warn": 1, "redact": 2, "block": 3}


def stronger(a: str, b: str) -> str:
    """Return the stricter of two actions."""
    return a if RANK[a] >= RANK[b] else b


@dataclass(frozen=True)
class Policy:
    default_action: str = "warn"
    max_prompt_chars: int = 100_000
    internal_suffixes: tuple = DEFAULT_INTERNAL_SUFFIXES
    actions: dict = field(default_factory=dict)

    def action_for(self, finding_type: str) -> str:
        return self.actions.get(finding_type, self.default_action)


def load_policy(path: str | Path) -> Policy:
    """Load and validate. Any mistake raises, so a typo can never weaken a rule."""
    raw = yaml.safe_load(Path(path).read_text()) or {}
    actions = raw.get("actions", {})
    default = raw.get("default_action", "warn")
    for name, act in {**actions, "default_action": default}.items():
        if act not in RANK:
            raise ValueError(f"policy: unknown action {act!r} for {name!r}; use {sorted(RANK)}")
    unknown = set(actions) - ALL_TYPES
    if unknown:
        raise ValueError(f"policy: unknown finding types {sorted(unknown)}")
    limit = int(raw.get("max_prompt_chars", 100_000))
    if limit <= 0:
        raise ValueError("policy: max_prompt_chars must be positive")
    return Policy(default, limit, tuple(raw.get("internal_suffixes", DEFAULT_INTERNAL_SUFFIXES)), dict(actions))
