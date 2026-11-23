# PromptGuard: everything you need to study

This is the one file to prepare from. `INTERVIEW_GUIDE.md` has the pitch and Q&A, `THREAT_MODEL.md` has the
risk analysis. This file explains how the whole thing works, in the order you should learn it.

## 0. How to study (about 3 hours)
1. **Pass 1 (45 min):** read sections 1 to 3 and run the commands in section 9. See it work before reading code.
2. **Pass 2 (90 min):** read sections 4 to 6 with the code open next to it. For each file, close the file and explain it out loud.
3. **Pass 3 (45 min):** sections 7, 8, 10. Answer the questions aloud without looking. Record yourself once.

Rule: you may only say something in an interview if you could open the file and show it.

## 1. The project in plain words
Employees paste API keys and customer data into AI tools like ChatGPT. PromptGuard checks the text first.
Plain code finds secrets and personal data. A YAML policy turns each finding into **block**, **redact** or **warn**.
An optional AI advisor can explain a decision or make it stricter, never weaker. Every decision is logged
without storing the secret. A web UI lets you try it and see the audit log.

It is a **prototype** to learn how DLP for AI works. Microsoft Purview and Netskope do this at scale. Say that first.

Two roles: the **employee** whose prompt is checked, and the **security team** who owns `policy.yaml` and reads the dashboard.

## 2. Architecture

```
 browser
   |  (only talks to the Next.js app)
   v
 Next.js web app  (web/)                       React pages + server-side route handlers
   |  /api/check  /api/examples  /api/stats  /api/events
   |  adds X-Admin-Token on the server for stats/events
   v
 FastAPI service  (pguard/api.py)              /check /examples /stats /events /chat /health
   v
 Guard.check()  (pguard/engine.py)
   1 normalise text          fold look-alike characters, strip invisible ones
   2 detect                  detectors.py (regex, Luhn, entropy, base64/hex decode)
   3 policy                  policy.yaml -> allow | warn | redact | block, strongest wins
   4 advisor (optional)      advisor.py, sees metadata only, can only tighten
   5 redact or refuse        build the forwarded text, or return nothing on block
   6 audit                   audit.py -> SQLite, masked values + HMAC only
```

Why a proxy layer in Next.js (the **backend-for-frontend** pattern): the browser never sees the admin token and
never talks to the Python service directly, so the Python service does not need CORS or to be trusted by the browser.

## 3. File map

| File | What it does | Key thing to know |
|---|---|---|
| `pguard/detectors.py` | Finds sensitive data | Returns `Finding(type, start, end, value, confidence)`. `value` is hidden from `repr` so it can't leak into logs |
| `pguard/policy.py` + `policy.yaml` | Type to action mapping | Validated on load: a typo raises instead of weakening a rule |
| `pguard/engine.py` | The decision pipeline | The tighten-only line, fail-closed `try/except`, size cap |
| `pguard/advisor.py`, `llm.py` | Optional AI advisor | Gets metadata only; output must be strict JSON; any failure falls back to rules |
| `pguard/audit.py` | SQLite audit log | Masked previews + HMAC; key in a separate `0600` file |
| `pguard/api.py` | HTTP service | Admin endpoints closed unless `PG_ADMIN_TOKEN` is set |
| `pguard/samples.py` | Example prompts | Shared by the CLI, Streamlit and web UI |
| `pguard/cli.py` | Command line | Exit code 2 on block, so scripts/CI can gate on it |
| `web/src/app/api/*/route.ts` | Server-side proxy | Validates input, fixes the user name to `web-visitor`, hides internal errors |
| `web/src/components/` | UI | `playground.tsx`, `dashboard.tsx`, `decision-badge.tsx`, `app-shell.tsx` |
| `tests/`, `eval/run_eval.py` | 61 tests and the evaluation | Includes tests that prove the safety rules |

## 4. The detectors (learn this best)

