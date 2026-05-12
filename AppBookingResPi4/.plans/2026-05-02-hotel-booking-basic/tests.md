# Tests: Hotel Room Booking – MVP

Run the full setup block first, then each test in order. Tear down at the end.

---

## Setup

```bash
make clean && make
./appbooking -p 8080 -d /tmp/hotel_test.db &
sleep 0.3
```

---

## T1 — Build verification (native + Pi cross-compile)

```bash
make clean && make
```
**Pass:** output contains `[native] Build successful: ./appbooking`; exit code 0; zero
compiler warnings from `-Wall -Wextra`.

```bash
make pi
```
**Pass:** output contains `[pi] Cross-compile successful: ./appbooking-pi`; `file appbooking-pi`
shows `ELF 32-bit LSB executable, ARM`.

**Fail:** missing cross-compiler → `sudo apt install gcc-arm-linux-gnueabihf`;
missing sqlite headers → `sudo apt install libsqlite3-dev`.

---

## T2 — Database schema and seed data

```bash
sqlite3 /tmp/hotel_test.db ".tables"
```
**Pass:** output lists `bookings` and `rooms`.

```bash
sqlite3 /tmp/hotel_test.db "SELECT room_number, room_type FROM rooms ORDER BY room_id;"
```
**Pass:**
```
101|standard
102|standard
103|standard
104|standard
201|deluxe
202|deluxe
```

```bash
sqlite3 /tmp/hotel_test.db "SELECT COUNT(*) FROM bookings;"
```
**Pass:** `0` (empty at startup).

**Fail:** missing tables → check `SCHEMA` string in `storage.c`; missing seed rows →
check `storage_seed_rooms()` guard (`SELECT COUNT(*) FROM rooms`).

---

## T3 — `GET /api/rooms` returns all rooms

```bash
curl -s http://localhost:8080/api/rooms | jq '{ok: .ok, count: (.data | length)}'
```
**Pass:** `{"ok":true,"count":6}`.

```bash
curl -s http://localhost:8080/api/rooms | jq '.data[0]'
```
**Pass:** object with keys `room_id`, `room_number`, `room_type`, `description`.

**Fail:** `{"ok":false,...}` → check `storage_room_list()` and `handle_list_rooms()`;
`count: 0` → seed data not inserted, check `storage_seed_rooms()`.

---

## T4 — `GET /api/availability` with no bookings

```bash
curl -s "http://localhost:8080/api/availability?check_in=2026-06-10&check_out=2026-06-13" | jq .
```
**Pass:** `{"ok":true,"data":{"occupied":[]}}`.

```bash
# Missing parameter → 400
curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:8080/api/availability?check_in=2026-06-10"
```
**Pass:** `400`.

```bash
# Reversed dates → 400
curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:8080/api/availability?check_in=2026-06-13&check_out=2026-06-10"
```
**Pass:** `400`.

**Fail:** query string not parsed → check `strchr(path,'?')` logic in
`handle_availability()`; wrong SQL → check date comparison direction in
`storage_availability()`.

---

## T5 — `POST /api/book` creates a booking

```bash
curl -s -X POST http://localhost:8080/api/book \
  -H "Content-Type: application/json" \
  -d '{"guest_name":"Alice","email":"alice@example.com","check_in":"2026-06-10","check_out":"2026-06-13","guests":2,"room_id":1}' \
  | jq .
```
**Pass:** `{"ok":true,"data":{"booking_id":1}}`.

```bash
# Verify the booking is stored
sqlite3 /tmp/hotel_test.db \
  "SELECT guest_name, check_in_date, check_out_date, status FROM bookings WHERE booking_id=1;"
```
**Pass:** `Alice|2026-06-10|2026-06-13|active`.

```bash
# Invalid: check_out before check_in
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8080/api/book \
  -H "Content-Type: application/json" \
  -d '{"guest_name":"Bob","email":"bob@x.com","check_in":"2026-06-13","check_out":"2026-06-10","guests":1,"room_id":2}' 
```
**Pass:** `400`.

**Fail:** returns `-1` from insert → check `storage_booking_insert()` bind order;
JSON not parsed → check `parse_json_string` / `parse_json_int` for field names.

---

## T6 — Conflict detection returns HTTP 409

