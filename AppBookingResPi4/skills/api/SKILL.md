# Skill: api

---

## Purpose

Implement and extend REST API handlers in `src/api.c` — routing, JSON parsing, response formatting, and wiring new endpoints into `api_handle()`.

---

## When to use

- Adding a new REST endpoint (`POST /api/...`, `GET /api/.../:id`, etc.)
- Modifying request parsing or response format in an existing handler
- Fixing routing bugs in `api_handle()`
- Adding input validation to a handler

---

## Files involved

| File | Role |
|---|---|
| `src/api.c` | Route dispatcher (`api_handle`) and all HTTP handler functions |
| `src/api.h` | Public interface: `void api_handle(int fd, const char *req, size_t len)` |
| `src/booking.c` | Domain logic called by handlers |
| `src/web.c` | Static asset handler for `GET /` |

---

## Constraints and gotchas

- **No external JSON library.** Parse with `strstr` + `sscanf` only.
- Request body fits within `BUF_SIZE` (8192 bytes) in `server.c` — no streaming.
- Always respond with `{"ok":true,"data":{...}}` on success, `{"ok":false,"error":"..."}` on failure.
- HTTP status line must match: `200 OK`, `400 Bad Request`, `404 Not Found`.
- Route matching in `api_handle()` uses plain `strcmp` / `sscanf` on `path`.
- Extract `:id` from path with: `sscanf(path, "/api/bookings/%d", &id)`
- Method is extracted with: `sscanf(req, "%7s %255s", method, path)`

---

## Patterns

### Handler signature
```c
static void handle_create(int fd, const char *body) { ... }
static void handle_get(int fd, int id) { ... }
static void handle_update(int fd, int id, const char *body) { ... }
static void handle_cancel(int fd, int id) { ... }
static void handle_resources(int fd) { ... }
```

### JSON field extraction (no library)
```c
static int parse_json_string(const char *json, const char *key, char *out, size_t sz) {
    char search[64];
    snprintf(search, sizeof(search), "\"%s\"", key);
    const char *p = strstr(json, search);
    if (!p) return -1;
    p = strchr(p + strlen(search), '"');
    if (!p) return -1;
    p++;
    const char *end = strchr(p, '"');
    if (!end) return -1;
    size_t len = (size_t)(end - p);
    if (len >= sz) len = sz - 1;
    memcpy(out, p, len);
    out[len] = '\0';
    return 0;
}

static int parse_json_int64(const char *json, const char *key, int64_t *out) {
    char search[64];
    snprintf(search, sizeof(search), "\"%s\"", key);
    const char *p = strstr(json, search);
    if (!p) return -1;
    p = strchr(p + strlen(search), ':');
    if (!p) return -1;
    while (*p == ':' || *p == ' ') p++;
    *out = (int64_t)strtoll(p, NULL, 10);
    return 0;
}
```

### Response helpers
```c
static void send_str(int fd, const char *s) { write(fd, s, strlen(s)); }

#define RESP_OK  "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n"
#define RESP_404 "HTTP/1.1 404 Not Found\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"not found\"}"
#define RESP_400 "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"bad request\"}"
```

### Routing in api_handle()
```c
char method[8], path[256];
sscanf(req, "%7s %255s", method, path);

int id;
if (strcmp(path, "/api/bookings") == 0) {
    if (strcmp(method, "GET") == 0)  handle_list(fd);
    else if (strcmp(method, "POST") == 0) handle_create(fd, body_start(req));
    else send_str(fd, RESP_404);
} else if (sscanf(path, "/api/bookings/%d", &id) == 1) {
    if (strcmp(method, "GET") == 0)    handle_get(fd, id);
    else if (strcmp(method, "PUT") == 0)    handle_update(fd, id, body_start(req));
    else if (strcmp(method, "DELETE") == 0) handle_cancel(fd, id);
    else send_str(fd, RESP_404);
} else if (strcmp(path, "/api/resources") == 0 && strcmp(method, "GET") == 0) {
    handle_resources(fd);
}
```

---

## Step-by-step: adding a new endpoint

1. Add the handler function in `src/api.c` (static, above `api_handle`)
2. Add the route match in `api_handle()` in `src/api.c`
3. `make clean && make` — verify zero warnings
4. Test with curl (see Tests section)

---

## Tests and verification

```bash
make clean && make
./appbooking -p 8080 -d /tmp/test.db &
sleep 0.3

# List (GET)
curl -s http://localhost:8080/api/bookings | jq .

# Create (POST)
curl -s -X POST http://localhost:8080/api/bookings \
  -H "Content-Type: application/json" \
  -d '{"resource":"Room A","user":"alice","note":"test","start_ts":1000000,"end_ts":1003600}' | jq .

# Get by ID
curl -s http://localhost:8080/api/bookings/1 | jq .

# Resources
curl -s http://localhost:8080/api/resources | jq .

kill %1
rm -f /tmp/test.db
```
**Pass:** Each curl returns `{"ok":true,...}`.
**Fail:** `{"ok":false,...}` or connection refused — check server started, check routing logic.
