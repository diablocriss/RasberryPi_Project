# ⚠️ SUPERSEDED — DO NOT RUN THESE TESTS

The old schema (`resource`, `user`, `start_ts`, `end_ts`) no longer exists.
All curl commands below will return `{"ok":false,"error":"not found"}` — that is
correct behaviour for the new skeleton; it does NOT mean anything is broken.

**Run instead:** `.plans/2026-05-02-hotel-booking-basic/tests.md`

---

# Tests: Core Booking REST API (ARCHIVED)

## Build Verification
```bash
make clean && make
./appbooking -p 8080 -d /tmp/test_bookings.db &
sleep 0.3
```

## Manual curl Tests

### 1. List bookings (empty)
```bash
curl -s http://localhost:8080/api/bookings | jq .
# Expected: {"ok":true,"data":[]}
```

### 2. Create a booking
```bash
curl -s -X POST http://localhost:8080/api/bookings \
  -H "Content-Type: application/json" \
  -d '{"resource":"Room A","user":"alice","note":"standup","start_ts":1800000000,"end_ts":1800003600}' | jq .
# Expected: {"ok":true,"data":{"id":1}}
```

### 3. Create overlapping booking (same resource, overlapping time)
```bash
curl -s -X POST http://localhost:8080/api/bookings \
  -H "Content-Type: application/json" \
  -d '{"resource":"Room A","user":"bob","note":"clash","start_ts":1800001800,"end_ts":1800005400}' | jq .
# Expected: {"ok":false,"error":"conflict"}
```

### 4. Create booking with invalid time range
```bash
curl -s -X POST http://localhost:8080/api/bookings \
  -H "Content-Type: application/json" \
  -d '{"resource":"Room B","user":"bob","note":"","start_ts":1800003600,"end_ts":1800000000}' | jq .
# Expected: {"ok":false,"error":"invalid time range"}
```

### 5. Get booking by ID
```bash
curl -s http://localhost:8080/api/bookings/1 | jq .
# Expected: booking object with id=1
```

### 6. Get non-existent booking
```bash
curl -s http://localhost:8080/api/bookings/999 | jq .
# Expected: {"ok":false,"error":"not found"}
```

### 7. Update note
```bash
curl -s -X PUT http://localhost:8080/api/bookings/1 \
  -H "Content-Type: application/json" \
  -d '{"note":"updated standup"}' | jq .
# Expected: {"ok":true}
curl -s http://localhost:8080/api/bookings/1 | jq .note
# Expected: "updated standup"
```

### 8. Cancel booking
```bash
curl -s -X DELETE http://localhost:8080/api/bookings/1 | jq .
# Expected: {"ok":true}
curl -s http://localhost:8080/api/bookings | jq '.data | length'
# Expected: 0
```

### 9. List resources
```bash
curl -s http://localhost:8080/api/resources | jq .
# Expected: ["Room A","Room B","Lab 1","Lab 2","Desk 1"]
```

### 10. Dashboard loads
```bash
curl -s http://localhost:8080/ | grep -c "AppBookingRes"
# Expected: 1
```

## Teardown
```bash
kill %1
rm -f /tmp/test_bookings.db
```
