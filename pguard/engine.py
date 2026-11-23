"""The guard: detect -> apply policy -> (optional) agent review -> decide.

Key safety rule: the agent can only TIGHTEN a decision. If the rules say
"block", the agent is not even consulted; if it proposes something weaker than
the rules, its proposal is ignored and the attempt is logged.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from .audit import AuditLog, mask
from .detectors import Finding, detect
from .policy import RANK, Policy, stronger

MAX_EXPLANATION = 500


@dataclass
class Result:
    decision: str                       # allow | warn | redact | block
    rule_decision: str                  # what the deterministic rules alone said
    explanation: str
    findings: list = field(default_factory=list)   # list[(Finding, action)]
    redacted_text: str | None = None    # present for allow/warn/redact, never for block
    agent_used: bool = False
    agent_tightened: bool = False
    agent_loosen_attempt: bool = False

    def to_dict(self) -> dict:
        """Safe to return over the API: findings carry masked values only."""
        return {
            "decision": self.decision, "rule_decision": self.rule_decision,
            "explanation": self.explanation, "text": self.redacted_text,
            "findings": [{"type": f.type, "action": a, "confidence": f.confidence,
                          "masked": mask(f.type, f.value)} for f, a in self.findings],
            "agent": {"used": self.agent_used, "tightened": self.agent_tightened,
                      "loosen_attempt_ignored": self.agent_loosen_attempt},
        }


def _template_explanation(decision: str, findings) -> str:
    kinds = ", ".join(sorted({f.type.replace("_", " ") for f, _ in findings})) or "nothing"
    return {
        "block": f"Blocked: the prompt contains {kinds}. Remove it and resend; credentials and "
                 "payment data must never be pasted into an AI tool.",
        "redact": f"Sent with sensitive values replaced by placeholders ({kinds}).",
        "warn": f"Warning: possible sensitive data ({kinds}). Check before sending.",
        "allow": "No sensitive data detected.",
    }[decision]


def normalise(text: str) -> str:
    """Defeat cheap obfuscation before scanning: fold look-alike characters (NFKC, e.g. fullwidth
    letters) and drop invisible format characters such as zero-width spaces. The text that is
    forwarded is this cleaned copy."""
    text = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


def _redact(text: str, spans: list[Finding]) -> str:
    for f in sorted(spans, key=lambda f: f.start, reverse=True):   # right-to-left keeps offsets valid
        text = text[:f.start] + f"[REDACTED:{f.type}]" + text[f.end:]
    return text


class Guard:
    def __init__(self, policy: Policy, audit: AuditLog | None = None, advisor=None):
        self.policy, self.audit, self.advisor = policy, audit, advisor

    def check(self, prompt: str, user: str = "anonymous") -> Result:
        try:
            result = self._check(prompt)
        except Exception:                       # fail CLOSED: a bug must never let data through
            result = Result("block", "block", "Blocked: the guard hit an internal error.")
        if self.audit:
            self.audit.record(
                user=user, decision=result.decision, rule_decision=result.rule_decision,
                prompt_chars=len(prompt), findings=result.findings, agent_used=result.agent_used,
                agent_tightened=result.agent_tightened, agent_loosen_attempt=result.agent_loosen_attempt)
        return result

    def _check(self, prompt: str) -> Result:
        if len(prompt) > self.policy.max_prompt_chars:
            return Result("block", "block", "Blocked: the prompt is too large to scan safely.")

        prompt = normalise(prompt)
        found = detect(prompt, self.policy.internal_suffixes)
        pairs = [(f, self.policy.action_for(f.type)) for f in found]
        rule = "allow"
        for _, act in pairs:
            rule = stronger(rule, act)

        final, used, tightened, loosen, advice = rule, False, False, False, None
        # Only consult the agent when there is something ambiguous and the rules did not already block.
        if self.advisor and pairs and rule != "block":
            used = True
            info = {"rule_decision": rule,
                    "findings": [{"type": f.type, "action": a, "confidence": f.confidence,
                                  "masked": mask(f.type, f.value)} for f, a in pairs]}
            try:
                advice = self.advisor.review(info)
            except Exception:
                advice = None                   # advisor failure = fall back to the rules
            if advice and advice.action in RANK:
                loosen = RANK[advice.action] < RANK[rule]
                final = stronger(rule, advice.action)          # <-- the tighten-only clamp
                tightened = RANK[final] > RANK[rule]

        if final == "block":
            text = None
        elif final == "redact":
            floor = RANK["warn"] if tightened else RANK["redact"]
            text = _redact(prompt, [f for f, a in pairs if RANK[a] >= floor])
        else:
            text = prompt

        explanation = (advice.explanation[:MAX_EXPLANATION] if advice and not loosen
                       else _template_explanation(final, pairs))
        return Result(final, rule, explanation, pairs, text, used, tightened, loosen)