```bash
# Same room, overlapping window (2026-06-11 to 2026-06-14 overlaps the Alice booking 06-10 to 06-13)
curl -s -X POST http://localhost:8080/api/book \
  -H "Content-Type: application/json" \
  -d '{"guest_name":"Charlie","email":"c@x.com","check_in":"2026-06-11","check_out":"2026-06-14","guests":1,"room_id":1}' \
  | jq .
```
**Pass:** `{"ok":false,"error":"conflict"}` and HTTP status `409`.

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8080/api/book \
  -H "Content-Type: application/json" \
  -d '{"guest_name":"Charlie","email":"c@x.com","check_in":"2026-06-11","check_out":"2026-06-14","guests":1,"room_id":1}'
```
**Pass:** `409`.

```bash
# Adjacent booking (check_in == previous check_out) must NOT conflict
curl -s -X POST http://localhost:8080/api/book \
  -H "Content-Type: application/json" \
  -d '{"guest_name":"Dave","email":"d@x.com","check_in":"2026-06-13","check_out":"2026-06-15","guests":1,"room_id":1}' \
  | jq .ok
```
**Pass:** `true` — check-out day of one booking equals check-in day of another; the SQL
condition `check_in_date < ? AND check_out_date > ?` excludes this case.

**Fail:** conflict not detected → check SQL bind order in `storage_conflict_check()` —
`check_out` must bind to param 2 (`check_in_date < check_out`) and `check_in` to param 3
(`check_out_date > check_in`).

---

## T7 — Admin authentication

```bash
# Without header → 401
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/bookings
```
**Pass:** `401`.

```bash
# Wrong password → 401
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8080/api/bookings -H "X-Admin-Password: wrongpass"
```
**Pass:** `401`.

```bash
# Correct password → 200 with booking list
curl -s http://localhost:8080/api/bookings \
  -H "X-Admin-Password: admin123" | jq '{ok: .ok, count: (.data | length)}'
```
**Pass:** `{"ok":true,"count":2}` (Alice + Dave from T5/T6).

**Fail:** always 401 → check `strstr(req, "X-Admin-Password: admin123")` in
`check_admin_password()`; ensure the raw HTTP request string is passed, not just the body.

---

## T8 — Cancel booking (`DELETE /api/bookings/:id`)

```bash
# Cancel Alice's booking (booking_id=1)
curl -s -X DELETE http://localhost:8080/api/bookings/1 \
  -H "X-Admin-Password: admin123" | jq .
```
**Pass:** `{"ok":true}`.

```bash
# Booking no longer in active list
curl -s http://localhost:8080/api/bookings \
  -H "X-Admin-Password: admin123" | jq '.data | map(.booking_id)'
```
**Pass:** `[2]` — only Dave's booking remains (adjust IDs if seed order differs).

```bash
# Row still exists in DB with status=cancelled
sqlite3 /tmp/hotel_test.db \
  "SELECT status FROM bookings WHERE booking_id=1;"
```
**Pass:** `cancelled`.

```bash
# Cancel non-existent booking → 404
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE http://localhost:8080/api/bookings/999 \
  -H "X-Admin-Password: admin123"
```
**Pass:** `404`.

**Fail:** returns 200 but status unchanged → check `storage_booking_cancel()` UPDATE
statement; 404 for valid ID → check that `booking_cancel()` distinguishes
`sqlite3_changes(db) == 0` from SQL error.

---

## T9 — Availability reflects cancelled booking + browser smoke test

```bash
# After cancelling booking_id=1, room 1 should be free again for 2026-06-10 to 2026-06-13
curl -s "http://localhost:8080/api/availability?check_in=2026-06-10&check_out=2026-06-13" \
  | jq '.data.occupied'
```
**Pass:** `[]` — the cancelled booking no longer blocks availability (Dave's booking
is for 06-13 to 06-15 which does not overlap 06-10 to 06-13).

**Browser tests (manual):**

1. Open `http://localhost:8080/` in a browser.
   **Pass:** Sneat Bootstrap navbar appears; two date-picker inputs appear; "Check
   Availability" button is visible; booking form section is present.

2. Enter check-in `2026-07-01`, check-out `2026-07-05`; click "Check Availability".
   **Pass:** Six room cards render; all are green (available).

3. Click any green room card; it should pre-select the room in the booking form.
   Fill in name, email, guests=1, submit.
   **Pass:** Thank-you message (`#section-thanks`) appears; `#section-form` is hidden.

4. Open `http://localhost:8080/admin`.
   **Pass:** Password prompt appears; enter `admin123`; booking table loads.

5. Click "Cancel" on the booking just created.
   **Pass:** Row disappears from table; repeat availability check confirms room is free.

**Fail browser tests:** open DevTools console for JS errors; check `fetch` URLs are
relative (`/api/...`); check `Content-Type: text/html` header from `web_serve()`.

---

## Teardown

```bash
kill %1
rm -f /tmp/hotel_test.db
```