| Type | How it is found | Why this way |
|---|---|---|
| AWS access key | `AKIA`/`ASIA` + 16 uppercase/digits | Fixed public format, so regex is precise |
| AWS secret key | 40 base64-ish chars, only if an "aws ... secret" label is nearby | Otherwise every 40-char hash would match |
| GitHub / Slack token, JWT | Known prefixes (`ghp_`, `xoxb-`, `eyJ...`) | Fixed formats |
| Private key | `-----BEGIN ... PRIVATE KEY-----` to the END line, or the rest of the text if unterminated | Fail safe: take more, not less |
| Credit card | 13-19 digits that pass the **Luhn checksum** | Luhn removes most random digit runs |
| Email | Regex | Redact, not block |
| Internal IP | RFC 1918 ranges only (10/8, 172.16/12, 192.168/16) | Public and loopback IPs are not secrets |
| Internal hostname | Ends in `.internal`, `.corp`, `.local`, `.lan`, `.intranet` (configurable) | Reveals internal infrastructure |
| Phone | 10-13 digits with `+`, brackets, spaces or dashes | Plain digit runs would hit order numbers |
| Possible phone | Bare 10 digits starting 6-9, low confidence, **warn** | The ambiguous case |
| High entropy | 24+ chars, letters and digits, Shannon entropy at least 4.0, not a hex hash or UUID | Catches unknown-format random secrets |
| Encoded secret | Base64 or hex blob that decodes to ASCII containing a known credential, up to 3 layers | Closes cheap hiding tricks |

Overlaps: when two findings cover the same text, the higher-priority type wins (a key block containing an email reports only the key).

**Normalisation** (`engine.normalise`): NFKC folds look-alike characters (fullwidth `ＡＫＩＡ` becomes `AKIA`);
characters in Unicode category Cf (zero-width space, etc.) are removed. The text that is forwarded is this cleaned copy.

## 5. The decision logic (`engine.py`)
1. Prompt longer than 100,000 characters: **block** (fail closed).
2. Normalise, detect, look up each finding's action in the policy.
3. `rule decision` = the strongest action among findings (`allow < warn < redact < block`).
4. If there is an advisor, there are findings, and the rule decision is not already `block`: ask it.
5. `final = stronger(rule, advice)`. If the advice was weaker, it is ignored and logged as a "loosen attempt".
6. `block`: no text returned. `redact`: replace matching spans with `[REDACTED:type]`. Otherwise the text passes.
7. Any exception anywhere: **block**.

Why the advisor only sees metadata: injected instructions in the prompt cannot reach it, and it cannot leak the prompt.

## 6. The audit log and web layer

**Audit** (`audit.py`): two tables, `events` and `findings`. Findings store type, action, confidence, a masked
preview, and an HMAC-SHA256 fingerprint (first 16 hex chars). Credentials show only `[type len=N]`. Never stored: raw
values, prompt text.

Why HMAC, not a plain hash: a phone number has about 10^10 possibilities, so a plain hash can be reversed by trying
them all. HMAC needs a secret key, kept in `audit.key` (permissions `0600`), so it can't.

**Web layer** (`web/`):
- Pages are React; data is fetched by client components from `/api/*`.
- Route handlers (`route.ts`) run on the server: validate JSON and length, call the Python service with an 8-second timeout,
  return generic errors (`502`) so internal details don't leak, and add the admin token for stats/events.
- Security headers are set in `next.config.ts`: `nosniff`, `X-Frame-Options: DENY`, referrer policy, permissions policy.
- React escapes output by default, so findings and prompt text rendered in the page are not an XSS risk.
- Accessibility: automated axe scan shows 0 violations; text contrast at least 6.6:1; keyboard focus rings; skip link.

**Important weakness to state yourself:** the Next.js server adds the admin token for *every* visitor, so in this demo
anyone who opens the dashboard can see the audit data (masked values only). That is acceptable for a demo of masked
data, but it is not access control. A real deployment would put SSO or a login in front of the dashboard routes.

## 7. Glossary (say each in one sentence)
- **DLP (data loss prevention):** tools that stop sensitive data leaving an organisation.
- **PII:** personally identifiable information, like emails and phone numbers.
- **PCI data:** payment card data, regulated by the PCI DSS standard.
- **Luhn algorithm:** a checksum that real card numbers satisfy.
- **Shannon entropy:** a measure of randomness; random keys score higher than normal text.
- **RFC 1918:** the private IP ranges used inside networks.
- **HMAC:** a hash that needs a secret key; used here so fingerprints can't be brute-forced.
- **Masking vs redaction:** masking hides part of a value in logs; redaction removes it from the text being sent.
- **Fail closed (fail secure):** on error, deny. The opposite is fail open.
- **Least privilege:** give a component only the access it needs; the advisor sees metadata and has no tools.
- **Defense in depth:** several independent layers, so one failure is not fatal.
- **Prompt injection:** text that tries to give instructions to an AI. *Direct* comes from the user; *indirect* hides in content the user pastes.
- **False positive / false negative:** a harmless thing flagged / a real secret missed.
- **Evasion:** a trick to hide data from a detector, like encoding it.
- **Unicode normalisation (NFKC):** converting look-alike characters to their standard form.
- **Backend-for-frontend (BFF):** a server layer that sits between the browser and a backend and holds secrets for it.
- **OWASP Top 10 for LLM Applications:** a list of the main risks of LLM apps; this project targets LLM02 (sensitive information disclosure).
- **Threat model:** a structured list of who attacks, what they can do, and what stops them.

