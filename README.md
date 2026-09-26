# GuessIngs — AI Nutrition Analysis

Scan or type a food product's ingredient list and get a clear, **consistent** ingredient-based score (0–100), a
**GREEN / YELLOW / RED** verdict, and the exact calculation behind it.

AI is used for what it's good at — reading labels, extracting and classifying ingredients, and writing explanations.
The **score itself comes from a deterministic rule engine** in normal application code, so the same ingredient list
always produces the same score, verdict and breakdown.

```
Scan / Upload / Type  →  OCR (+ Claude vision)  →  Normalize  →  Classify (KB → rules → cache → AI)
                      →  Deterministic scoring engine  →  Score + verdict  →  Result  →  History
```

## Stack

| Layer    | Tech |
|----------|------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS v4, shadcn-style components (Radix), TanStack Query |
| Backend  | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL (SQLite supported for tests) |
| OCR / AI | Tesseract OCR, Anthropic Claude (optional — structured outputs) |
| Other    | Redis (optional, shared rate limits), Docker Compose, GitHub Actions |

## Features

- Registration / login (bcrypt, httpOnly session cookie + CSRF double-submit, token revocation on password change)
- Scan with live mobile camera, photo upload (drag & drop) or manual input
- OCR with image validation and quality checks (blur, darkness, resolution); review/edit step before analysis
- Ingredient normalization: case, accents, British spellings, E-/INS-numbers, synonyms, percentages,
  "contains 2% or less of", sub-ingredients in brackets, functional classes (`emulsifier (soy lecithin)`), duplicates
- Classification pipeline: curated knowledge base (870+ names, synonyms and E-numbers) → deterministic patterns → cached AI classifications → AI
- Deterministic scoring with a full receipt-style breakdown, NOVA estimate, concerns, positives and alternatives
- History (search, filter, pagination), saved products, side-by-side comparison (2–4 products), dashboard
- Profile (name, password, account deletion) and settings (theme, AI summaries, NOVA display)
- Every analysis is reproducible: stored structured inputs + rule/KB/AI versions, plus a **Verify score** action
- Light/dark mode, mobile bottom navigation with a primary Scan action, desktop sidebar

## Scoring rules (v1.0.0)

Start at **100**, then:

| Rule | Points |
|------|--------|
| Added sugar / syrups (one deduction, by earliest sugar position) | 1st −30 · 2nd–3rd −25 · 4th–5th −20 · 6th+ −15; −5 per extra sugar source; max −30 |
| Artificial sweetener | −10 each |
| Hydrogenated / partially hydrogenated oil | −25 (once) |
| Artificial color | −8 each |
| Artificial flavor | −8 each |
| Preservative | −6 each |
| Emulsifier / ultra-processed marker | −5 each |
| Excessive sodium (only if sodium is provided, > 600 mg / 100 g) | −10 |
| NOVA 4 (any sweetener, hydrogenated oil, artificial color/flavor or emulsifier marker) | −20 |
| Whole-food fiber/protein source in the first 5 ingredients | +5 each, max +10 |
| Healthy fat source in the first 5 ingredients | +5 |

Clamped to 0–100. **80–100 GREEN · 50–79 YELLOW · 0–49 RED.**
Implementation: [`backend/app/services/scoring.py`](backend/app/services/scoring.py) — pure functions, no AI, no I/O.

Unknown ingredients never change the score; they are listed with a warning. When AI is enabled, an ingredient the
knowledge base and rules don't recognize is classified once by Claude and cached in the `ingredients` table, so it is
classified identically from then on.

## Running locally

Prerequisites: Python 3.11+, Node 22+, PostgreSQL 16, `tesseract-ocr`.

```bash
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # set SECRET_KEY; optionally ANTHROPIC_API_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev                     # http://localhost:3000 — /api is proxied to :8000
```

Or the whole stack with Docker:

```bash
cp .env.example .env            # set SECRET_KEY
docker compose up --build       # http://localhost:3000
```

### AI configuration

AI is optional. Without `ANTHROPIC_API_KEY` the app uses Tesseract OCR and the deterministic knowledge base only.
With a key, label photos are read with Claude vision (structured JSON output validated with Pydantic), unknown
ingredients are classified, and results get a short AI-written summary. Default model: `claude-opus-5`
(`AI_MODEL` to change). AI failures and refusals fall back gracefully to the deterministic path.

