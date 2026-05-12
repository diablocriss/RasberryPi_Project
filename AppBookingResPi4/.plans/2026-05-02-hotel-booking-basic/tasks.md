# Tasks: Hotel Room Booking – MVP

All tasks are for the Executor (Copilot). Complete them in order; each task ends with
its own verification step before moving to the next.

---

> ## ✅ STATUS (2026-05-03): ALL TASKS COMPLETE — MVP SHIPPED
>
> **Build status:** `make clean && make` → zero warnings ✓  
> **Both pages verified:** `GET /` → "Hotel Booking" ✓  `GET /admin` → "Hotel Admin" ✓  
> **Deploy path:** `make pi64 && make deploy64` (Pi is aarch64) ✓  
> **Next action:** **Task 15** — full build + pi64 verify, then **Task 16** — deploy to Pi and run T1–T9.

---

---

## Phase 1 — Data layer

- [x] **Task 1: Rewrite `src/booking.h` — new `Room` and `Booking` structs**

  Replace the entire file with:
  - `Room` struct: `int room_id`, `char room_number[8]`, `char room_type[16]`, `char description[128]`
  - `Booking` struct: `int booking_id`, `char guest_name[64]`, `char email[64]`,
    `char check_in_date[12]`, `char check_out_date[12]`, `int number_of_guests`,
    `int room_id`, `char room_number[8]`, `char room_type[16]`, `int64_t created_at`,
    `char status[16]`
  - Function declarations (remove all old `resource`/`user`/`start_ts`/`end_ts` functions):
    ```c
    int  booking_create(const Booking *b);        // returns booking_id or -1
    int  booking_cancel(int booking_id);          // returns 0 or -1
    int  booking_list(Booking **out, int *count); // active only
    void booking_free_list(Booking *list);
    int  booking_check_conflict(int room_id, const char *check_in, const char *check_out);
    ```

  → verify: `grep -n "room_id\|check_in_date\|guest_name" src/booking.h` shows all new fields.

---

- [x] **Task 2: Rewrite `src/storage.h` — new storage interface**

  Replace the entire file with declarations matching the new schema:
  ```c
  int storage_init(const char *db_path);
  void storage_close(void);

  int storage_room_list(Room **out, int *count);
  int storage_room_free_list(Room *list);

  int storage_booking_insert(const Booking *b);            // returns booking_id or -1/-2
  int storage_booking_cancel(int booking_id);
  int storage_booking_list(Booking **out, int *count);     // active bookings with room_number
  int storage_availability(const char *check_in,
                           const char *check_out,
                           int **occupied_ids, int *count); // room_ids with conflicts
  int storage_conflict_check(int room_id,
                             const char *check_in,
                             const char *check_out);        // 1=conflict, 0=free, -1=error
  ```

  → verify: `grep -n "storage_room_list\|storage_availability\|storage_conflict_check" src/storage.h` shows all five groups.

---

- [x] **Task 3: Rewrite `src/storage.c` — new schema, seed data, mutex, queries**

  *(Done. `storage.c` implements the new hotel schema with `rooms` + `bookings` tables,
  seed data, `pthread_mutex_t db_lock`, `storage_conflict_check`, `storage_availability`,
  `storage_booking_insert`, `storage_booking_cancel`, `storage_booking_list`,
  `storage_room_list`.)*

  > **Do NOT run `make clean && make` yet.** `booking.c` still has the old implementation
  > and will not compile against the new `booking.h`. Complete Task 4 first, then verify
  > both tasks together.

---

