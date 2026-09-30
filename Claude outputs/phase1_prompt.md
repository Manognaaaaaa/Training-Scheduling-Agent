# Phase 1 prompt: Synthetic data + simulator

Paste everything below the line into Claude Code (from the repo root).

---

We're starting **Phase 1: Synthetic data + simulator**. Read `CLAUDE.md` first. Phase 0 is done, so don't redo anything from it. The 11 tables in `backend/app/models/` already exist; reuse them.

## Housekeeping first

1. Update `CLAUDE.md`: the LLM line should say **Groq API** (`GROQ_API_KEY`, `GROQ_MODEL` in `backend/.env`, still behind `backend/app/llm/`, wired in Phase 5). Set Current status to "Phase 0 done, Phase 1 in progress".
2. `backend/requirements.txt` is saved as UTF‑16 (PowerShell `>` redirect). Re-save it as UTF‑8. From now on update it with `pip freeze | Out-File -Encoding utf8 requirements.txt`, and add that command to the "How to work" section of CLAUDE.md.

## Goal of this phase

A deterministic generator that fills the DB with one realistic year of training data, plus a **simulated clock** that, when advanced, "plays out" the year: attendance happens, drivers get booked, people get sick, trainers go on leave. The data must contain **built-in problems** so later phases (forecasting, agent) have real shortfalls to detect and fix. The generator is a graded generative component, so it also needs a validation report.

No LLM in this phase. Plain Python with `random.Random(seed)`, no global `random` calls.

## Domain rules (put these in `backend/app/simulator/rules.py`)

These constants will be reused by the Phase 4 constraint checker, so keep them in one importable module with docstrings.

- `SIM_YEAR = 2026`, sim starts `2026-01-01 00:00`.
- Shifts: day `06:00–14:00`, night `22:00–06:00`, rotating (alternates day/night weekly, derive week parity from ISO week number).
- Session slots: `09:00`, `14:00`, `18:00` start times, Sunday to Thursday (UAE work week). Session length = course `duration_hours` (cap at 4h per session; longer courses just use 4h sessions, keep it simple).
- **Rest rule:** a driver can't attend a session that starts within 8 hours after their shift ends, or overlaps their shift. Write a helper `is_driver_free(driver, start, end, unavailability_rows) -> (bool, reason)` that the seed, the simulator and later the constraint checker all use.
- Trainer weekly load: no more than `max_sessions_per_week` sessions; no double booking.
- Booking window: drivers get booked into sessions starting within the next **21 days**.
- Ramadan 2026 approx `2026-02-18` to `2026-03-19`, summer peak `2026-07-01` to `2026-08-31`. Hard-code as constants with a comment saying they're approximate.

## Seed data (`backend/app/simulator/seed.py`)

Run with: `python -m app.simulator.seed --seed 42 --reset` (from `backend/`). `--reset` drops and recreates all tables. Same seed must give byte-identical data.

- **~300 drivers.** Nationality mix realistic for a Dubai transport operator (Indian, Pakistani, Filipino, Bangladeshi, Nepali, Egyptian, Sri Lankan, Emirati, other). Use small hand-written first/last name lists per nationality in `simulator/names.py` (no Faker). Shift mix roughly 50% day, 35% night, 15% rotating. 4 depots. Hire dates spread over past 10 years, ~5% hired during 2026 (inactive until hire date is passed; `is_active` flips in the simulator). `employee_code` like `DRV-0001`.
- **~10 trainers**, `max_sessions_per_week` 4 to 6.
- **8 courses**, mix of mandatory and optional, e.g. Defensive Driving, Road Safety Refresher, First Aid, Fuel-Efficient Driving, Customer Service, Heat Stress Awareness, EV Handling, Hazmat Awareness. Realistic `duration_hours` and `default_capacity` (8 to 15).
- **Training targets for 2026:** mandatory courses target ≈ 85–95% of active drivers; optional courses smaller.
- **Sessions for the whole year**, spread across weeks, respecting trainer load and no double booking. Total planned capacity per course should be around 110–130% of target (so the plan looks fine on paper).
- **Enrollments:** only for sessions in the first 21 days (the rest get booked by the simulator as the clock moves). Eligible driver for a course = active, hasn't attended that course in 2026, not already booked in a future session of it, and `is_driver_free`.
- **Driver unavailability:** annual leave blocks (2 to 4 weeks, heavily clustered in Jul–Aug), plus a few pre-known absences. Reason field set.
- `sim_state` row id=1 at `2026-01-01 00:00`.
- Write an `audit_log` row: actor `system`, action `seed_created`, details include seed and row counts.

### Built-in scenarios (`simulator/scenarios.py`)

The data must produce shortfalls **by itself** if nobody intervenes. Implement these as clearly named, documented scenarios so I can explain them in my report:

