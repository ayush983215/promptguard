# PromptGuard: interview guide

Read STUDY_GUIDE.md first (it explains everything), then this file for the pitch and Q&A, then THREAT_MODEL.md once. Everything here maps to code you can open and point at.

## 1. The 30-second pitch
"Employees paste API keys, customer data and internal code into tools like ChatGPT. I built a small
gateway that checks each prompt first. Plain code detects secrets and personal data, a YAML policy
decides block, redact or warn, and an optional AI agent can explain a decision or make it stricter,
but never weaker. Everything is logged without ever storing the secret. It's a prototype; commercial
DLP tools do this at scale, and I built it to learn where the hard parts are."

## 2. Walk-through of one request
Prompt: `fix this: key=AKIAIOSFODNN7EXAMPLE, mail priya@acme.com`
1. **API** (`api.py`) receives it. Size is capped.
2. **Detectors** (`detectors.py`) find two things: `aws_access_key` and `email`.
3. **Policy** (`policy.yaml`): AWS key -> block, email -> redact.
4. **Decision** is the strongest action, so `block`. No text goes out, the user gets an explanation.
5. **Audit** (`audit.py`) stores: type, action, masked preview `[aws_access_key len=20]`, keyed hash. Not the key, not the prompt.
6. **Dashboard** shows the counts.
If it had only contained the email: decision `redact`, text becomes `mail [REDACTED:email]` and is forwarded.

## 3. The detectors, and why each check is there
- **Prefix patterns** (AWS `AKIA...`, GitHub `ghp_...`, Slack `xox...`, JWT `eyJ...`, PEM private-key block): these formats are fixed, so regex is precise.
- **AWS secret key**: 40 random-looking characters are only flagged as an AWS secret when an "aws ... secret" label is nearby, otherwise every hash would match.
- **Credit cards**: a digit run alone is not enough; it must pass the **Luhn checksum**. This removes most random numbers (order IDs).
- **Entropy**: random keys have high Shannon entropy (about 4+ bits/char); words and identifiers are lower. Git SHAs, MD5s and UUIDs are explicitly excluded.
- **Internal IPs / hostnames**: only RFC 1918 ranges (10/8, 172.16/12, 192.168/16) and configurable suffixes like `.corp`.
- **Encodings**: base64 and hex blobs are decoded (up to 3 layers) and re-scanned, so `base64(base64(KEY))` is caught. Before scanning, text is normalised: look-alike (fullwidth) letters are folded and invisible characters like zero-width spaces are removed.
- **Overlaps**: when two findings cover the same text the higher-priority type wins (a key block containing an email reports only the key).

## 4. The design decisions you should be able to defend
1. **Deterministic core, AI on the side.** Rules are predictable, testable and can't be talked out of a decision. The LLM adds explanation, nothing else.
2. **Tighten-only agent.** One line in `engine.py`: `final = stronger(rule, advice.action)`. A prompt-injected or buggy model can raise severity but never lower it. There is a test that simulates a hijacked model replying "allow, ignore the rules".
3. **Agent sees metadata only.** The prompt text never goes to the agent, so injection text in the prompt has no path to it. It also means the agent can't leak the prompt.
4. **Fail closed.** Errors, oversize prompts and bad config all end in block or refusing to start.
5. **Audit without secrets.** Masked preview plus HMAC. A plain hash of a phone number could be brute-forced (only 10^10 possibilities); an HMAC with a random key kept in a separate 0600 file can't. The HMAC still lets us say "the same key was pasted 3 times".
6. **Policy validated on load.** A typo like `blokc` would otherwise silently weaken a rule.
7. **Admin endpoints closed by default.** If no token is configured they return 403, not 200.

## 5. Questions you'll probably get
**Why not just ask an LLM to check prompts?** It's slower, costs money, is non-deterministic, and is itself attackable by prompt injection. Regex and checksums are exact for well-defined formats. I use the LLM only where judgment helps and bound it.

**What if the prompt tries to attack your agent?** The agent never sees the prompt, only types and masked values. Even a fully hijacked reply can only make the decision stricter. Tests cover both.

**How would an attacker get around it?** Splitting the secret across lines or chunks, rot13, reversing it, spelling it out in words, or just not going through the gateway. `eval/run_eval.py` section D lists these and all 5 get through today. Hex, multi-layer base64, zero-width characters and fullwidth look-alikes were evasions I found and closed; section C is a regression test for them.

**False positives?** 0 of 15 benign cases in my set, but I wrote that set. Real traffic would produce more. I'd tune with real logs and offer a "report false positive" path.

**Isn't this just Purview / Netskope?** Yes, in function. This is a prototype to learn the mechanism. What I can say that a pure user can't: where it breaks, and how the audit and agent design avoid creating new risk.

**Where would this run in a company?** As a proxy or API gateway in front of approved AI tools, or behind a browser extension. Alerts would go to the SOC and the dashboard data into a SIEM.

**Is the audit log itself a risk?** It contains user IDs, which are personal data, so it needs access control and a retention period. It contains no secrets by design.

**How do you know the tests mean anything?** I broke three rules on purpose (let the agent loosen, store raw values, fail open) and checked that a test failed each time.

**What did you not test?** The LLM advisor against a real API (only with a fake model), scale, and any real traffic.

## 6. What to say about the AI part, honestly
It's about 15% of the project. It is optional, off by default, and the tool works fully without it. If asked
"how did you use agentic AI?": a bounded advisor with a fixed output schema, no tool access to the raw prompt,
and a code-level clamp on what it can change.

## 7. Live demo script (3 minutes)
Start both servers first (commands in STUDY_GUIDE.md section 9), then open http://localhost:3000.
1. **Playground:** click "Leaked AWS key". Show BLOCK, the masked preview, and that nothing is forwarded.
2. Click "Email + internal host". Show REDACT and the `[REDACTED:...]` text that would be sent.
3. Click "Prompt injection attempt". Still BLOCK: the rules don't read English instructions.
4. Click "Known limit: rot13". It gets through. Say so yourself: "this is a gap I documented."
5. **Dashboard:** show the counts, the repeated-value panel, and say the log holds masked data only.
6. Optional: `python -m pguard.cli "key AKIAIOSFODNN7EXAMPLE"; echo $?` shows exit code 2.

## 8. Threat model
Open `THREAT_MODEL.md`: four actors, ten threats with mitigation and residual risk, and a mapping to the OWASP Top 10 for LLM Applications (LLM02 sensitive information disclosure is the main one). The biggest residual risk is T9: a user can skip the gateway. Say that yourself.

## 9. What I'd build next
Proxy/browser-extension enforcement, more encodings, name and address detection (NER), per-team policies,
SIEM export, and a feedback loop for false positives.