- [x] **Task 4: Rewrite `src/booking.c` — thin domain layer over new storage**

  *(Done. `booking.c` and `api.c` skeleton are in place. Service is `active (running)`
  on the Pi via systemd. `make pi64 && make deploy64` is the live deploy path — the Pi
  runs aarch64 and SQLite is bundled from `src/sqlite3.c`. `web.c` `write()` warnings
  suppressed with `ssize_t r = write(...); (void)r;` pattern.)*

  > **Executor note (2026-05-03):** The old skeleton code below is superseded. The
  > actual files on disk are correct. The remaining issue was `User=pi` in
  > `install-service.sh` (fixed to `${SUDO_USER:-$USER}`) and `clean` target missing
  > `pi64` artifacts (both fixed by Planner). `make clean && make` now builds with zero
  > warnings on the native target.

  The old file references `storage_booking_select`,
  `storage_booking_update`, and `booking_free_list(list, count)` — none of which exist
  in the new `storage.h`. The new file is:

  ```c
  #include "booking.h"
  #include "storage.h"
  #include <stdlib.h>

  int booking_create(const Booking *b) {
      if (storage_conflict_check(b->room_id, b->check_in_date, b->check_out_date) == 1)
          return -2;
      return storage_booking_insert(b);
  }

  int booking_cancel(int booking_id) {
      return storage_booking_cancel(booking_id);
  }

  int booking_list(Booking **out, int *count) {
      return storage_booking_list(out, count);
  }

  void booking_free_list(Booking *list) {
      free(list);
  }

  int booking_check_conflict(int room_id, const char *check_in, const char *check_out) {
      return storage_conflict_check(room_id, check_in, check_out);
  }
  ```

  Also rewrite `src/api.c` to remove the old `booking_to_json` function and `handle_list`
  handler that reference the old struct fields (`b->resource`, `b->user`, `b->start_ts`,
  etc.). Replace `src/api.c` with a minimal compilable skeleton:

  ```c
  #include "api.h"
  #include "booking.h"
  #include "storage.h"
  #include "web.h"
  #include <stdio.h>
  #include <string.h>
  #include <unistd.h>

  #define RESP_OK  "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n"
  #define RESP_404 "HTTP/1.1 404 Not Found\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"not found\"}"
  #define RESP_400 "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"bad request\"}"

  static void send_str(int fd, const char *s) { write(fd, s, strlen(s)); }

  void api_handle(int fd, const char *req, size_t len) {
      (void)len;
      char method[8], path[256];
      sscanf(req, "%7s %255s", method, path);

      if (strcmp(path, "/") == 0 || strcmp(path, "/admin") == 0) {
          web_serve_index(fd);
          return;
      }
      send_str(fd, RESP_404);
  }
  ```

  → verify (after both Tasks 3 and 4 are done):
  ```bash
  make clean && make
  # expected: "[native] Build successful: ./appbooking" — zero warnings
  ./appbooking -p 8080 -d /tmp/hotel_test.db &
  sleep 0.3
  sqlite3 /tmp/hotel_test.db ".tables"
  # expected: bookings  rooms
  sqlite3 /tmp/hotel_test.db "SELECT COUNT(*) FROM rooms;"
  # expected: 6
  kill %1 ; rm -f /tmp/hotel_test.db
  ```

---

## Phase 2 — API endpoints

- [x] **Task 5: Add JSON helpers and response macros to `src/api.c`**

  At the top of `src/api.c` (after `#include`s), add:

  - `parse_json_string(json, key, out, sz)` — same pattern as the `api` skill.
  - `parse_json_int(json, key, out)` — variant returning `int` via `strtol`.
  - Updated response macros:
    ```c
    #define RESP_401 "HTTP/1.1 401 Unauthorized\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"unauthorized\"}"
    #define RESP_409 "HTTP/1.1 409 Conflict\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"conflict\"}"
    #define RESP_500 "HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"internal error\"}"
    #define ADMIN_PASSWORD "admin123"
    ```
  - Helper `check_admin_password(req)` — scans request headers for
    `X-Admin-Password: admin123`; returns 1 if present and matching, 0 otherwise.
    Use `strstr(req, "X-Admin-Password: " ADMIN_PASSWORD)`.

  → verify: `make clean && make` — zero warnings.

---

