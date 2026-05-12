# Spec: Hotel Room Booking – MVP

## Objective

Build a lightweight hotel room booking web application that runs on Raspberry Pi 4 as
a single self-contained binary. Guests view room availability on a calendar, submit
booking requests, and receive a confirmation message. Hotel staff access a
password-protected management page to view and cancel bookings.

---

## Scope

### In scope

- Two SQLite tables: `rooms` (static seed data) and `bookings`
- Five REST endpoints: `GET /api/rooms`, `GET /api/availability`,
  `POST /api/book`, `GET /api/bookings`, `DELETE /api/bookings/:id`
- Conflict detection: reject a booking when the requested room already has an active
  booking with overlapping dates
- Guest page (`web/index.html`): Sneat Bootstrap 5 layout, availability checker,
  booking form with flatpickr date picker, fetch-based submission, thank-you message
- Management page (`web/admin.html`): same Sneat layout, JS password prompt,
  booking table with cancel buttons
- Both HTML files embedded into the binary via `xxd`
- Native (x86_64) and Raspberry Pi 4 cross-compile targets in the Makefile

### Out of scope

- **libmicrohttpd** – the project uses a hand-rolled TCP/pthread server (`server.c`);
  migrating to libmicrohttpd would require rewriting `server.c`, all API handlers, and
  the test harness with zero user-visible benefit for an MVP.
- **jansson** – all JSON parsing uses `strstr`/`sscanf` per the established project
  convention; the fixed hotel schema is small enough that a library adds no value.
- Guest authentication / session tokens
- Email or SMS notifications
- Room CRUD (rooms are seeded once at DB initialisation)
- Pagination of the booking list
- Multi-room bookings per request
- Payment integration
- Editing an existing booking (cancel + rebook instead)

---

## Architecture

```
Client HTTP request
  └─ server.c  accept() → pthread → recv() → api_handle()
       ├─ GET /                    → web.c: serve index_html (guest page)
       ├─ GET /admin               → web.c: serve admin_html (management page)
       ├─ GET /api/rooms           → api.c: handle_list_rooms()
       ├─ GET /api/availability    → api.c: handle_availability()
       ├─ POST /api/book           → api.c: handle_book()
       │                                   ↳ booking.c → storage.c → SQLite
       ├─ GET /api/bookings        → api.c: handle_admin_list()   [password]
       └─ DELETE /api/bookings/:id → api.c: handle_admin_cancel() [password]
```

**Thread model:** one pthread per TCP connection; `storage.c` functions are NOT
thread-safe – protect with a `pthread_mutex_t db_lock` in `storage.c`.

---

## Database schema

```sql
CREATE TABLE IF NOT EXISTS rooms (
  room_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  room_number  TEXT    NOT NULL UNIQUE,
  room_type    TEXT    NOT NULL,   -- 'standard' or 'deluxe'
  description  TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS bookings (
  booking_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  guest_name        TEXT    NOT NULL,
  email             TEXT    NOT NULL,
  check_in_date     TEXT    NOT NULL,   -- 'YYYY-MM-DD'
  check_out_date    TEXT    NOT NULL,   -- 'YYYY-MM-DD'
  number_of_guests  INTEGER NOT NULL DEFAULT 1,
  room_id           INTEGER NOT NULL REFERENCES rooms(room_id),
  created_at        INTEGER NOT NULL,   -- Unix timestamp UTC (time(NULL))
  status            TEXT    NOT NULL DEFAULT 'active'  -- 'active' or 'cancelled'
);
```

Seed data — inserted once if `rooms` table is empty at `storage_init()`:

| room_number | room_type | description          |
|-------------|-----------|----------------------|
| 101         | standard  | Standard room, 1 bed |
| 102         | standard  | Standard room, 2 beds |
| 103         | standard  | Standard room, 1 bed, garden view |
| 104         | standard  | Standard room, 2 beds, garden view |
| 201         | deluxe    | Deluxe room, king bed, sea view |
| 202         | deluxe    | Deluxe suite, 2 rooms, sea view |

---

## API endpoints

### `GET /api/rooms`

Returns the full room list.

```json
{"ok":true,"data":[
  {"room_id":1,"room_number":"101","room_type":"standard","description":"..."},
  ...
]}
```

### `GET /api/availability?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD`

Returns the IDs of rooms that are **occupied** during the requested window.
A room is occupied if it has an `active` booking where:
`check_in_date < req.check_out AND check_out_date > req.check_in`

```json
{"ok":true,"data":{"occupied":[1,3]}}
```

Returns `400` if either date is missing or check_in >= check_out.

### `POST /api/book`

Request body:
```json
{"guest_name":"Alice","email":"alice@example.com",
 "check_in":"2026-06-10","check_out":"2026-06-13",
 "guests":2,"room_id":1}
```

- Validates all fields non-empty, `guests >= 1`, `check_in < check_out`, `room_id` exists.
- Runs conflict check; returns `409` with `{"ok":false,"error":"conflict"}` if occupied.
- On success returns `{"ok":true,"data":{"booking_id":7}}`.

### `GET /api/bookings`

Requires header `X-Admin-Password: admin123`.
Returns `401` if header absent or wrong.
Returns all active bookings joined with `rooms` for room_number:

```json
{"ok":true,"data":[
  {"booking_id":1,"guest_name":"Alice","email":"...","room_number":"101",
   "room_type":"standard","check_in_date":"2026-06-10","check_out_date":"2026-06-13",
   "number_of_guests":2,"created_at":1748000000,"status":"active"},
  ...
]}
```

### `DELETE /api/bookings/:id`

