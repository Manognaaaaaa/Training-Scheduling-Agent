# Phase 2 prompt: ERP core (CRUD + calendar view)

Paste everything below the line into Claude Code (from the repo root).

---

We're starting **Phase 2: ERP core**. Read `CLAUDE.md` first. Phases 0 and 1 are done, so don't redo anything from them. Reuse the existing models, `services/sim_clock.get_sim_now`, `services/audit.log_event` and the helpers in `simulator/rules.py` (especially `is_driver_free`, `session_end`, `week_start`). Set Current status in CLAUDE.md to "Phase 1 done, Phase 2 in progress".

## Goal of this phase

Turn the app into a real mini ERP: a training admin can view, search, create, edit and retire **drivers, trainers, courses (with their 2026 target) and sessions**, manage who is enrolled in a session, and see the whole year on a **calendar coloured by fill rate**. Every change a user makes goes to `audit_log`. No LLM, no forecasting (that's Phase 3), no full constraint checker (that's Phase 4).

No schema changes should be needed. If you think one is, explain why before making it.

## Backend

### General rules for every CRUD endpoint

- One router file per resource in `backend/app/routers/`, all under `/api`. Pydantic schemas per resource in `backend/app/schemas/` with separate `Create`, `Update` (all fields optional, used for PATCH) and `Out` models.
- List endpoints return a page object: `{ items, total, page, page_size }`. Support `page` (default 1), `page_size` (default 25, max 200), `sort` (field name, prefix `-` for descending, whitelist the allowed fields) and the filters listed below.
- Errors: 404 for unknown id, 409 for conflicts (duplicate code, delete blocked, rule clash), 422 for bad input. Error body always has a readable `detail` string the UI can show as is.
- "Now" is always `get_sim_now(db)`, never the real clock (CLAUDE.md rule 6).
- **Audit every write**: `log_event(actor="user", action="<entity>_created|updated|deleted|deactivated|cancelled", entity_type, entity_id, details)`. For updates, `details` holds only the changed fields as `{field: [old, new]}`. Put the diff helper in `services/audit.py`.
- Keep business logic out of routers: routers call functions in `backend/app/services/` (e.g. `services/sessions.py`, `services/enrollments.py`).

### Drivers: `/api/drivers`

- List filters: `q` (matches name or employee_code, case insensitive), `nationality`, `shift`, `depot`, `is_active`.
- Create: `employee_code` auto-generated as the next `DRV-xxxx` if not given; must be unique.
- **No hard delete** (drivers have training history). `DELETE /api/drivers/{id}` sets `is_active = false` and cancels that driver's future `booked` enrollments. Log it as `driver_deactivated` with the number of cancelled bookings.
- `GET /api/drivers/{id}` also returns: training history (course, session date, status) and upcoming bookings.
- `GET /api/drivers/{id}/unavailability`, `POST` to add a block (start, end, reason), `DELETE /api/drivers/{id}/unavailability/{uid}`. Adding a block cancels any future `booked` enrollments it overlaps (same behaviour as sick days in the simulator).
- `GET /api/drivers/options` returns distinct nationalities, shifts and depots for filter dropdowns.

### Trainers: `/api/trainers`

- List filter: `q` on name. Each item also includes `sessions_this_week` (week containing sim now, via `week_start`) so the UI can show load vs `max_sessions_per_week`.
- Delete: 409 if the trainer has any scheduled or completed sessions; the message says how many and suggests reassigning them. Otherwise hard delete.
- Editing `max_sessions_per_week` below the number of sessions they already have in some future week is allowed, but return a `warnings` list in the response naming those weeks.

### Courses: `/api/courses`

- Each course item includes its `target_completions` for `SIM_YEAR` (joined from `training_targets`), and the create/update schemas accept it too, so the UI edits course + target in one form. Create or update the `TrainingTarget` row in the same transaction.
- `code` unique (409 on clash).
- Delete: 409 if the course has any sessions. Otherwise delete the course and its target.

### Sessions: `/api/sessions`