- [x] **Task 6: Implement `handle_list_rooms(fd)` in `src/api.c` — `GET /api/rooms`**

  1. Call `storage_room_list(&rooms, &count)`.
  2. Build JSON array: each room as `{"room_id":N,"room_number":"101","room_type":"standard","description":"..."}`.
  3. Send `RESP_OK` + JSON body; free room list.
  4. Wire into `api_handle()`: `strcmp(path, "/api/rooms") == 0 && strcmp(method,"GET") == 0`.

  → verify:
  ```bash
  curl -s http://localhost:8080/api/rooms | jq '.data | length'
  # expected: 6
  ```

---

- [x] **Task 7: Implement `handle_availability(fd, req)` in `src/api.c` — `GET /api/availability`**

  1. Extract query string from path using `strchr(path, '?')`.
  2. Parse `check_in` and `check_out` with `sscanf(qs, "check_in=%11[^&]&check_out=%11s", ci, co)`.
  3. Validate: both non-empty; `strcmp(ci, co) < 0` (check_in before check_out).
  4. Call `storage_availability(ci, co, &ids, &cnt)`.
  5. Build JSON: `{"ok":true,"data":{"occupied":[1,3,...]}}`.
  6. Free `ids`; send response.
  7. Wire into router: path starts with `/api/availability` + GET.

  → verify:
  ```bash
  # free dates (no bookings yet)
  curl -s "http://localhost:8080/api/availability?check_in=2026-06-10&check_out=2026-06-13" | jq .
  # expected: {"ok":true,"data":{"occupied":[]}}
  ```

---

- [x] **Task 8: Implement `handle_book(fd, body)` in `src/api.c` — `POST /api/book`**

  1. Parse fields from JSON body: `guest_name`, `email`, `check_in`, `check_out`, `guests` (int), `room_id` (int).
  2. Validate: all non-empty, `guests >= 1`, `strcmp(check_in, check_out) < 0`, `room_id > 0`.
  3. Populate a `Booking` struct; call `booking_create(&b)`.
  4. On return `-2`: send `RESP_409`.
  5. On return `< 0` (other error): send `RESP_500`.
  6. On success: send `RESP_OK` + `{"ok":true,"data":{"booking_id":N}}`.
  7. Wire into router: `strcmp(path, "/api/book") == 0 && strcmp(method,"POST") == 0`.

  → verify:
  ```bash
  curl -s -X POST http://localhost:8080/api/book \
    -H "Content-Type: application/json" \
    -d '{"guest_name":"Alice","email":"alice@x.com","check_in":"2026-06-10","check_out":"2026-06-13","guests":2,"room_id":1}' | jq .
  # expected: {"ok":true,"data":{"booking_id":1}}
  ```

---

- [x] **Task 9: Implement `handle_admin_list(fd, req)` in `src/api.c` — `GET /api/bookings`**

  1. Check `check_admin_password(req)` → send `RESP_401` if 0.
  2. Call `booking_list(&list, &count)`.
  3. Serialize each `Booking` to JSON: all fields including `room_number`, `room_type`, `created_at`, `status`.
  4. Free list; send response.
  5. Wire into router: `strcmp(path, "/api/bookings") == 0 && strcmp(method,"GET") == 0`.

  → verify:
  ```bash
  # Without password → 401
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/bookings
  # expected: 401

  # With password → list
  curl -s http://localhost:8080/api/bookings \
    -H "X-Admin-Password: admin123" | jq '.data | length'
  # expected: 1 (after Task 8 booking)
  ```

---

