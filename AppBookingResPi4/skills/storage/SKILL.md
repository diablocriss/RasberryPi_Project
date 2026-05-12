# Skill: storage

---

## Purpose

SQLite3 persistence layer in `src/storage.c` — schema, prepared statements, and all booking CRUD operations against the database.

---

## When to use

- Adding new columns to the `bookings` table
- Writing new SQL queries (e.g., filter by resource, date range queries)
- Debugging SQLite errors or unexpected query results
- Adding a new table (e.g., `resources`)

---

## Files involved

| File | Role |
|---|---|
| `src/storage.c` | SQLite3 open/close, schema, all prepared-statement functions |
| `src/storage.h` | Public interface declarations |
| `src/booking.h` | `Booking` struct used as input/output |

---

## Constraints and gotchas

- Database path is runtime-configurable via `-d` flag (default: `bookings.db`).
- Schema is created with `CREATE TABLE IF NOT EXISTS` on every `storage_init()` call — safe to re-run.
- Always use prepared statements (`sqlite3_prepare_v2` + `sqlite3_bind_*`) — never `sprintf` into SQL.
- `storage_booking_cancel()` sets `cancelled=1`; it does NOT delete the row.
- `storage_booking_list()` returns only rows where `cancelled=0`.
- The `storage_booking_list()` caller must call `booking_free_list()` to free the returned array.
- `storage_booking_insert()` should return the new row ID (via `sqlite3_last_insert_rowid`), not just 0.
- Error returns: `-1` = SQLite error, `-2` = conflict (set by caller after `storage_booking_conflict_check()`).

---

## Patterns

### Schema
```sql
CREATE TABLE IF NOT EXISTS bookings (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  resource   TEXT    NOT NULL,
  user       TEXT    NOT NULL,
  note       TEXT    DEFAULT '',
  start_ts   INTEGER NOT NULL,
  end_ts     INTEGER NOT NULL,
  cancelled  INTEGER DEFAULT 0
);
```

### Prepared statement pattern
```c
sqlite3_stmt *s;
sqlite3_prepare_v2(db, "SELECT ... FROM bookings WHERE id=?", -1, &s, NULL);
sqlite3_bind_int(s, 1, id);
int rc = sqlite3_step(s);
if (rc == SQLITE_ROW) {
    // read columns
}
sqlite3_finalize(s);
```

### Conflict check
```c
int storage_booking_conflict_check(const char *resource, int64_t start_ts, int64_t end_ts) {
    sqlite3_stmt *s;
    sqlite3_prepare_v2(db,
        "SELECT COUNT(*) FROM bookings WHERE resource=? AND cancelled=0 "
        "AND start_ts < ? AND end_ts > ?",
        -1, &s, NULL);
    sqlite3_bind_text(s, 1, resource, -1, SQLITE_STATIC);
    sqlite3_bind_int64(s, 2, end_ts);
    sqlite3_bind_int64(s, 3, start_ts);
    sqlite3_step(s);
    int count = sqlite3_column_int(s, 0);
    sqlite3_finalize(s);
    return count > 0 ? 1 : 0;
}
```

### Adding a new column

1. Add the column to `SCHEMA` in `storage.c` (only for new DBs).
2. For existing DBs, add a migration: `ALTER TABLE bookings ADD COLUMN new_col TEXT DEFAULT ''`
3. Update `storage_booking_insert()`, `storage_booking_select()`, `storage_booking_list()`, and `storage_booking_update()`.
4. Update `Booking` struct in `src/booking.h`.

---

## Tests and verification

```bash
make clean && make
./appbooking -p 8080 -d /tmp/test.db &
sleep 0.3

curl -s -X POST http://localhost:8080/api/bookings \
  -d '{"resource":"Room A","user":"alice","note":"db test","start_ts":1000,"end_ts":2000}' | jq .

# Verify row in DB directly
sqlite3 /tmp/test.db "SELECT * FROM bookings;"

kill %1
rm -f /tmp/test.db
```
**Pass:** `sqlite3` shows the inserted row with correct values.
**Fail:** Empty result or error — check `storage_booking_insert()` return value and SQLite error logs.