## 8. Numbers you can quote, with their honest limits
- **61 automated tests** pass. Three of them were proven meaningful by deliberately breaking the code (the agent loosening a decision, storing raw values, failing open) and watching a test fail.
- **Evaluation:** 19 of 19 positive cases caught, 0 of 15 benign cases flagged. *I wrote these cases, so this is optimistic and not an independent benchmark. Say so.*
- **5 evasions closed** (base64 up to 3 layers, hex, zero-width, fullwidth) with regression tests; **5 still get through** (rot13, reversed-then-encoded, split across lines, spaced out, spelled in words).
- **Accessibility:** axe-core reports 0 violations across 4 pages at desktop and mobile widths.

## 9. Commands to run before the interview
```bash
cd ~/cyberSecurity/promptguard
.venv/bin/python -m pytest -q                       # 61 pass
.venv/bin/python eval/run_eval.py                   # see evasions that still get through
.venv/bin/python -m pguard.cli "key AKIAIOSFODNN7EXAMPLE"; echo $?   # prints block, exit code 2
# full demo (two terminals)
PG_ADMIN_TOKEN=demo-token PG_SEED_DEMO=1 .venv/bin/uvicorn pguard.api:app --port 8765
cd web && npm run dev     # open http://localhost:3000
```
Drills (do these so you can talk about them from experience):
1. Change `email: redact` to `email: block` in `policy.yaml` and watch the behaviour change.
2. Change it to `email: blokc` and see the service refuse to start.
3. Try each example in the Playground, including the rot13 one, and say why it gets through.
4. In `engine.py`, find the line `final = stronger(rule, advice.action)` and explain it without looking at notes.

## 10. Questions to practise aloud
**About the project**
1. What does it do, and who is it for?
2. Walk me through one request from the browser to the log.
3. Why not use an LLM for the detection?
4. What stops the AI advisor from being attacked or leaking data?
5. How could someone get around it? (Name three, then the biggest: not using the gateway.)
6. What are the false-positive risks, and how would you tune them?
7. Why does the audit log use an HMAC?
8. How is this different from Purview or Netskope?

**About security thinking**
9. What does "fail closed" mean and where did you use it?
10. What is indirect prompt injection and how does it apply here?
11. What would you add for a real deployment? (Enforcement, SSO on the dashboard, SIEM export, per-team policy, name/address detection.)
12. What is the weakest part of your own project? (Dashboard access in the demo, evasions, self-written test cases, no real LLM test.)

**About the stack**
13. Why a Next.js proxy instead of the browser calling FastAPI? (Token stays server-side, no CORS, validation in one place.)
14. How do you keep the admin token out of the browser? (Server-only environment variable, never prefixed `NEXT_PUBLIC_`; verified it is not in the built JavaScript.)
15. Why FastAPI and SQLite? (Small, typed, simple; SQLite is enough for a prototype and would become Postgres at scale.)

**The honest-process question**
16. "Did you write all of this yourself?" Be truthful. This was built with an AI coding assistant. A good answer: "I built it with AI assistance, then I studied it, tested it, and I can explain every part. I ran the tests, broke the safety rules on purpose to check the tests catch it, and I know what it doesn't do." Only say this if it is true for you, and only after you actually have studied it.

## 11. What not to claim
- Not "production-ready", "enterprise" or "deployed" until it really is hosted.
- Not "100% detection". Say what was measured and that you wrote the test set.
- Not "works with GPT/Claude". The advisor has only been tested with a fake model.
- Not "novel". Say it is a learning prototype of an existing product category.
- Not that the dashboard is access-controlled. In the demo it is open by design.

## 12. One-page cheat sheet
- **What:** gateway that checks prompts for secrets/PII before they reach an AI tool: block, redact or warn.
- **How:** deterministic detectors, YAML policy, optional advisor (tighten only), masked audit log, web UI.
- **Best idea:** `final = stronger(rule, advice)`: a hijacked AI can over-block but never leak.
- **Also good:** fail closed; HMAC audit; secrets never stored; closed evasions are regression-tested.
- **Limits to volunteer:** 5 evasions pass; user can bypass the gateway; tests are self-written; dashboard open in demo; advisor not tested on a live model.
- **Terms:** DLP, PII, PCI, Luhn, entropy, HMAC, fail closed, least privilege, defense in depth, prompt injection, BFF.