- [x] **Task 10: Implement `handle_admin_cancel(fd, req, booking_id)` in `src/api.c` — `DELETE /api/bookings/:id`**

  1. Check `check_admin_password(req)` → `RESP_401` if 0.
  2. Call `booking_cancel(booking_id)` → `RESP_404` if -1.
  3. Send `RESP_OK` + `{"ok":true}`.
  4. Wire into router:
     ```c
     int bid;
     if (sscanf(path, "/api/bookings/%d", &bid) == 1 && strcmp(method,"DELETE") == 0)
         handle_admin_cancel(fd, req, bid);
     ```

  → verify:
  ```bash
  curl -s -X DELETE http://localhost:8080/api/bookings/1 \
    -H "X-Admin-Password: admin123" | jq .
  # expected: {"ok":true}

  curl -s http://localhost:8080/api/bookings \
    -H "X-Admin-Password: admin123" | jq '.data | length'
  # expected: 0
  ```

---

## Phase 3 — Frontend

- [x] **Task 11: Create `web/index.html` — guest booking page (Sneat Bootstrap 5)**

  Create `web/index.html` from scratch. Requirements:
  - `<head>`: Bootstrap 5.3 CSS from jsDelivr; Sneat CSS from jsDelivr CDN:
    `https://cdn.jsdelivr.net/npm/@themeselection/sneat-bootstrap-html-admin-template-free@latest/...`
    If Sneat CDN is unreliable use Bootstrap 5 utility classes only (fallback).
    flatpickr 4.6 CSS and JS from CDN.
  - Sneat horizontal navbar with brand name "Hotel Booking".
  - **Section A** (`id="section-availability"`): two `<input type="text">` (`id="ci"`,
    `id="co"`) initialised with flatpickr; radio buttons for room type filter
    (All / Standard / Deluxe); "Check Availability" button (`id="btn-check"`).
    On click: fetch `/api/rooms` and `/api/availability?...`, render a Bootstrap card
    grid where each room shows room_number + type; available rooms get `bg-success text-white`,
    occupied rooms get `bg-secondary text-white`. Clicking an available card copies
    `room_id` into the booking form dropdown.
  - **Section B** (`id="section-form"`): booking form — room select dropdown (`id="room-sel"`
    populated from `/api/rooms`), name, email, guests number input (min=1), check-in /
    check-out flatpickr inputs, textarea for optional request, Submit button.
    On submit: `POST /api/book` → on 409 show inline alert "That room is already booked
    for those dates."; on other errors show generic alert; on success hide Section B and
    show Section C.
  - **Section C** (`id="section-thanks"`, hidden): thank-you message with booking_id.
  - `<script>` block: all JS inline; no external JS file; use `fetch` API with `async/await`.

  → verify:
  ```bash
  make clean && make
  ./appbooking -p 8080 -d /tmp/hotel_test.db &
  sleep 0.3
  curl -s http://localhost:8080/ | grep -c "Hotel Booking"
  # expected: ≥ 1
  kill %1 ; rm -f /tmp/hotel_test.db
  ```

---

- [x] **Task 12: Create `web/admin.html` — management page (Sneat Bootstrap 5)**

  > **Do NOT verify with curl yet.** `web.c` still calls `web_serve_index()` and has no
  > knowledge of `admin.html` until Tasks 13 and 14 are complete. Complete all three
  > tasks (12 → 13 → 14) before running any verification.

  Create `web/admin.html` from scratch. Requirements:
  - Same Bootstrap 5 + Sneat `<head>` links as `index.html`.
  - Sneat horizontal navbar with "Hotel Admin" brand and a link back to `/`.
  - On `DOMContentLoaded`: get `pwd = sessionStorage.getItem("adminPwd")`;
    if null call `pwd = window.prompt("Admin password:")` and
    `sessionStorage.setItem("adminPwd", pwd)`.
  - `loadBookings()` async function: fetch `/api/bookings` with
    `headers: {"X-Admin-Password": pwd}`; if HTTP 401 show alert "Wrong password",
    clear `sessionStorage`, and return; on success render Bootstrap table
    (`id="booking-table"`) with columns: ID, Guest, Email, Room, Type, Check-in,
    Check-out, Guests, Booked at, Action.
  - Each Action cell: `<button class="btn btn-sm btn-danger">Cancel</button>` that calls
    `DELETE /api/bookings/{id}` then `loadBookings()`.
  - "Refresh" button at page top triggers `loadBookings()`.
  - All JS inline in a `<script>` block.

  → no standalone verify — see batch verify at end of Task 14.