- List filters: `course_id`, `trainer_id`, `status`, `source`, `start_from`, `start_to`. Each item includes course code/name, trainer name, `booked`, `attended`, `no_show` counts and `fill_rate` (see calendar section).
- Create (from the UI): `source = "manual"`, `status = "scheduled"`. `end_time` is computed with `session_end(start, course.duration_hours)` unless given; `capacity` defaults to the course's `default_capacity`.
- **Light validation for now** (put it in `services/sessions.py` as small named functions, Phase 4 will fold these into the real constraint checker): start must be after sim now; start hour in `SESSION_START_HOURS` and weekday in `SESSION_WEEKDAYS` (reject with a clear message otherwise); trainer not double booked; trainer not over `max_sessions_per_week` for that week; capacity between 1 and 30.
- Update: only `scheduled` sessions in the future can be edited. Changing time or trainer re-runs the checks above. Lowering capacity below the current number of booked drivers → 409.
- `completed` and `cancelled` sessions are read-only (409 on edit).
- **No hard delete.** `POST /api/sessions/{id}/cancel` sets status `cancelled` and cancels its `booked` enrollments. Log it with the count.

### Enrollments (nested under sessions)

- `GET /api/sessions/{id}/enrollments` → driver code, name, shift, nationality, status.
- `POST /api/sessions/{id}/enrollments` body `{ driver_id }`. Reject (409, with the reason) if: session not scheduled or already started, session full, driver inactive, driver already enrolled in this session, driver already attended this course in 2026, driver booked in an overlapping session, or `is_driver_free` returns False (show its reason, e.g. "less than 8h rest after the shift").
- `DELETE /api/sessions/{id}/enrollments/{enrollment_id}` sets status `cancelled` (not a hard delete).
- `GET /api/sessions/{id}/eligible-drivers?q=` returns active drivers who would pass all the checks above (limit 50), so the UI only offers valid choices. Do this efficiently: load the session's time window, the relevant unavailability rows and overlapping enrollments once, then loop in Python. No N+1 queries.

### Calendar: `GET /api/calendar`