Requires `X-Admin-Password: admin123`. Sets `status='cancelled'`. Returns `{"ok":true}`.
Returns `404` if booking not found. Returns `401` if password wrong.

---

## Frontend structure

### Guest page — `web/index.html`

- Sneat Bootstrap 5 horizontal navbar + single content area (no sidebar).
- Bootstrap 5.3 loaded from CDN (jsDelivr); flatpickr 4.6 loaded from CDN.
- Sneat core CSS loaded from jsDelivr (`@themeselection/sneat-bootstrap-html-admin-template`
  free CDN build).
- **Section A – Availability checker:**
  Two flatpickr inputs (`check-in`, `check-out`), a room-type filter (`all / standard /
  deluxe`), and a "Check availability" button.
  On click: calls `GET /api/rooms` + `GET /api/availability?...` in parallel, then renders
  a Bootstrap card grid where available rooms are highlighted green and occupied rooms grey.
- **Section B – Booking form:**
  Dropdown populated from `GET /api/rooms`, name, email, guests (number, min 1), check-in /
  check-out (flatpickr), optional request textarea, Submit button.
  On submit: calls `POST /api/book`; shows inline error (conflict, validation) or hides form
  and shows Section C.
- **Section C – Thank-you message:** hidden div, shown on successful booking.

### Management page — `web/admin.html`

- Same Sneat Bootstrap 5 layout.
- On `DOMContentLoaded`: reads password from `sessionStorage` key `adminPwd`; if absent,
  calls `window.prompt("Enter admin password:")` and stores result.
- Calls `GET /api/bookings` with `X-Admin-Password` header; renders a table.
- Each row has a "Cancel" button that calls `DELETE /api/bookings/{id}` and refreshes.
- If password is wrong, shows an alert and clears `sessionStorage`.

---

## Build system changes

Two files are replacing the single-file embedding:

```makefile
src/index_html.h: web/index.html
    xxd -i $< | sed 's/web_index_html/index_html/g' > $@

src/admin_html.h: web/admin.html
    xxd -i $< | sed 's/web_admin_html/admin_html/g' > $@
```

Both headers become prerequisites for `build/obj/web.o` and `build/obj-pi/web.o`.

`web.c` includes both headers and selects based on path:
```c
#include "index_html.h"
#include "admin_html.h"

void web_serve(int fd, const char *path) {
    const unsigned char *html = index_html;
    unsigned int html_len     = index_html_len;
    if (strcmp(path, "/admin") == 0) {
        html     = admin_html;
        html_len = admin_html_len;
    }
    // write HTTP header + body
}
```

`web.h` exposes `void web_serve(int fd, const char *path)`.
`api.c` calls `web_serve(fd, path)` in place of the old `web_serve_index(fd)`.

No change to `LDFLAGS` (still `-lpthread -lsqlite3`).

---

## Technical constraints

- C11, `-Wall -Wextra -O2 -D_GNU_SOURCE`
- No external JSON library — `strstr` / `sscanf` only
- No libmicrohttpd — `server.c` (raw TCP/pthread) unchanged
- Dates stored as `TEXT 'YYYY-MM-DD'`; ISO string comparison equals chronological order in SQLite
- Admin password hard-coded as `#define ADMIN_PASSWORD "admin123"` in `src/api.c`
- `xxd` must be installed: `sudo apt install xxd`
- Cross-compiler for live Pi (aarch64): `sudo apt install gcc-aarch64-linux-gnu`; use `make pi64 && make deploy64`
- SQLite is bundled as `src/sqlite3.c` (amalgamation) — no `-lsqlite3` runtime dep; `LDFLAGS = -lpthread` only
- Pi needs internet access for CDN assets (Bootstrap, flatpickr) at runtime

---

## Design decisions

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| Server library | Keep `server.c` raw TCP | Zero refactor; all existing skills and Makefile cover this |
| JSON library | `strstr`/`sscanf` | Project convention; fixed schema needs no library |
| Date storage | `TEXT 'YYYY-MM-DD'` | Lexicographic = chronological for ISO dates; no C timestamp math |
| Multi-page | Two HTML files via `xxd` | Clean separation; same embedding approach, just two rules |
| Admin auth | `X-Admin-Password` request header | Stateless, no sessions, no cookies, trivially testable with `curl -H` |
| Frontend assets | CDN (jsDelivr) | Avoids bundling ~500 KB of vendor assets into the binary; Pi internet is assumed |
| Thread safety | `pthread_mutex_t db_lock` in `storage.c` | Each connection runs in its own thread; SQLite is not thread-safe without a lock |

---

## Success criteria

- [ ] `make clean && make` produces `./appbooking` with zero warnings (`-Wall -Wextra`)
- [ ] `make pi` produces `./appbooking-pi` (ARM ELF)
- [ ] `GET /api/rooms` returns JSON array with 6 rooms
- [ ] `GET /api/availability` for a free date range returns `{"occupied":[]}`
- [ ] `POST /api/book` with valid data returns `{"ok":true,"data":{"booking_id":N}}`
- [ ] `POST /api/book` for same room + overlapping dates returns HTTP 409 `{"ok":false,"error":"conflict"}`
- [ ] `GET /api/bookings` without password header returns HTTP 401
- [ ] `GET /api/bookings` with correct `X-Admin-Password` header returns booking list
- [ ] `DELETE /api/bookings/1` with correct password sets status=cancelled; booking absent from subsequent list
- [ ] Browser: guest page loads Sneat layout, flatpickr opens, form submits successfully
- [ ] Browser: admin page prompts for password, table renders, cancel button removes row
