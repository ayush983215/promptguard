# Deploying PromptGuard

There are two front ends. The **Next.js app in `web/`** is the main UI. The Streamlit page (`app.py`) is a
simpler single-service alternative.

## Option 1 (main UI): Next.js on Vercel + FastAPI on a container host
The web app calls the Python service, so both must be reachable.

1. **Host the API** (section B below: Render, Fly.io or Railway). Set `PG_ADMIN_TOKEN` to a long random value and
   `PG_SEED_DEMO=1` so the dashboard starts with sample data. Note its public HTTPS URL.
2. **Deploy `web/` on Vercel**: import the repo, set the *Root Directory* to `web`, and add two environment
   variables: `PROMPTGUARD_API` (the API URL) and `PG_ADMIN_TOKEN` (the same value). Do not prefix either with
   `NEXT_PUBLIC_`, or the token would be sent to browsers.
3. Open the Vercel URL and check the Playground and Dashboard both work.

Caveats: free API hosts sleep when idle, so the first request can be slow. The Dockerfile has not been built on
this machine. The web app has been built and tested locally against the API, but not yet deployed anywhere.

## Option 2: Streamlit only

Two things can be hosted. For an interview, the Streamlit demo is the one that matters.

## A. Streamlit demo (recommended): app.py
1. Push this folder to a GitHub repo (repo root = this folder).
2. Go to https://share.streamlit.io, sign in with GitHub, click **Create app**.
3. Pick the repo, branch `main`, main file `app.py`. Deploy. Python 3.12 is fine.
4. You get a public URL. The first start seeds sample traffic so the dashboard is not empty.

Notes
- The demo log is on the host's temporary disk and resets when the app restarts. That's intended.
- It uses `requirements.txt` (runtime only). CI uses `requirements-dev.txt`.
- No API keys are needed or should be added. The hosted demo runs the rule layer only.
- Visitors can type anything, so the page tells them to use placeholders. Their text is processed on the host.

## B. API service (optional): Dockerfile
```bash
docker build -t promptguard .
docker run -p 8000:8000 -e PG_ADMIN_TOKEN=change-me -e PG_DB=/data/audit.db -v pg-data:/data promptguard
```
Any container host works (Render, Fly.io, Railway). Set `PG_ADMIN_TOKEN` to a long random value; without it
`/stats` and `/events` stay closed. Put it behind HTTPS. The Dockerfile has not been built on this machine
(Docker was not running), so build it once before relying on it.

## Enabling the agent / `/chat` (needs a key)
`PG_LLM_MODEL`, `PG_LLM_KEY`, `PG_LLM_URL` (any OpenAI-compatible server, including local Ollama) and
`PG_USE_AGENT=1`. Never commit keys; use the host's secret settings.