1. **Night-shift mismatch:** one mandatory course (e.g. Defensive Driving) has most sessions at 09:00, so night-shift drivers mostly can't be booked or no-show. Expected result: this course falls behind, and the gap is concentrated on night shift (useful for the fairness panel later).
2. **Trainer leave:** on a set date in Q2 one trainer goes on 6 weeks of unplanned leave; the simulator cancels their sessions in that window when the clock reaches the event date (not at seed time). Log it to `audit_log`.
3. **Seasonal dips:** lower attendance during Ramadan and the summer peak.
4. **One healthy course** that finishes on or above target, as a control.

Scenario events with dates live in code as a list; the simulator applies each one once when the clock passes its date. Record applied events in `audit_log` so they don't re-run.

## Simulator (`backend/app/simulator/engine.py`)

`advance(db, days: int) -> AdvanceSummary` processes **one day at a time** (so Phase 7 can stream it). For each day:

1. Apply any scenario events dated that day.
2. Activate drivers whose `hire_date` is reached.
3. Roll new sick-day unavailability (small daily probability, 1 to 3 days) and cancel affected future `booked` enrollments.
4. For every `scheduled` session whose `end_time` is that day: decide attendance for each `booked` enrollment → `attended` or `no_show`, then mark the session `completed`.
   - Attendance probability: base ~0.88, minus penalties (night shift + morning session, Ramadan, summer, driver on unavailability = always no_show). Keep the model in one small documented function.
   - **Determinism across step sizes:** use a per-decision RNG, e.g. `random.Random(hash_tuple(seed, session_id, driver_id))` built from a stable hash (hashlib, not Python `hash()`), so advancing 7+7 days gives exactly the same result as 14.
5. Book drivers into sessions starting in the next 21 days using the eligibility rules. Booking fill should be imperfect (not every seat filled), and no-show drivers become eligible again.
6. Move `sim_state.current_time` forward.

One `audit_log` row per advance call (actor `system`, action `sim_advanced`, details = the summary), not one per enrollment.

`AdvanceSummary` (Pydantic, in `backend/app/schemas/sim.py`): from/to time, sessions completed, attended, no_shows, new bookings, cancellations, sick events, scenario events applied, and a per-day breakdown list.

Stop at year end (don't advance past `2026-12-31 23:59`).

## API (`backend/app/routers/sim.py`, prefix `/api/sim`)

- `GET /state` → current sim time, % of year elapsed, and quick totals.
- `POST /advance` body `{ "days": 1..90 }` → `AdvanceSummary`.
- `POST /reset` body `{ "seed": 42 }` (optional) → reseed and return state.
- `GET /progress` → per course: target, attended so far, booked upcoming, planned capacity remaining. (Rough version only; real tracking is Phase 3.)

Add a helper `get_sim_now(db)` in `backend/app/services/sim_clock.py` and use it everywhere "now" matters (CLAUDE.md rule 6).

## Frontend: Simulation control page

Replace the placeholder Simulation page with a simple working version: current sim time, buttons **+1 day, +1 week, +1 month, Reset**, the last advance summary as a small table, and the `/progress` table below. Typed calls in `src/api/`. Nothing fancy; charts come in Phase 3.

## Validation report (`python -m app.simulator.report`)

Because the generator is graded, write `docs/synthetic_data_report.md` automatically:

- Row counts per table; nationality, shift and depot distributions; sessions per course and per trainer; fill rate at seed.
- A **full-year dry run** on a temporary copy of the DB (don't touch `training.db`): final attended vs target per course, no-show rate by shift and by month.
- A check that the scenarios did what they should (night-shift course behind, trainer-leave dip visible, control course on target). Print PASS/FAIL per check.
- A short "assumptions" section listing the rules and probabilities used.

## Tests (`backend/tests/`, pytest)

Add `pytest` to requirements. Tests use a fresh in-memory SQLite DB.

- Same seed → identical counts and identical first 20 enrollments.
- Advancing 7 + 7 days == advancing 14 days (same attended/no_show outcomes).
- No session over capacity; no trainer double-booked or over weekly load; no driver booked in two overlapping sessions.
- No booking violates `is_driver_free` (shift overlap, rest rule, unavailability).
- Trainer-leave sessions are cancelled only after the event date.
- Can't advance past year end.

## Done when

- `python -m app.simulator.seed --seed 42 --reset` works; running it twice gives the same data.
- `/api/sim/advance` works from `/docs` and from the Simulation page; sim time moves and attendance appears.
- `pytest` passes.
- `docs/synthetic_data_report.md` is generated and all scenario checks PASS.

## Process

Follow CLAUDE.md: give me a short plan first (files to add/change and why), then build. If you think a schema change is needed, explain why before making it. After building, actually run the seed, the report, pytest, the server and the frontend build, and fix errors. Finish with: what changed, PowerShell commands to run and check it, a suggested commit message, and update the Current status line in CLAUDE.md to "Phase 1 done". Don't start Phase 2.
