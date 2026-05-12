# ⚠️ SUPERSEDED — DO NOT EXECUTE THIS PLAN

This plan used the old schema (`resource`, `user`, `start_ts`, `end_ts`).
The codebase has been replaced with the hotel booking schema (`rooms`, `bookings`,
`check_in_date`, `check_out_date`, `guest_name`).

**Active plan:** `.plans/2026-05-02-hotel-booking-basic/` — start at **Task 5**.

---

# Tasks: Core Booking REST API (ARCHIVED)

- [ ] Task 1: Add `booking_check_conflict()` to `src/storage.c` — SELECT COUNT(*) where resource matches, cancelled=0, and time ranges overlap; return 1 if conflict exists.
      → verify: manually call with known overlapping timestamps; confirm returns 1.

- [ ] Task 2: Wire conflict check into `storage_booking_insert()` — call `booking_check_conflict()` before INSERT; return -2 on conflict (distinct from -1 for DB error).
      → verify: `POST /api/bookings` twice with same resource/time; second returns `{"ok":false,"error":"conflict"}`.

- [ ] Task 3: Add `parse_json_string()` and `parse_json_int64()` helpers at top of `src/api.c` — extract a named field from a flat JSON object string using `strstr`+`sscanf`.
      → verify: unit-test inline with a known JSON string; confirm extracted values match.

- [ ] Task 4: Implement `handle_create(fd, body)` in `src/api.c` — parse `resource`, `user`, `note`, `start_ts`, `end_ts` from body; validate; call `booking_create()`; respond with id or error.
      → verify: `curl -X POST -d '{"resource":"Room A","user":"alice","note":"","start_ts":1000,"end_ts":2000}' http://localhost:8080/api/bookings` returns `{"ok":true,"data":{"id":1}}`.

- [ ] Task 5: Implement `handle_get(fd, id)` in `src/api.c` — call `booking_get()`; respond with booking JSON or 404.
      → verify: `curl http://localhost:8080/api/bookings/1` returns the booking; `/api/bookings/999` returns 404.

- [ ] Task 6: Implement `handle_update(fd, id, body)` in `src/api.c` — parse fields; call `booking_update()`; respond ok/error.
      → verify: `curl -X PUT -d '{"note":"updated"}' http://localhost:8080/api/bookings/1` and confirm via GET.

- [ ] Task 7: Implement `handle_cancel(fd, id)` in `src/api.c` — call `booking_cancel()`; respond ok/error.
      → verify: `curl -X DELETE http://localhost:8080/api/bookings/1`; confirm booking gone from list.

- [ ] Task 8: Implement `handle_resources(fd)` in `src/api.c` — return hardcoded JSON array `["Room A","Room B","Lab 1","Lab 2","Desk 1"]`.
      → verify: `curl http://localhost:8080/api/resources` returns the array.

- [ ] Task 9: Update the router in `api_handle()` to dispatch all new routes — extract `:id` from path with `sscanf`; route POST/GET/PUT/DELETE correctly.
      → verify: all curl tests from Tasks 4–8 pass in sequence.

- [ ] Task 10: `make clean && make` — confirm zero warnings with `-Wall -Wextra`.
      → verify: build output shows `[native] Build successful`.
