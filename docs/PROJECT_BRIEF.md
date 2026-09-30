# Project Brief: Dynamic Training Efficiency & Smart Calendar Optimiser

## Original topic (as given)

**5. Dynamic Training Efficiency & Smart Calendar Optimiser**

**Target capabilities:** annual target vs actual tracking · shortfall detection & trainer alerts · smart slot redistribution suggestions · calendar integration.

**Generative core:** Agentic LLM planner that samples multiple candidate schedules (stochastic plan generation), scores them against constraints, and presents the best options, plus LLM-generated natural-language alert messages.

**Steps**
- Simulate the domain: generate a synthetic year of training targets, session calendars, driver rosters, and attendance streams (this synthetic-data generator is itself a graded generative component).
- Build the tracking engine: cumulative completion vs. target curves, shortfall-risk forecasting (simple time-series model).
- On shortfall risk: the LLM agent samples N candidate redistribution plans (move drivers to low-attendance slots, add sessions), each validated by a hard-constraint checker (capacity, driver availability, rest rules).
- Rank valid plans, draft the trainer alert with justification, and write accepted changes to a calendar API (Google Calendar sandbox).
- Responsible-AI layer: hallucination (the agent must never reference non-existent drivers/slots; measure constraint-checker catch rate); fairness (reallocation burden must not concentrate on one driver group, e.g. night shift, one nationality); full audit log of agent decisions.

## End goal

A fully working, live web app (mini ERP for a training department), not just scripts. It updates as data flows in.

### App pages
- Dashboard: target vs actual per course, at-risk flags
- Master data (ERP CRUD): drivers, trainers, courses, slots
- Calendar view: sessions color-coded by fill rate
- Alerts inbox: shortfall alerts with N ranked plans, Approve / Reject
- Audit log: every agent decision and why
- Fairness panel: burden distribution by shift / nationality
- Simulation control: simulated clock ("fast-forward 1 week") that streams attendance so the system feels live

## Architecture

```
React frontend (dashboard, CRUD, calendar, alerts, audit)
        |  REST + live updates
        v
FastAPI backend
 |- CRUD APIs
 |- Simulator (clock + attendance stream)
 |- Tracking + Forecasting service
 |- Agent Planner (LLM, samples N plans)
 |- Constraint Checker
 |- Ranker + Alert Writer (LLM)
 |- Calendar Sync (Google Calendar)
 |- Audit + Fairness service
        |
        v
Database (SQLite dev, Postgres deployed)
```

## Build phases

| # | Phase | Output |
|---|---|---|
| 0 | Foundation | Repo, FastAPI + React skeletons, DB schema |
| 1 | Synthetic data + simulator | Seeded DB, clock that streams attendance |
| 2 | ERP core | CRUD pages + calendar view |
| 3 | Tracking + forecasting | Dashboard charts, shortfall risk flags |
| 4 | Constraint checker | Validator with rejection reasons (built BEFORE the agent) |
| 5 | Agent planner | LLM producing N structured plans via real DB lookups |
| 6 | Ranking + alerts inbox | Scored plans, LLM alerts, Approve / Reject |
| 7 | Calendar sync + live updates | Approved plans to Google Calendar, auto-refresh UI |
| 8 | Responsible AI | Audit log page, fairness panel, hallucination catch rate |
| 9 | Eval, polish, deploy | Metrics report, hosted link |

## Status / decisions log
- 2026-09-30: Scope and phases agreed. Next: Phase 0. Pending decision: which LLM API (OpenAI / Claude / Gemini / Groq / Ollama).
