# Phase 3 prompt: Tracking + forecasting (dashboard charts + shortfall risk flags)

Paste everything below the line into Claude Code (from the repo root).

---

We're starting **Phase 3: Tracking + forecasting**. Read `CLAUDE.md` first. Phases 0, 1 and 2 are done, so don't redo anything from them. Reuse `services/sim_clock.get_sim_now`, `services/audit.log_event`, the fill rate function in `services/sessions.py`, the helpers in `simulator/rules.py` (`SIM_YEAR`, `SIM_START`, `SIM_END`, `week_start`, `BOOKING_WINDOW_DAYS`) and the react-query setup + `useRefresh` hook on the frontend. Set Current status in CLAUDE.md to "Phase 2 done, Phase 3 in progress".

## Goal of this phase

The training manager opens the Dashboard and in 10 seconds knows: **which courses will miss their 2026 target, by how much, how sure we are, and why**. Concretely:

1. **Tracking:** cumulative actual completions vs target per course, week by week, against a target pace line.
2. **Forecasting:** a simple, explainable time-series forecast of year-end completions per course, with a 90% range and a probability of hitting target.
3. **Risk flags:** each course gets a risk level plus deterministic, human-readable reasons and a **shortfall type** (capacity problem vs attendance problem). When a course becomes at risk, an `alerts` row is opened. Phase 5's agent will read these to decide what kind of fix to propose, so the reasons must be structured, not just text.
4. **Proof it works:** a backtest report showing the forecast is accurate and beats a naive baseline.

No LLM in this phase (alert `message` stays null; the LLM writes it in Phase 6). No constraint checker (Phase 4).

## Backend

### Definitions (put each in one named function with a docstring, reused everywhere)

- **Completion** = an enrollment with status `attended` in a `completed` session in `SIM_YEAR`. It counts in the week of the session's `start_time`. A driver counts once per course per year (Phase 2 already enforces this for new bookings).
- **Week** = Sunday to Saturday, using `week_start`. The year runs from the week containing `SIM_START` to the week containing `SIM_END`.
- **Target pace** at time t = `target × (t − SIM_START) / (SIM_END − SIM_START)` (linear). **Pace gap** = attended − target pace now (negative = behind).
- **Eligible pool** for a course = drivers who are active now, or have a `hire_date` before `SIM_END` (they get activated later), and have not completed the course in `SIM_YEAR`. No forecast may project more new completions than this pool.

### `services/tracking.py`

- `weekly_series(db, course_id=None)`: for every course, every week up to sim now: `attended_in_week`, `no_shows_in_week`, `cumulative_attended`, `target_pace`. Build it from **one grouped query** (course × week), then fill empty weeks with zero in Python. Bucketing by week must work on both SQLite and Postgres: either group by date in SQL and bucket in Python, or use the per-dialect snippet approach from `simulator/views.py`. No SQLite-only SQL.
- `group_breakdown(db, course_id, by="shift"|"nationality"|"depot")`: for each group, active drivers, completed, completion % of group, no-show rate. Used to explain *who* is falling behind (e.g. DEF night shift). Rotating stays its own group.

### `services/forecasting.py` (plain Python + `math`, no numpy/pandas/statsmodels)

**Main model: "pipeline forecast with smoothed rates".** We already know the future schedule, so we don't extrapolate a curve blindly. We forecast the two rates that matter with a time series, then apply them to the seats still on the calendar:

1. **Show-up rate** `p_show` = attended / (attended + no_show), computed per course **per week**, then smoothed with an **exponentially weighted moving average** over the weeks so far (`ALPHA = 0.3`, named constant). Recent weeks matter more, so a seasonal dip or a trainer issue shows up quickly.
2. **Fill rate** `p_fill` for sessions beyond the booking window = seats used / capacity of completed sessions, smoothed the same way.
3. **Shrinkage for small samples:** early in the year, or for small courses (EV has 4 sessions), raw rates are noise. Blend each course rate with the fleet-wide rate using a pseudo-count: `rate = (course_hits + K × fleet_rate) / (course_trials + K)` with `K = 20`. Before any data exists, fall back to priors `PRIOR_SHOW = 0.85`, `PRIOR_FILL = 0.85`. Explain this in a docstring (it's a Beta prior, but keep the explanation plain).
4. **Expected new completions** from each remaining `scheduled` session (start ≥ sim now):
   - session inside the booking window (already has bookings): `n = booked`, `q = p_show`
   - session beyond the window: `n = capacity`, `q = p_fill × p_show`
   - mean `μ = Σ n·q`, variance `σ² = INFLATION × Σ n·q·(1 − q)`. `INFLATION` starts at 1.0 and is tuned by the backtest so the 90% range really contains the final value about 90% of the time.
5. **Projection** = attended + μ, capped at attended + eligible pool. **90% range** = projection ± 1.645σ, clipped to [attended, attended + pool]. **P(hit target)** = `1 − Φ((target − attended − 0.5 − μ) / σ)` using `math.erf` for Φ. Handle σ = 0 (no sessions left) without dividing by zero.
6. **Forecast cone for the chart:** spread each remaining session's mean and variance into its week, accumulate, and return per future week `forecast_mean`, `forecast_low`, `forecast_high`.

**Baselines (only for the backtest and a comparison line, not for flags):**
- `naive_run_rate`: EWMA of weekly completions × weeks remaining. This is the "pure time series" answer that ignores the calendar.
- `linear_extrapolation`: attended ÷ elapsed fraction of the year.

Return a typed result per course (dataclass or Pydantic): `attended, target, target_pace, pace_gap, p_show, p_fill, remaining_sessions, remaining_seats, eligible_pool, projected, low, high, p_hit, naive_projection, risk_level, shortfall_type, reasons[]`.

### Risk rules (`services/risk.py`, deterministic, thresholds as named constants)

- `achieved`: attended ≥ target.
- `high`: P(hit) < 0.40 **or** projected < 90% of target.
- `medium`: P(hit) < 0.75 **or** projected < target.
- `low`: otherwise.
- `insufficient_data`: fewer than `MIN_WEEKS_FOR_FLAG = 4` weeks of completed sessions for that course. Still show the forecast, but don't open alerts.

**Shortfall type** (this tells the Phase 5 agent which tool to reach for):
- `seats_needed = (target − attended) / p_show`.
- `capacity_gap`: even if every remaining seat is filled, `remaining_seats < seats_needed`. Fix = **add sessions**.
- `attendance_gap`: enough seats exist but low fill or show-up rate means they won't convert. Fix = **move drivers to better slots / fill empty seats**.
- `pool_gap`: eligible pool < target − attended (not enough drivers left who need it). Fix = target review, not scheduling.
- `none` when risk is low or achieved.

**Reasons:** a list of structured objects `{code, message, value, benchmark}` generated from facts, ranked by impact, max 4. At least these codes:
- `low_show_rate`: "Show-up rate 61% vs fleet 83%"
- `group_gap`: the worst group from `group_breakdown` by shift, if its completion % is more than 15 points below the best group, e.g. "Night shift completion 38% vs day 66%"
- `recent_cancellations`: sessions of this course cancelled in the last 6 sim weeks (picks up the trainer-leave scenario)
- `capacity_short`: "Only 40 seats left but ~72 needed at current show-up rate"
- `behind_pace`: "64 completions behind target pace"

### Alerts + snapshots (schema change, explain it before making it)

We need forecast history (to draw how the forecast moved and to measure accuracy) and the alert needs its reasons. Proposed changes:
- New table **`forecast_snapshots`**: `id, course_id, as_of (sim time), attended, projected, low, high, p_hit, naive_projection, risk_level, shortfall_type`. Unique on (course_id, as_of).
- `alerts`: add `details` (JSON: p_hit, range, shortfall_type, reasons), `updated_at` (sim time) and `shortfall_type`.

Note in CLAUDE.md that `training.db` must be deleted and re-seeded, and update the data model section.

**Hook into the simulator:** after each simulated day, if the day just processed was a Saturday (week closed), compute forecasts for all courses, write one snapshot per course, and sync alerts. Call this from the advance loop in `simulator/engine.py` through one function `services/tracking_jobs.weekly_close(db)`, so the engine doesn't import forecasting details. Snapshots must be idempotent (re-running a week never duplicates).

**Alert sync rules** (`services/alerts.py`):
- At most **one open alert per course**.
- Course becomes medium/high and has no open alert → create one (`created_at` = sim now, `message` null), audit `alert_opened` with actor `system`.
- Open alert and risk changed → update `risk_level`, numbers, `details`, `updated_at`; audit `alert_escalated` or `alert_deescalated`.
- Open alert and course is back to low or achieved → status `resolved`, audit `alert_auto_resolved`.
- Never touch `dismissed` alerts (a user decision), but if a dismissed course gets *worse* (medium → high), open a new one.

### API: `routers/tracking.py` under `/api/tracking`, plus a read-only `routers/alerts.py`

- `GET /api/tracking/summary`: sim now, % of year elapsed, total attended vs total target, **mandatory compliance %** (mandatory courses only), counts by risk level, open alerts count.
- `GET /api/tracking/courses`: one row per course with all forecast fields, sorted high → medium → low → achieved, then by P(hit) ascending.
- `GET /api/tracking/courses/{id}`: the course row plus `series` (past weeks: cumulative actual + target pace; future weeks: forecast mean/low/high + target pace), `snapshots` (forecast history), `breakdown` by shift and by nationality, `events` (scenario events and session cancellations for this course from `audit_log`, to mark on the chart), and the next 10 scheduled sessions with fill.
- `POST /api/tracking/recompute`: run `weekly_close` logic now (for after manual edits). Audit it.
- `GET /api/alerts?status=open`: list for now; the full inbox with Approve / Reject is Phase 6.

Performance: `/tracking/courses` must use a fixed number of queries regardless of course or session count (aggregate once, compute in Python). No N+1.

### Backtest: `python -m app.services.forecast_backtest --seeds 42 1 2 3 4`

Like `simulator/report.py`: build an in-memory DB per seed, advance week by week to year end (snapshots get written by the hook), then compare snapshots against the final actual. Write `docs/forecast_backtest.md` with:
- **MAE and MAPE** of the year-end projection made at the end of March, June and September, for the pipeline model vs `naive_run_rate` vs `linear_extrapolation`.
- **90% range coverage**: share of snapshots whose range contained the final value. Tune `INFLATION` until coverage is between 85% and 95% and record the chosen value + why.
- **Flag quality**: treat "final < 95% of target" as the truth. Precision and recall of medium/high flags at the June checkpoint, and **lead time** (weeks before year end the course was first flagged and stayed flagged).
- A per-scenario check: DEF flagged with a `group_gap` reason pointing at night shift by mid-year; FA and HAZ flagged after the trainer leave starts (2026-04-19) with `recent_cancellations`; RSR never flagged high.
- Assumptions and limitations in plain words (linear target pace, independence assumption in the variance, etc.).

If the pipeline model doesn't beat both baselines at the June checkpoint, say so honestly in the report and suggest why, don't fudge it.

### Tests (pytest, reuse the seeded fixture)

- Forecast math on tiny hand-built inputs: no remaining sessions → projection = attended, σ = 0, P(hit) is 0 or 1; pool cap applied; shrinkage pulls a 1-session course toward the fleet rate; booked vs unbooked sessions use the right `n` and `q`.
- Risk thresholds at their boundaries; each shortfall type triggered by a crafted case.
- Uses sim time: changing `sim_state` changes target pace; nothing calls `datetime.now()` (grep test like Phase 1 if one exists).
- Scenario test on the seeded DB: advance to ~2026-06-30 → DEF is medium/high with a night-shift `group_gap`; FA has `recent_cancellations`; RSR is low.
- Alerts: one open alert per course after several advances; re-running `weekly_close` for the same week creates no duplicate snapshots or alerts; a course that recovers gets auto-resolved; dismissed alerts aren't reopened unless risk worsens.
- Every alert change writes exactly one `audit_log` row with actor `system`.
- `/tracking/courses` and `/tracking/courses/{id}` return valid data at sim start (no completions yet, no crash, `insufficient_data`).
- All Phase 1 and 2 tests still pass.

## Frontend

Add **Recharts** for charts. Typed `src/api/tracking.ts` and `src/api/alerts.ts`. Add `'tracking'` and `'alerts'` query keys to **every** group in `useRefresh` and to the sim advance/reset invalidation, so the dashboard updates the moment the clock moves.

### Chart rules (keep these consistent everywhere)

- **Risk colours are reserved for risk only:** high = red, medium = amber, low = green, achieved = blue or teal, insufficient data = grey. Always shown as a **badge with an icon + text label**, never colour alone. Chart series never use these colours.
- Series colours: actual = one strong neutral or brand colour (solid 2px line), target pace = grey dashed, forecast = same hue as actual but dotted, 90% range = light shaded band of that hue. Horizontal reference line at the target, labelled.
- **One y-axis per chart.** No dual axes. If two measures have different scales, make two charts.
- Every chart has hover tooltips (crosshair on line charts), a legend when there are 2+ series, and a "Show as table" toggle for accessibility.
- Thin lines, no numbers on every point, light grid. Dates on the x-axis as "Mar", "Apr", etc.
- Never use `toISOString()` for dates (same timezone rule as Phase 2, use the existing helpers).

### Dashboard page (`/`)

1. **KPI tiles row:** Mandatory compliance %, Total completions vs target (with % of year elapsed underneath for context), Courses at risk (high + medium counts as badges), Open alerts, Sim date.
2. **Course risk table:** course, mandatory badge, progress bar (attended / target with a tick at target pace), pace gap, projected year-end with 90% range ("212 (195 to 228)"), P(hit) as %, risk badge, shortfall type, top reason message. Default sort by risk. Row click → course detail.
3. **Small multiples:** a grid of mini line charts, one per course, **y-axis as % of target** so all courses share one scale (0 to 120%). Actual line, target pace dashed, forecast dotted. Risk badge in each card's corner. Click → course detail.
4. Empty / early state: at sim start show "Not enough data yet, advance the simulation" with a link to the Simulation page instead of empty charts.

### Course detail page (`/dashboard/courses/:id`)

- Header: course name, risk badge, shortfall type explained in one plain sentence (e.g. "Capacity problem: even full sessions can't reach target. Adding sessions is the likely fix.").
- **Main chart:** cumulative actual (solid) to sim now, target pace (dashed) for the full year, forecast mean (dotted) + 90% band from sim now to Dec 31, target reference line, a vertical "Sim now" line, and small markers for events (trainer leave, cancellations) with tooltips.
- **Reasons panel:** the structured reasons as a list with value vs benchmark.
- **Who is behind:** horizontal bar chart of completion % by shift, and a second one by nationality (completion % of group, sorted). Show group sizes so small groups aren't over-read.
- **Forecast history:** line of projected year-end over the weekly snapshots with the target line, so you can see the forecast reacting to events.
- **Weekly completions:** bar chart of attended per week (separate chart from the cumulative one).
- **Upcoming sessions:** next 10 with fill badges; click opens the existing session drawer from Phase 2.

### Small extras

- Sidebar: show the number of high-risk courses as a small red badge next to Dashboard.
- Simulation page: after an advance, show "Risk changes this run" (alerts opened / escalated / resolved) using the alerts endpoint.
- A "Recompute" button on the dashboard calling `POST /api/tracking/recompute`.

## Done when

- Advancing the sim updates the dashboard without a page reload, and risk flags change over time the way the scenarios predict (DEF and FA/HAZ go red/amber, RSR stays green).
- Every course has a forecast with a range, P(hit), risk level, shortfall type and at least one reason when at risk.
- Alerts are opened, updated and auto-resolved correctly, with audit rows.
- `docs/forecast_backtest.md` exists with MAE vs baselines, coverage, flag precision/recall and lead time.
- `pytest` passes (old + new) and `npm run build` passes with no type errors.

## Process

Follow CLAUDE.md: give me a short plan first (files to add/change and why, the schema change and why, npm packages). Build the backend first: forecasting + risk with unit tests, then the hook + alerts, then the API, then the backtest. Test before starting the frontend. After building, actually delete and re-seed `training.db`, run pytest, start the server, advance the sim to the end of June, hit `/api/tracking/courses` and check the scenario courses look right, run the backtest, and run `npm run build`; fix errors before saying it's done. Update `package.json` if anything was installed (no new Python packages should be needed). Finish with: what changed, PowerShell commands to run and check it, a quick manual test checklist for me (5 to 8 clicks), the key backtest numbers in 3 lines, a suggested commit message, and update the Current status line in CLAUDE.md to "Phase 3 done". Don't start Phase 4.
