# Tests: Sneat UI Redesign

Each test maps to one task group and gives an exact command or browser action to verify.

---

## Test A — Vendor assets present on disk
**Verifies:** Group A (copy step)

```bash
ls -lh web/vendor/css/core.css \
        web/vendor/js/bootstrap.js \
        web/vendor/js/helpers.js \
        web/vendor/js/menu.js
```
Expected: four files, sizes ~585K, ~328K, ~32K, ~24K respectively (no zero-byte files).

---

## Test B — xxd headers generated correctly
**Verifies:** Group B (Makefile rules)

```bash
make src/vendor_core_css.h src/vendor_bootstrap_js.h \
     src/vendor_helpers_js.h src/vendor_menu_js.h
head -1 src/vendor_core_css.h
```
Expected: first line matches `unsigned char vendor_core_css[] = {` (symbol name must be
`vendor_core_css`, not `web_vendor_css_core_css`).

```bash
grep "vendor_bootstrap_js\b" src/vendor_bootstrap_js.h | head -1
grep "vendor_helpers_js\b"   src/vendor_helpers_js.h   | head -1
grep "vendor_menu_js\b"      src/vendor_menu_js.h       | head -1
```
Expected: one match each, with the clean symbol name (no path prefix).

---

## Test C — Clean build with zero warnings
**Verifies:** Groups B, C, D, E, F all compile together

```bash
make clean && make 2>&1 | tee /tmp/build.log
grep -E "warning:|error:" /tmp/build.log
```
Expected: `grep` returns nothing (no warnings, no errors). Binary `appbooking` exists:
```bash
ls -lh appbooking
```

---

## Test D — Vendor CSS route returns HTTP 200
**Verifies:** Group C and D (web.c + api.c routes)

Start server in background, then:
```bash
./appbooking -p 8080 -d /tmp/test.db &
sleep 1
curl -si http://localhost:8080/vendor/css/core.css | head -5
curl -si http://localhost:8080/vendor/js/bootstrap.js | head -5
curl -si http://localhost:8080/vendor/js/helpers.js | head -5
curl -si http://localhost:8080/vendor/js/menu.js | head -5
kill %1
```
Expected for each: first line `HTTP/1.1 200 OK`, second line contains the correct
`Content-Type` (`text/css` for the CSS file, `application/javascript` for the JS files).

---

## Test E — Guest page renders Sneat layout
**Verifies:** Group E

```bash
./appbooking -p 8080 -d /tmp/test.db &
sleep 1
curl -s http://localhost:8080/ | grep -c "layout-menu\|layout-wrapper\|layout-content-navbar"
kill %1
```
Expected: count ≥ 3 (all three landmark classes present in the page HTML).

Manual browser check: open `http://localhost:8080/` — sidebar visible, collapses on
mobile viewport (DevTools → toggle device toolbar, width < 768px), room availability
section shows date pickers, booking form shows guest-name / guest-email fields.

---

## Test F — Admin page renders Sneat layout with working table
**Verifies:** Group F

```bash
./appbooking -p 8080 -d /tmp/test.db &
sleep 1
curl -s http://localhost:8080/admin | grep -c "layout-menu\|booking-table\|refresh-btn"
kill %1
```
Expected: count ≥ 3.

Manual browser check: open `http://localhost:8080/admin` — sidebar visible with "Admin"
item active, table header shows ID / Guest / Email / Room / Check-in / Check-out / Action,
Refresh button triggers a `GET /api/bookings` fetch (visible in DevTools Network tab).

---

## Test G — End-to-end booking flow
**Verifies:** application logic still works after HTML rewrite

1. Open `http://localhost:8080/`
2. Enter check-in = tomorrow, check-out = day after tomorrow, click **Check Availability**
3. At least one room card appears
4. Click a room card → booking form scrolls into view with room / dates pre-filled
5. Enter name + email, click **Book** → success message appears
6. Navigate to `/admin` → new booking row visible in the table
7. Click **Cancel** on the row → row disappears after confirmation

All seven steps must pass without console errors.

---

## Test H — Cross-compile (Pi target)
**Verifies:** vendor headers work for ARM cross-compile

```bash
make pi 2>&1 | grep -E "warning:|error:"
ls -lh appbooking-pi
```
Expected: no warnings or errors, `appbooking-pi` binary produced (ARM ELF):
```bash
file appbooking-pi | grep -i arm
```
