# CodeLens

GitHub-based PR intelligence tool. Understand a Pull Request before performing a detailed manual code review.

> **MVP — Phase 1: GitHub Foundation.**

This phase implements GitHub App authentication, PR URL input, and fetching of PR metadata, changed files, and diff. Analysis/risk/map features come in later phases.

## Monorepo layout

```
codelens/
├── frontend/   # Next.js + React + TS + Tailwind
└── backend/    # FastAPI + Pydantic
```

## Prerequisites

- Node.js >= 20
- Python >= 3.11

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # then fill in values
uvicorn main:app --reload --port 8000
```

Health check: http://localhost:8000/api/health

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and paste a GitHub PR URL.

## Environment variables

See `backend/.env.example`. Two auth modes are supported:

- **GitHub App** (preferred): `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY_PATH` (or `GITHUB_PRIVATE_KEY`), `GITHUB_INSTALLATION_ID`
- **PAT fallback** (local dev only): `GITHUB_TOKEN`

If both are configured, the GitHub App takes precedence.

## API

- `GET /api/health` — liveness
- `POST /api/analyze` — body `{ "pr_url": "https://github.com/owner/repo/pull/123" }` → PR metadata, changed files, diff
