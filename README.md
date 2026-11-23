# PromptGuard

A lightweight data-loss-prevention (DLP) gateway for prompts sent to LLMs such as ChatGPT or Copilot.
It checks every prompt **before** it leaves, then blocks it, redacts it, or lets it through with a warning.

**Status: working prototype.** It is not a replacement for commercial DLP (Microsoft Purview, Netskope).
I built it to understand how DLP for AI works and where it breaks. Known limits are listed below.

## Architecture

```
 user / app
     |
     v
 POST /check or /chat  (FastAPI)            python -m pguard.cli "text"
     |
     v
 Guard.check()  ------------------------------------------------------------+
   1. detectors.py   regex + Luhn + entropy + base64 decode   (no AI)        |
   2. policy.yaml    finding type -> allow | warn | redact | block            |
   3. advisor.py     OPTIONAL agent: explains, may only TIGHTEN a decision    |
   4. decision = strongest action;  redact text or return nothing on block    |
     |                                                                        |
     v                                                                        v
 safe text -> upstream LLM                                      audit.py (SQLite)
                                                           masked values + keyed hashes
                                                                      |
                                                                      v
                                                          dashboard (Streamlit)
```

## Web UI
`web/` is a Next.js + Tailwind + shadcn/ui front end (sidebar layout, light and dark themes, responsive, accessibility-scanned
with axe: 0 violations on all pages). See [web/README.md](web/README.md). The older Streamlit page (`app.py`) still works.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q                      # 61 tests
.venv/bin/python eval/run_eval.py                  # detection quality + known evasions
.venv/bin/python -m pguard.cli "key AKIAIOSFODNN7EXAMPLE"   # exit code 2 = blocked

PG_ADMIN_TOKEN=change-me .venv/bin/uvicorn pguard.api:app --port 8000
curl -X POST localhost:8000/check -H 'content-type: application/json' \
     -d '{"prompt":"mail priya@acme.com","user":"alice"}'

.venv/bin/python demo.py                           # sample traffic
.venv/bin/streamlit run app.py                     # demo page: try it + dashboard + limits
```

Optional agent / `/chat` forwarding (any OpenAI-compatible endpoint, including local Ollama):
`PG_LLM_MODEL=... PG_LLM_KEY=... PG_LLM_URL=... PG_USE_AGENT=1`. Without these the tool runs fully offline.

Start with [STUDY_GUIDE.md](STUDY_GUIDE.md) (everything to learn). See also: [THREAT_MODEL.md](THREAT_MODEL.md) (actors, threats, OWASP LLM Top 10 mapping), [DEPLOY.md](DEPLOY.md), [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md).

## Security properties (each one has a test)

| Property | How |
|---|---|
| Agent can never loosen a rule-based decision | `stronger(rule, agent)` clamp in `engine.py`; a loosening attempt is ignored and logged |
| Agent never sees the prompt | it receives finding types and masked previews only |
| Agent is not consulted on a block | the decision is already final |
| Fails closed | any exception, oversize prompt or invalid policy ends in block / refuse to start |
| Raw secrets never stored | audit keeps type, action, masked preview and an HMAC (keyed, so low-entropy values can't be brute-forced from the hash) |
| Admin endpoints closed by default | `/stats` and `/events` need `PG_ADMIN_TOKEN`; unset means 403 |
| Config typos can't weaken policy | unknown action or finding type raises at load |

## Known limits (measured by `eval/run_eval.py`)

- Evasions that still get through (measured): rot13, reversed text inside base64, a key split across lines
  or chunks, and a key spelled out in words. Closed and regression-tested: base64 (up to 3 layers), hex,
  zero-width characters and fullwidth look-alike letters.
- Eval cases were written by me, so detection numbers are optimistic. They are not an independent benchmark.
- Regex/entropy detection means false positives and misses on unusual formats; the phone and card
  patterns are generic, not country-complete.
- Names, addresses and free-text business secrets ("Project Falcon launch date") are not detected.
- It only protects traffic that goes through it. A user who opens ChatGPT directly bypasses it; a real
  deployment needs a proxy, browser extension or network control to enforce that.
- The LLM advisor path is tested with a fake model only, not yet against a live API.
