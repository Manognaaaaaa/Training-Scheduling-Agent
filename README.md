# Training Optimiser

A mini ERP for a driver training department. It tracks annual training targets against actual completions per course, detects shortfall risk, and uses an agentic LLM planner to propose schedule changes. Every proposed plan is checked by a deterministic constraint checker, ranked, explained to the trainer in plain language, and (once approved) synced to Google Calendar. A responsible-AI layer covers hallucination checks, fairness of reallocation burden, and a full audit log.

Full brief: [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md)

## Stack

- **Backend:** FastAPI (Python 3.12), SQLAlchemy 2.0, pydantic-settings
- **Frontend:** React + Vite + TypeScript, Tailwind CSS, React Router
- **Database:** SQLite in dev, Postgres when deployed
- **LLM:** Groq API (`GROQ_API_KEY`, `GROQ_MODEL` in `backend/.env`), behind one interface in `backend/app/llm/` (wired in Phase 5)
- **Calendar:** Google Calendar API (sandbox calendar)

## Running it (Windows, PowerShell)

### Backend

First time only:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Every time:

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The API runs on http://localhost:8000 and the interactive docs are at http://localhost:8000/docs.
Check http://localhost:8000/api/health: it should return `{"status":"ok","database":"ok","tables":11}`.

### Synthetic data and simulator (Phase 1)

Run from `backend/` with the virtual environment active. The app needs seeded data before the Simulation page shows anything.

```powershell
python -m app.simulator.seed --seed 42 --reset   # drop and regenerate the 2026 year (same seed = same data)
python -m app.simulator.report                   # writes docs/synthetic_data_report.md
pytest -q                                        # tests use an in-memory database
```

The Simulation page (http://localhost:5173/simulation) moves the simulated clock forward; the same controls exist at `/api/sim/advance`, `/api/sim/state`, `/api/sim/progress` and `/api/sim/reset` (see `/docs`).

### Frontend

First time only:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
```

Every time:

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173. The sidebar footer shows a green "API connected" badge when the backend is running, and a red "API offline" badge when it is not.

## Structure

- `backend/` : API, simulator, agent, services
- `frontend/` : React app
- `docs/` : project brief and notes

## Build phases

| # | Phase | Status |
|---|---|---|
| 0 | Foundation: repo, FastAPI + React skeletons, DB schema | Done |
| 1 | Synthetic data + simulator | Done |
| 2 | ERP core: CRUD pages + calendar view | Next |
| 3 | Tracking + forecasting: dashboard charts, shortfall risk flags | |
| 4 | Constraint checker (built before the agent) | |
| 5 | Agent planner: LLM produces N structured plans from real DB lookups | |
| 6 | Ranking + alerts inbox: scored plans, LLM alerts, Approve / Reject | |
| 7 | Calendar sync + live updates | |
| 8 | Responsible AI: audit log, fairness panel, hallucination catch rate | |
| 9 | Eval, polish, deploy | |
