# Skill: booking

---

## Purpose

Domain logic for creating, reading, updating, and cancelling bookings in `src/booking.c` — including input validation and conflict detection.

---

## When to use

- Adding new booking validation rules (e.g., max duration, resource whitelist)
- Changing conflict detection logic
- Adding new fields to the `Booking` struct
- Debugging incorrect booking state or unexpected cancellations

---

## Files involved

| File | Role |
|---|---|
| `src/booking.h` | `Booking` struct definition; CRUD function declarations |
| `src/booking.c` | Thin domain layer — delegates to `storage.c` |
| `src/storage.c` | SQLite persistence; where conflict check SQL lives |
| `src/storage.h` | `storage_booking_*` function declarations |

---

## Constraints and gotchas

- `Booking.start_ts` and `end_ts` are Unix seconds (int64_t) — no TZ conversion in C.
- Cancelled bookings have `cancelled=1`; they are **never deleted** from the DB.
- Conflict check: two bookings conflict if they share the same `resource` AND their time ranges overlap AND neither is cancelled. Overlap condition: `A.start < B.end AND A.end > B.start`.
- `booking_free_list()` must be called after `booking_list()` to free the malloc'd array.
- `booking_create()` returns the new row ID on success, -1 on DB error, -2 on conflict.

---

## Patterns

### Booking struct (src/booking.h)
```c
typedef struct {
    int      id;
    char     resource[64];
    char     user[64];
    char     note[256];
    int64_t  start_ts;
    int64_t  end_ts;
    int      cancelled;
} Booking;
```

### Validation (add to booking_create before calling storage)
```c
if (b->start_ts >= b->end_ts) return -3;   // -3 = invalid time range
if (b->resource[0] == '\0') return -4;      // -4 = missing resource
if (b->user[0] == '\0') return -5;          // -4 = missing user
```

### Conflict detection SQL (in storage.c)
```sql
SELECT COUNT(*) FROM bookings
WHERE resource = ?
  AND cancelled = 0
  AND start_ts < ?      -- other booking starts before new one ends
  AND end_ts   > ?      -- other booking ends after new one starts
```
Bind: `(resource, new_end_ts, new_start_ts)`

---

## Step-by-step: adding a new validation rule

1. In `src/booking.c`, add the check in `booking_create()` before calling `storage_booking_insert()`.
2. Return a distinct negative error code (document it in `src/booking.h`).
3. In `src/api.c`, map the new error code to an appropriate JSON error string.
4. Add a curl test (see Tests section).

---

## Tests and verification

```bash
make clean && make
./appbooking -p 8080 -d /tmp/test.db &
sleep 0.3

# Valid booking
curl -s -X POST http://localhost:8080/api/bookings \
  -d '{"resource":"Room A","user":"alice","note":"","start_ts":1000,"end_ts":2000}' | jq .
# Expected: {"ok":true,"data":{"id":1}}

# Conflict
curl -s -X POST http://localhost:8080/api/bookings \
  -d '{"resource":"Room A","user":"bob","note":"","start_ts":1500,"end_ts":2500}' | jq .
# Expected: {"ok":false,"error":"conflict"}

# Invalid time range
curl -s -X POST http://localhost:8080/api/bookings \
  -d '{"resource":"Room B","user":"bob","note":"","start_ts":2000,"end_ts":1000}' | jq .
# Expected: {"ok":false,"error":"invalid time range"}

kill %1
rm -f /tmp/test.db
```
**Pass:** All three curl responses match expected.
**Fail:** Unexpected response body — check error code mapping in `src/api.c`.
