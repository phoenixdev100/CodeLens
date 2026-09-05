# CodeLens — Project Guide

## Stack

- **Frontend**: Next.js (App Router) + React + TypeScript + Tailwind CSS
- **Backend**: Python + FastAPI + Pydantic
- **GitHub**: GitHub App (JWT → installation token) with PAT fallback for local dev
- **AI**: provider abstraction with mock fallback (Phase 4+)
- **State**: stateless (no DB for MVP)

## Commands

### Backend
```bash
cd backend
.venv\Scripts\activate           # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
pytest                           # tests
```

### Frontend
```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
npm run build                    # production build
npm run lint
```

## Environment

Backend reads `.env` in `backend/`. See `backend/.env.example`.

Required for GitHub App auth: `GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY_PATH`, `GITHUB_INSTALLATION_ID`.
Fallback for local dev: `GITHUB_TOKEN`.

Frontend talks to backend at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Architecture notes

- Backend is organized by domain: `github/` (auth + API client), `api/` (routes), `models/` (Pydantic schemas), `context/` (repository context builder), `analysis/` (deterministic analysis engine), `ai/` (AI provider abstraction), `risk/` (risk engine), `priority/` (review priority engine), `impact_map/` (graph builder), `phase4.py` (Phase 4 orchestrator), `config.py` (settings).
- Phase 1 (`/api/analyze`): GitHub auth + PR fetch + diff.
- Phase 2 (`/api/context`): repository context — file classification, diff parsing, content retrieval, import/dependency detection, test mapping.
- Phase 3 (`/api/analyze-signals`): deterministic analysis — change, critical areas, security, quality, tests. No AI, no risk score, no priority.
- Phase 4 (`/api/analyze-full`): full pipeline — Phase 3 analysis + AI insights + risk scoring + review priority. Uses mock AI provider if no OpenAI key is configured.
- Phase 5 (`/api/impact-map`): visual Impact Map — graph of changed files, connected dependencies, test files, and functional areas with risk/severity visualization data. Frontend renders with React Flow (`@xyflow/react`).
- Phase 6: complete enterprise dashboard UI — light/white theme, sidebar navigation, Overview/Risk/Priority/Findings/Impact Map/Diff tabs, finding detail drawer, demo mode with mock data.
- AI reasoning lives in `backend/ai/` behind a provider interface (`AIProvider` ABC; `MockAIProvider` fallback; `OpenAIProvider` for real calls).
- Risk weights are configurable via `backend/config.py` (defaults: Change 15, Scope 15, Critical 25, Security 20, Quality 10, Tests 15).
- Impact Map reuses Phase 2 `DependencyGraph`, Phase 3 findings, and Phase 4 risk/priority — does not create a second dependency system.
- Frontend mirrors backend schemas in `frontend/types/`. Dashboard at `/dashboard?pr=URL` or `/dashboard?demo=1`.

## MVP boundaries

Phases 1-6 implemented: GitHub auth, PR fetch, diff, repository context, deterministic analysis, AI insights, risk scoring, review priority, Impact Map with React Flow, and complete enterprise dashboard UI.
No PostgreSQL, Redis/Celery, webhooks, multi-language, or advanced security scanning (post-MVP).
