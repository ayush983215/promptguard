# PromptGuard web UI

Next.js 16 (App Router) + Tailwind CSS v4 + shadcn/ui. It is a thin front end for the Python guard service.

```
browser  ->  Next.js (this app)  ->  FastAPI guard service (../pguard)
              /api/check, /api/stats, ...     /check, /stats, ...
```

The browser only ever talks to this app. Its route handlers in `src/app/api/` call the FastAPI service and add the
admin token on the server, so the token is never sent to the browser. Detection logic lives only in Python.

## Run locally
```bash
# 1. guard service (from the repo root)
PG_ADMIN_TOKEN=demo-token PG_SEED_DEMO=1 .venv/bin/uvicorn pguard.api:app --port 8765

# 2. web app (from web/)
cp .env.example .env.local        # set PROMPTGUARD_API=http://127.0.0.1:8765 and the same PG_ADMIN_TOKEN
npm install
npm run dev                       # or: npm run build && npm start
```

## Where things are
- `src/app/page.tsx`, `dashboard/`, `about/`: the three pages (Playground, Dashboard, How it works)
- `src/components/`: app shell (sidebar, mobile nav), playground, dashboard, decision badge
- `src/components/ui/`: shadcn/ui primitives
- `src/app/globals.css`: all colour tokens, light and dark. Text contrast checked at 6.6:1 or better
- `src/app/api/*/route.ts`: server-side proxy to the guard service