- Query: `start`, `end` (required, max 62 days apart), optional `course_id`, `trainer_id`, `include_cancelled` (default false).
- Returns a flat list of lightweight events: id, course code/name, trainer name, start, end, location, capacity, status, source, booked, attended, `fill_rate`, `fill_band`.
- **Fill rate definition** (put it in one function in `services/sessions.py` with a docstring, it's reused in Phase 3):
  - scheduled session: `booked / capacity`
  - completed session: `attended / capacity`
  - cancelled: `null`
- `fill_band`: `low` (< 50%), `medium` (50 to 79%), `high` (≥ 80%), `cancelled`. Thresholds as named constants.
- Also return `sim_now` in the response so the calendar can draw a "now" line and open on the current week.
- Must be one or two queries total (join + group by), not one per session. A month view has ~100+ sessions.

### Tests (pytest, reuse the seeded in-memory DB fixture from `conftest.py`)

- CRUD happy path for drivers, trainers, courses, sessions (create, get, list with filter, patch, delete/deactivate/cancel).
- 404 on unknown ids; 409 on duplicate `employee_code` and course `code`; 409 deleting a trainer or course that has sessions.
- Deactivating a driver cancels only their future booked enrollments.
- Creating a session: rejected in the past, on a Friday, at 11:00, with a double-booked trainer, and over trainer weekly load.
- Enrollment: rejected when full, when driver already attended the course, and when `is_driver_free` fails; `eligible-drivers` never returns someone that `POST` would reject (check a sample).
- Completed sessions can't be edited.
- Every write adds exactly one `audit_log` row with actor `user`, and an update's details contain only changed fields.
- Calendar: correct fill rate and band for a scheduled and a completed session; range over 62 days → 422.
- All Phase 1 tests still pass.

## Frontend

Add **`@tanstack/react-query`** for data fetching and cache invalidation (Phase 7 auto refresh will build on it). After any mutation, invalidate the affected queries. Also invalidate everything after a sim advance or reset on the Simulation page, so other pages never show stale data.

Add **FullCalendar** (`@fullcalendar/react`, `@fullcalendar/daygrid`, `@fullcalendar/timegrid`, `@fullcalendar/interaction`) for the calendar. Only the free MIT plugins.

Typed API modules in `src/api/` (one per resource), reusing `apiFetch`. Make `apiFetch` throw an error that carries the backend's `detail` message so the UI can show it.

### ⚠️ Timezone gotcha (important)

Backend datetimes are **naive** (no timezone) and mean Dubai local time. Never use `toISOString()` to send a date to the API: it converts to UTC and shifts every session by 4 hours. Write one helper `toApiDateTime(date)` in `src/utils/datetime.ts` that formats as `YYYY-MM-DDTHH:mm:ss` in local time, and use it everywhere. Configure FullCalendar with `timeZone: 'local'`.

### Reusable components (`src/components/`)

- `DataTable`: columns config, server-side pagination, sortable headers, loading and empty states.
- `FormModal` (or drawer) for create/edit, with field-level errors from 422 and a banner for 409 `detail`.
- `ConfirmDialog` for deactivate/delete/cancel, showing what will happen (e.g. "This will cancel 3 upcoming bookings").
- `Toast` for success and error messages.
- `Badge` for status, shift and fill band.

Keep styling consistent with the existing Tailwind shell (slate palette). No UI kit needed.

### Master Data page

Tabs: **Drivers | Trainers | Courses | Sessions**, tab kept in the URL (`/master-data?tab=drivers`).

- **Drivers:** search box (debounced), filters for nationality, shift, depot, active; columns code, name, nationality, shift, depot, hire date, active badge. Row click opens a **driver detail drawer**: profile, training history, upcoming bookings, unavailability list with add/remove. Buttons: Add driver, Edit, Deactivate.
- **Trainers:** name, max sessions/week, "this week: 3 / 5" load bar. Add, edit, delete (show the 409 message nicely if blocked).
- **Courses:** code, name, duration, capacity, mandatory badge, 2026 target. Add, edit (including target), delete.
- **Sessions:** filters (course, trainer, status, date range), columns date/time, course, trainer, location, booked/capacity, fill badge, status, source. Row click opens the same **session drawer** used by the calendar.

### Session drawer (shared by Master Data and Calendar)

- Session details, with Edit and Cancel session buttons (hidden if not editable).
- Enrollment list with status badges and a remove button for `booked` rows.
- **Add driver**: a searchable picker backed by `/eligible-drivers`, so only valid drivers appear. If the POST still fails, show the backend reason.

### Calendar page

- Week view by default (time grid, 07:00 to 22:00, Sunday first day, Friday/Saturday shown but greyed), plus Month view toggle.
- Opens on the **current sim week** and draws a "now" indicator at sim time (not real time). A "Go to sim now" button.
- Events coloured by `fill_band` (e.g. red low, amber medium, green high, grey cancelled). Completed sessions look muted/striped so past vs future is obvious. Event text: course code, `booked/capacity`, trainer.
- Filters above the calendar: course, trainer, show cancelled. A small legend explaining the colours and the fill rate definition.
- Fetch by the visible range via `/api/calendar` (use FullCalendar's `datesSet` to get the range).
- Click an event → session drawer. Click an empty slot in the future → create session modal prefilled with that start time (backend validation decides if it's allowed).
- Restrict navigation to 2026.

## Done when

- All CRUD endpoints work from `/docs` and from the Master Data page, with filters, sorting and pagination.
- Invalid actions show the backend's reason in the UI instead of failing silently.
- Calendar shows the year's sessions coloured by fill rate, opens on sim now, and updates after a sim advance.
- Every user change appears in `audit_log`.
- `pytest` passes (old + new tests) and `npm run build` passes with no type errors.

## Process

Follow CLAUDE.md: give me a short plan first (files to add/change and why, and the npm packages you'll add), then build. Build the backend first and test it before starting the frontend. After building, actually run pytest, start the server, hit a few endpoints, and run `npm run build`; fix errors before saying it's done. Update `requirements.txt` (UTF-8, `Out-File`) and `package.json` if anything was installed. Finish with: what changed, PowerShell commands to run and check it, a quick manual test checklist for me (5 to 8 clicks to try in the UI), a suggested commit message, and update the Current status line in CLAUDE.md to "Phase 2 done". Don't start Phase 3.
