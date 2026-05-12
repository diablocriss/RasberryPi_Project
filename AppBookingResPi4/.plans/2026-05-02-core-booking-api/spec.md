# Spec: Core Booking REST API

## Objective
Implement the full CRUD REST API for bookings so the web dashboard and external clients can create, read, update, and cancel reservations.

## Scope
- **In scope:**
  - `POST /api/bookings` — create a new booking
  - `GET  /api/bookings/:id` — fetch a single booking by ID
  - `PUT  /api/bookings/:id` — update resource/user/note/times of an existing booking
  - `DELETE /api/bookings/:id` — cancel a booking (sets `cancelled=1`, does not delete the row)
  - `GET  /api/resources` — return a hardcoded list of bookable resources
  - Input validation: start_ts < end_ts, resource and user fields non-empty
  - Conflict detection: reject a new/updated booking if the same resource has an overlapping active booking

- **Out of scope:**
  - Authentication / authorization
  - Pagination of `/api/bookings`
  - Resource CRUD (resources are static for now)
  - Email / push notifications

## User Flow / Data Flow
1. Client sends `POST /api/bookings` with JSON body `{resource, user, note, start_ts, end_ts}`.
2. `api_handle()` in `src/api.c` parses the request line and body.
3. Calls `booking_create()` in `src/booking.c` which validates and calls `storage_booking_insert()`.
4. `storage_booking_insert()` checks for overlapping bookings before inserting.
5. Returns `{"ok":true,"data":{"id":…}}` on success or `{"ok":false,"error":"…"}` on failure.

## Technical Constraints
- JSON parsing must be done with simple `sscanf`/`strstr` — no external JSON library.
- Request body is at most 1 KB; no streaming needed.
- SQLite conflict check must use a single SELECT before INSERT (no triggers).
- All timestamps are Unix seconds (int64), no time zone handling in C.

## Design Decisions
- **Chosen approach:** parse JSON fields manually with `strstr` + `sscanf`; sufficient for the small fixed schema.
- **Alternatives considered:** embedding jsmn or cJSON — rejected to keep zero external dependencies beyond sqlite3.
- **Assumptions:** The HTTP request body fits within the existing `BUF_SIZE` (8192 bytes) buffer in `server.c`.

## Success Criteria
- [ ] `POST /api/bookings` with valid JSON returns `{"ok":true,"data":{"id":1}}` and row appears in `GET /api/bookings`.
- [ ] `POST /api/bookings` with `start_ts >= end_ts` returns `{"ok":false,"error":"invalid time range"}`.
- [ ] `POST /api/bookings` for an overlapping resource/time returns `{"ok":false,"error":"conflict"}`.
- [ ] `GET  /api/bookings/1` returns the booking JSON.
- [ ] `GET  /api/bookings/999` returns 404.
- [ ] `PUT  /api/bookings/1` updates the note field.
- [ ] `DELETE /api/bookings/1` sets `cancelled=1`; booking no longer appears in `GET /api/bookings`.
- [ ] `GET  /api/resources` returns a JSON array of resource names.
- [ ] `make clean && make` succeeds with no warnings.