## Deployment (Vercel + Render)

The Next.js frontend runs on **Vercel**. The FastAPI backend needs the Tesseract binary and PostgreSQL,
which Vercel's serverless functions can't provide, so it runs on **Render** from `backend/Dockerfile`
(any Docker host works). The browser only talks to the Vercel domain; `/api/*` is proxied to the backend,
so session cookies stay first-party.

1. **Generate a proxy secret** (shared by both sides):
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. **Backend on Render** — Dashboard → *New* → *Blueprint* → pick this repo/branch. `render.yaml` creates
   the `guessings-api` Docker service and a PostgreSQL database; migrations run on every start. When prompted,
   set `PROXY_SECRET` (step 1) and optionally `ANTHROPIC_API_KEY`. `SECRET_KEY` is generated for you.
   Note the service URL, e.g. `https://guessings-api.onrender.com`, and check `/api/health` returns `{"status":"ok"}`.
3. **Frontend on Vercel** — *Add New Project* → import this repo → **Root Directory: `frontend`**
   (framework preset Next.js is detected). Environment variables:
   - `BACKEND_URL` = the Render URL from step 2 (used at build time for the proxy — redeploy if it changes)
   - `PROXY_SECRET` = the value from step 1
4. Deploy, open the Vercel URL, register and scan a label.

The backend only trusts the forwarded client IP (used for rate limiting) on requests carrying
`PROXY_SECRET`, so calling the Render URL directly can't bypass the limits. Render's free tier sleeps
after inactivity (first request takes ~30–60 s) and its free PostgreSQL expires after 30 days — use a
paid plan or an external database (e.g. Neon; `postgres://` URLs are accepted) for real use.

## Testing

| Suite | Command | Count |
|-------|---------|-------|
| Backend unit + API/integration (SQLite or PostgreSQL via `DATABASE_URL`) | `cd backend && pytest` | 148 |
| Frontend unit/component (Vitest + Testing Library) | `cd frontend && npm test` | 31 |
| End-to-end, mobile, tablet, accessibility (Playwright + axe) | `cd frontend && npm run build && npm run e2e` | 37 |

Backend tests cover empty/invalid input, case differences, duplicates, synonyms, positions, every scoring rule,
sodium, positives, unknown ingredients, score < 0 and > 100, score and verdict boundaries, JSON schema validation,
determinism (same input → same result), auth/CSRF/rate limiting, authorization between users, upload validation,
OCR on real generated images, AI fallbacks, and error handling without leaking internals.
E2E tests run on desktop, Pixel 7 and tablet viewports and include axe WCAG 2 AA checks in light and dark mode.

## Security

- bcrypt password hashing (SHA-256 pre-hash, no 72-byte truncation), password strength rules
- JWT in `HttpOnly`, `SameSite=Lax` cookies (`Secure` in production) + CSRF double-submit token; Bearer tokens for API clients
- Session revocation on password change; constant-time login (no account enumeration)
- Per-IP rate limits on auth / analysis / general routes and per-account login limits (in-memory or Redis)
- Strict Pydantic validation on all input; upload type sniffing, size/pixel limits, decompression-bomb protection
- Every query scoped to the current user (404 for other users' data)
- Security headers (CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, HSTS in production)
- Friendly error envelopes — no stack traces reach users; secrets only from environment variables
- In production, run the frontend behind a reverse proxy/load balancer that sets `X-Forwarded-For`

## Project layout

```
backend/
  app/core/         config, db, security, rate limiting, error handling
  app/services/     normalization, knowledge_base, patterns, classifier, scoring, insights, ocr, ai, analysis
  app/api/          auth, users, scan, analyses (+ compare, dashboard), products, meta
  alembic/          migrations
  tests/
frontend/
  src/app/          (public) landing/features/how-it-works/privacy/terms · (auth) login/register · (app) screens
  src/components/   ui primitives, analysis (score ring, breakdown, result), scan, layout
  src/lib/          API client, types, validation, queries
  src/test/         Vitest suites
  e2e/              Playwright suites
```

*GuessIngs provides informational, ingredient-based assessments — not medical or dietary advice.*
