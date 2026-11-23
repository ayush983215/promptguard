# PromptGuard threat model

## What we protect
Sensitive data (credentials, payment data, personal data, internal infrastructure names) in text that an
employee is about to send to an external AI tool.

## Who we worry about
| Actor | What they do |
|---|---|
| **Careless employee** (the main case) | Pastes a config file, log or email thread without noticing the secret in it |
| **Malicious insider** | Deliberately tries to move data out, e.g. by encoding or splitting it |
| **Attacker controlling content** | Plants instructions in a document the employee pastes (indirect prompt injection), aiming at the guard or the AI tool |
| **Outsider reaching the service** | Calls the API or admin endpoints without permission |

## Trust boundaries
`employee -> [PromptGuard] -> external LLM`  and  `PromptGuard -> audit database -> dashboard`.
The prompt is **untrusted input**. The external LLM is **untrusted for confidentiality**. The optional
agent is **untrusted for authority**: its output is advisory and clamped.

## Threats and what we do about them

| # | Threat | Mitigation in the code | Residual risk |
|---|---|---|---|
| T1 | Secret pasted in plain text | Deterministic detectors + policy block | Unknown secret formats are missed |
| T2 | Secret hidden by encoding | Base64 and hex decoded up to 3 layers; NFKC folding; invisible characters stripped | rot13, reversed text, splitting, spaced-out or spelled-out secrets still pass |
| T3 | Prompt injection aims to make the guard allow data | Detectors are code, not language models, so text can't argue with them; agent sees metadata only | None for the rule layer. The agent can be misled, but only toward stricter decisions |
| T4 | Compromised or hijacked agent loosens a block | `stronger(rule, agent)` clamp; agent is not consulted on a block; loosening attempts are logged | A hijacked agent could over-block (availability), not leak |
| T5 | Guard crashes or is given a huge input | Fail closed: any exception blocks; size cap blocks; regexes are linear and bounded | A crash loop blocks users (availability) |
| T6 | Audit log becomes a second leak | No prompt text or raw values stored; masked previews; HMAC with a separate 0600 key | User IDs are personal data and need retention rules and access control |
| T7 | Unauthorised access to audit data | `/stats` and `/events` require `X-Admin-Token`; closed if unset; constant-time compare | Single shared token, no per-user auth or rate limiting |
| T8 | Weak policy by typo | Policy validated at startup; unknown action or type refuses to start | None known |
| T9 | User bypasses the gateway | Not solved in code | **Biggest gap.** Needs a proxy, browser extension or network controls |
| T11 | Anyone can read the audit dashboard in the web demo | Only masked data is ever stored; the admin token stays server-side | **Open by design in the demo:** the Next.js server adds the token for every visitor, so this is not access control. A real deployment needs SSO or a login in front of the dashboard |
| T10 | Hosted demo receives real secrets | Warning banner; only masked data kept; log lives on ephemeral disk | A visitor could still ignore the warning; the text does pass through the host's server |

## Mapping to OWASP Top 10 for LLM Applications (2025 list)
Check the exact wording against owasp.org before quoting it in an interview.

| OWASP item | How PromptGuard relates |
|---|---|
| **LLM02 Sensitive Information Disclosure** | The main target: stops sensitive data going out to the model provider |
| **LLM01 Prompt Injection** | Rule layer is immune to injected text; agent input is metadata-only and its output is clamped |
| **LLM06 Excessive Agency** | The agent has no tools and no authority: it can only explain or tighten |
| **LLM10 Unbounded Consumption** | Prompt size cap and linear-time detectors |
| LLM05 Improper Output Handling | Partly: the agent's reply is parsed against a strict schema and truncated |

Not covered: model poisoning, supply chain, system prompt leakage, vector/embedding weaknesses, misinformation.

## Out of scope for this prototype
Model-output scanning (data coming *back* from the LLM), file and image uploads, names and addresses
(needs NER), per-user policies, SSO, SIEM export, and enforcement of the gateway on every device.