---

- [x] **Task 13: Update `web.c` and `web.h` — serve two HTML files**

  Replace `web.h`:
  ```c
  #pragma once
  void web_serve(int fd, const char *path);
  ```

  Replace `web.c`:
  1. Include both `index_html.h` and `admin_html.h`.
  2. `web_serve(fd, path)`: if `strcmp(path, "/admin") == 0` use `admin_html` /
     `admin_html_len`; else use `index_html` / `index_html_len`.
  3. Use `ssize_t r = write(...); (void)r;` pattern for all `write()` calls.
  4. Format the `Content-Length` header with `%u` (not `%zu`) — `xxd` generates
     `unsigned int` for the length symbol, not `size_t`.

  Update `src/api.c`:
  - In `api_handle()`, replace `web_serve_index(fd)` with `web_serve(fd, path)`.
  - Route: `if (strcmp(path,"/") == 0 || strcmp(path,"/admin") == 0)`.

  → no standalone verify — see batch verify at end of Task 14.

---

## Phase 4 — Build system

- [x] **Task 14: Update `Makefile` — add `admin_html.h` embedding rule, then verify Tasks 12–14**

  In `Makefile`:
  1. Add new xxd rule (place it right after the `src/index_html.h` rule):
     ```makefile
     src/admin_html.h: web/admin.html
     	xxd -i $< | sed 's/web_admin_html/admin_html/g' > $@
     ```
  2. Extend the `web.o` dependency lines to include `admin_html.h`:
     ```makefile
     build/obj/web.o:     src/index_html.h src/admin_html.h
     build/obj-pi/web.o:  src/index_html.h src/admin_html.h
     build/obj-pi64/web.o: src/index_html.h src/admin_html.h
     ```
  3. The `clean` target already includes `src/admin_html.h` — confirm it is present;
     add it if missing.

  → **Batch verify for Tasks 12 + 13 + 14** (run after all three are done):
  ```bash
  make clean && make
  # expected: zero warnings; "src/admin_html.h" generated; "[native] Build successful"

  ./appbooking -p 8080 -d /tmp/hotel_test.db &
  sleep 0.3

  curl -s http://localhost:8080/ | grep -c "Hotel Booking"
  # expected: ≥ 1

  curl -s http://localhost:8080/admin | grep -c "Hotel Admin"
  # expected: ≥ 1

  kill %1 ; rm -f /tmp/hotel_test.db
  ```

---

- [x] **Task 15: Full build verification — native and Pi64 cross-compile**

  ```bash
  make clean && make
  # expected: "[native] Build successful: ./appbooking" — zero warnings

  make pi64
  # expected: "[pi64] Cross-compile successful: ./appbooking-pi64"

  file appbooking-pi64
  # expected: ELF 64-bit LSB executable, ARM aarch64
  ```

  → verify: both targets succeed with zero warnings.

---

- [x] **Task 16: Deploy to Pi and run full test suite**

  1. On dev machine — deploy:
     ```bash
     make pi64 && make deploy64
     # then on Pi:
     sudo systemctl restart appbooking
     ```
  2. On Pi — run the full test sequence from `tests.md` (T1–T9) in order.
     Use `http://localhost:8080` on the Pi or `http://100.122.45.123:8080` from dev.
  3. If any test fails, fix the specific handler or SQL query on the dev machine,
     rebuild (`make pi64 && make deploy64`), restart the service, and re-run that test.
  4. Do not mark this task complete until all nine tests pass on the Pi.

  → verify: all `curl` commands return expected HTTP status codes and JSON on the Pi;
  browser loads `http://100.122.45.123:8080/` with Sneat layout and working date pickers.
