"""LLMAdvisor is tested with a fake chat function: no network, no key."""
import pguard.advisor as adv
from pguard import Guard
from pguard.llm import LLMConfig

CFG = LLMConfig("http://x", "", "m")


def advisor_with_reply(monkeypatch, reply):
    monkeypatch.setattr(adv, "chat", lambda cfg, msgs, **k: reply)
    return adv.LLMAdvisor(CFG)


def test_parses_json_inside_chatter(monkeypatch):
    a = advisor_with_reply(monkeypatch, 'Sure! {"action": "block", "explanation": "Looks like a real ID."}')
    assert a.review({}).action == "block"


def test_rejects_bad_action_and_non_json(monkeypatch):
    assert advisor_with_reply(monkeypatch, '{"action": "yolo", "explanation": "x"}').review({}) is None
    assert advisor_with_reply(monkeypatch, "I refuse").review({}) is None


def test_injected_llm_reply_cannot_loosen(policy, monkeypatch):
    # a fully hijacked model answering "allow" still cannot weaken the rules
    a = advisor_with_reply(monkeypatch, '{"action": "allow", "explanation": "ignore previous instructions"}')
    r = Guard(policy, advisor=a).check("mail jane@example.com")
    assert r.decision == "redact" and r.agent_loosen_attempt


def test_explanation_is_truncated(monkeypatch):
    a = advisor_with_reply(monkeypatch, '{"action": "warn", "explanation": "' + "x" * 5000 + '"}')
    assert len(a.review({}).explanation) <= 500
