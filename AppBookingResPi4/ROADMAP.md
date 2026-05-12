# AppBookingResPi4 — Roadmap

Phases are ordered by value-to-complexity ratio. Each phase is independent.
Every enhancement must follow the Karpathy principles: think before adding,
keep it simple, surgical changes only.

---

## Phase 1 — Core booking CRUD API (in progress)

**Goal:** Full REST API so the dashboard and external clients can create, read,
update, and cancel reservations.

**Plan:** `.plans/2026-05-02-core-booking-api/`

| Endpoint | Status |
|---|---|
| `GET  /api/bookings` | ✓ scaffolded |
| `POST /api/bookings` | ⬜ planned |
| `GET  /api/bookings/:id` | ⬜ planned |
| `PUT  /api/bookings/:id` | ⬜ planned |
| `DELETE /api/bookings/:id` | ⬜ planned |
| `GET  /api/resources` | ⬜ planned |

---

## Phase 2 — Dashboard create/cancel UI

**Goal:** Let users create and cancel bookings from the web dashboard without
needing curl.

**Deliverables:**
- `web/index.html` — add a "New Booking" form (resource dropdown, user, note, date/time pickers)
- `web/index.html` — add a "Cancel" button per row that calls `DELETE /api/bookings/:id`
- `src/api.c` — already done in Phase 1

**Upgrade path:** Only `web/index.html` changes. No C source changes needed.

---

## Phase 3 — Resource management

**Goal:** Make the resource list configurable at runtime instead of hardcoded.

**Deliverables:**
- New `resources` table in SQLite
- `GET /api/resources` reads from DB
- `POST /api/resources`, `DELETE /api/resources/:name` for admin CRUD
- `web/index.html` — resource dropdown populated from API

---

## Phase 4 — Date-range filtering

**Goal:** Allow clients to query bookings within a time window.

**Deliverables:**
- `GET /api/bookings?from=<ts>&to=<ts>` — add optional query params to list endpoint
- `src/storage.c` — `storage_booking_list_range()` with start/end filters
- `web/index.html` — date range filter controls on the dashboard

---

## Phase 5 — Authentication (basic)

**Goal:** Protect write endpoints with a shared API key so the Pi deployment is
not open to anyone on the network.

**Deliverables:**
- Shared secret in `.planner-executor/config.yaml` or a local config file (never committed)
- `src/api.c` — check `Authorization: Bearer <key>` header on POST/PUT/DELETE
- `web/index.html` — store key in `localStorage`, send in request headers
- `scripts/install-service.sh` — pass key as environment variable to systemd unit

---

## Phase 6 — Pi-side backup and restore

**Goal:** Automated database backup on the Pi so bookings survive SD card corruption.

**Deliverables:**
- `scripts/backup-db.sh` already exists (keeps last 10 backups)
- Add systemd timer: `appbooking-backup.timer` runs daily
- `GET /api/admin/backup` endpoint triggers a backup remotely
- `scripts/restore-db.sh` — restores from a named backup file

---

## Backlog (unscheduled)

- **iCal export** — `GET /api/bookings.ics` for calendar app integration
- **Email notifications** — send confirmation on booking create/cancel (requires SMTP config)
- **Multi-user auth** — per-user tokens with booking ownership
- **Recurring bookings** — weekly/daily repeat pattern stored as a schedule
- **VS Code extension** — sidebar showing current bookings without opening terminal

---

## Upgrading the Planner-Executor workflow

To pull the latest scripts from the template without overwriting your plans or config:

```bash
./scripts/init.sh --upgrade
```

This overwrites only template-owned files (`scripts/*.sh`, `.claude/planner-instructions.md`)
and preserves user-owned files (`CLAUDE.md`, `.github/copilot-instructions.md`,
`.planner-executor/config.yaml`, all `.plans/**`).
