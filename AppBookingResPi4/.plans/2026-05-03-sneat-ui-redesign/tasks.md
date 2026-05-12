# Tasks: Sneat UI Redesign

## Group A — Copy vendor assets

- [x] **A1** Create directory `web/vendor/` and copy the four Sneat dist files into it:
  ```bash
  SNEAT=sneat-bootstrap-html-admin-template-free-v3.0.0/sneat-bootstrap-html-admin-template-free
  mkdir -p web/vendor/css web/vendor/js
  cp $SNEAT/dist/css/core.css        web/vendor/css/core.css
  cp $SNEAT/dist/js/bootstrap.js     web/vendor/js/bootstrap.js
  cp $SNEAT/dist/js/helpers.js       web/vendor/js/helpers.js
  cp $SNEAT/dist/js/menu.js          web/vendor/js/menu.js
  ```
  Verify: `ls -lh web/vendor/css/ web/vendor/js/` — four files, sizes match originals.

---

## Group B — Makefile: xxd rules for vendor files

- [x] **B1** In `Makefile` after line 45 (the `src/admin_html.h` rule), add four new xxd rules:
  ```makefile
  src/vendor_core_css.h: web/vendor/css/core.css
  	xxd -i $< | sed 's/web_vendor_css_core_css/vendor_core_css/g' > $@

  src/vendor_bootstrap_js.h: web/vendor/js/bootstrap.js
  	xxd -i $< | sed 's/web_vendor_js_bootstrap_js/vendor_bootstrap_js/g' > $@

  src/vendor_helpers_js.h: web/vendor/js/helpers.js
  	xxd -i $< | sed 's/web_vendor_js_helpers_js/vendor_helpers_js/g' > $@

  src/vendor_menu_js.h: web/vendor/js/menu.js
  	xxd -i $< | sed 's/web_vendor_js_menu_js/vendor_menu_js/g' > $@
  ```

- [x] **B2** In `Makefile` line 47, extend the `$(TARGET)` prerequisite to include the four new headers:
  ```makefile
  $(TARGET): src/index_html.h src/admin_html.h \
             src/vendor_core_css.h src/vendor_bootstrap_js.h \
             src/vendor_helpers_js.h src/vendor_menu_js.h \
             $(OBJS)
  ```

- [x] **B3** In `Makefile` update the `build/obj/web.o` and `build/obj-pi/web.o` order-only
  deps (lines 54–55) to also depend on the four vendor headers:
  ```makefile
  build/obj/web.o: src/index_html.h src/admin_html.h \
                   src/vendor_core_css.h src/vendor_bootstrap_js.h \
                   src/vendor_helpers_js.h src/vendor_menu_js.h
  build/obj-pi/web.o: src/index_html.h src/admin_html.h \
                      src/vendor_core_css.h src/vendor_bootstrap_js.h \
                      src/vendor_helpers_js.h src/vendor_menu_js.h
  ```
  Also update `build/obj-pi64/web.o` (line 108) the same way.

- [x] **B4** In `Makefile` line 69, extend `pi:` prerequisites:
  ```makefile
  pi: src/index_html.h src/admin_html.h \
      src/vendor_core_css.h src/vendor_bootstrap_js.h \
      src/vendor_helpers_js.h src/vendor_menu_js.h \
      $(PI_TARGET)
  ```
  Do the same for `pi64:` (line 91).

- [x] **B5** In `Makefile` `clean:` target (line 155), extend the `rm -f` list:
  ```makefile
  rm -f $(OBJS) $(PI_OBJS) $(PI64_OBJS) \
        $(TARGET) $(PI_TARGET) $(PI64_TARGET) \
        src/index_html.h src/admin_html.h \
        src/vendor_core_css.h src/vendor_bootstrap_js.h \
        src/vendor_helpers_js.h src/vendor_menu_js.h
  ```

---

## Group C — web.c: add four static asset routes

- [x] **C1** In `src/web.c`, add `#include` lines for the four new vendor headers after
  line 3 (`#include "admin_html.h"`):
  ```c
  #include "vendor_core_css.h"
  #include "vendor_bootstrap_js.h"
  #include "vendor_helpers_js.h"
  #include "vendor_menu_js.h"
  ```

- [x] **C2** In `src/web.c`, replace the current `web_serve` function (lines 8–29) with
  the extended version below. The key changes are:
  - Add a `content_type` variable alongside `html` / `html_len`
  - Add four `else if` branches for the vendor routes before the final `write` calls
  - Keep the existing `/admin` branch unchanged

  ```c
  void web_serve(int fd, const char *path) {
      const unsigned char *html = index_html;
      unsigned int         html_len = index_html_len;
      const char          *content_type = "text/html; charset=utf-8";
      char header[256];

      if (strcmp(path, "/admin") == 0) {
          html         = admin_html;
          html_len     = admin_html_len;
      } else if (strcmp(path, "/vendor/css/core.css") == 0) {
          html         = vendor_core_css;
          html_len     = vendor_core_css_len;
          content_type = "text/css";
      } else if (strcmp(path, "/vendor/js/bootstrap.js") == 0) {
          html         = vendor_bootstrap_js;
          html_len     = vendor_bootstrap_js_len;
          content_type = "application/javascript";
      } else if (strcmp(path, "/vendor/js/helpers.js") == 0) {
          html         = vendor_helpers_js;
          html_len     = vendor_helpers_js_len;
          content_type = "application/javascript";
      } else if (strcmp(path, "/vendor/js/menu.js") == 0) {
          html         = vendor_menu_js;
          html_len     = vendor_menu_js_len;
          content_type = "application/javascript";
      }

      int hlen = snprintf(header, sizeof(header),
          "HTTP/1.1 200 OK\r\n"
          "Content-Type: %s\r\n"
          "Content-Length: %u\r\n"
          "Connection: close\r\n\r\n",
          content_type, html_len);
      ssize_t r;
      r = write(fd, header, hlen);
      (void)r;
      r = write(fd, html, html_len);
      (void)r;
  }
  ```

---

## Group D — api.c: register vendor routes

- [x] **D1** Open `src/api.c` and find the route dispatcher (the block that calls
  `web_serve` for `/` and `/admin`). Add the four vendor paths to the same `if/else if`
  chain so they are forwarded to `web_serve` instead of returning a 404:
  ```c
  if (strcmp(path, "/") == 0 ||
      strcmp(path, "/admin") == 0 ||
      strcmp(path, "/vendor/css/core.css") == 0 ||
      strcmp(path, "/vendor/js/bootstrap.js") == 0 ||
      strcmp(path, "/vendor/js/helpers.js") == 0 ||
      strcmp(path, "/vendor/js/menu.js") == 0) {
      web_serve(fd, path);
      return;
  }
  ```
  (Exact line numbers depend on the current state of `api.c` — locate the existing
  `web_serve` call and extend the condition guarding it.)

---

## Group E — Rewrite web/index.html (guest page)

Read these reference files before writing:
- `sneat-.../html/index.html` — layout shell (copy the entire
  `div.layout-wrapper.layout-content-navbar` skeleton, sidebar `<aside>`, topbar `<nav>`,
  and `div.content-wrapper > div.container-xxl` wrapper)
- `sneat-.../html/cards-basic.html` — card structure for room availability results
- `sneat-.../html/form-layouts-vertical.html` — form field layout for booking form

- [x] **E1** Rewrite `web/index.html` keeping **all existing JavaScript verbatim**
  (every `fetch`, DOM ID, event listener, and flatpickr call). Only the HTML structure
  and CSS classes change. Required structure:

  ```html
  <!doctype html>
  <html lang="en" class="layout-menu-fixed layout-compact">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no, minimum-scale=1.0, maximum-scale=1.0">
    <title>Hotel Booking</title>
    <!-- Fonts (CDN — graceful fallback to system fonts offline) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400;1,500;1,600;1,700&display=swap" rel="stylesheet">
    <!-- Sneat vendor CSS (locally embedded) -->
    <link rel="stylesheet" href="/vendor/css/core.css">
    <!-- flatpickr (CDN) -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <!-- Sneat helpers must be in <head> -->
    <script src="/vendor/js/helpers.js"></script>
  </head>
  <body>
    <div class="layout-wrapper layout-content-navbar">
      <div class="layout-container">

        <!-- Sidebar -->
        <aside id="layout-menu" class="layout-menu menu-vertical menu bg-menu-theme">
          <div class="app-brand demo">
            <a href="/" class="app-brand-link">
              <span class="app-brand-text demo menu-text fw-bold">Hotel</span>
            </a>
            <a href="javascript:void(0);" class="layout-menu-toggle menu-link text-large ms-auto">
              <i class="bx bx-chevron-left bx-sm d-flex align-items-center justify-content-center"></i>
            </a>
          </div>
          <div class="menu-inner-shadow"></div>
          <ul class="menu-inner py-1">
            <li class="menu-item active">
              <a href="/" class="menu-link">
                <i class="menu-icon tf-icons bx bx-home-circle"></i>
                <div>Book a Room</div>
              </a>
            </li>
            <li class="menu-item">
              <a href="/admin" class="menu-link">
                <i class="menu-icon tf-icons bx bx-table"></i>
                <div>Admin</div>
              </a>
            </li>
          </ul>
        </aside>
        <!-- / Sidebar -->

        <div class="layout-page">
          <!-- Topbar -->
          <nav class="layout-navbar container-xxl navbar navbar-expand-xl navbar-detached align-items-center bg-navbar-theme" id="layout-navbar">
            <div class="layout-menu-toggle navbar-nav align-items-xl-center me-3 me-xl-0 d-xl-none">
              <a class="nav-item nav-link px-0 me-xl-4" href="javascript:void(0)">
                <i class="bx bx-menu bx-sm"></i>
              </a>
            </div>
            <div class="navbar-nav-right d-flex align-items-center" id="navbar-collapse">
              <div class="navbar-nav align-items-center">
                <span class="nav-item nav-link fw-semibold px-0">Hotel Booking System</span>
              </div>
            </div>
          </nav>
          <!-- / Topbar -->

          <!-- Content wrapper -->
          <div class="content-wrapper">
            <div class="container-xxl flex-grow-1 container-p-y">

              <!-- Section 1: Availability check -->
              <div class="card mb-4" id="section-availability">
                <div class="card-header">
                  <h5 class="mb-0">Check Room Availability</h5>
                </div>
                <div class="card-body">
                  <!-- date pickers + room-type radios + Check button — keep existing IDs:
                       #ci, #co, radio[name=room-type], #btn-check, #availability-error, #availability-results -->
                </div>
              </div>

              <!-- Section 2: Booking form -->
              <div class="card" id="section-book">
                <div class="card-header">
                  <h5 class="mb-0">Make a Reservation</h5>
                </div>
                <div class="card-body">
                  <!-- Vertical form — keep existing IDs:
                       #room-id-display, #checkin-display, #checkout-display,
                       #guest-name, #guest-email, #btn-book, #book-error, #book-success -->
                </div>
              </div>

            </div>
            <div class="content-backdrop fade"></div>
          </div>
          <!-- / Content wrapper -->
        </div>
      </div>

      <!-- Overlay -->
      <div class="layout-overlay layout-menu-toggle"></div>
    </div>

    <!-- Sneat vendor JS (locally embedded) -->
    <script src="/vendor/js/bootstrap.js"></script>
    <script src="/vendor/js/menu.js"></script>
    <!-- flatpickr (CDN) -->
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <!-- Application logic (keep verbatim from current web/index.html) -->
    <script>
      /* === paste all existing JS here, unchanged === */
    </script>
  </body>
  </html>
  ```

---

## Group F — Rewrite web/admin.html (admin page)

Read these reference files before writing:
- `sneat-.../html/index.html` — same layout shell as Group E
- `sneat-.../html/tables-basic.html` — table-responsive, thead/tbody classes

- [x] **F1** Rewrite `web/admin.html` keeping **all existing JavaScript verbatim**.
  Required structure mirrors Group E's shell. Sidebar links are identical.
  Content area:

  ```html
  <!-- Content area -->
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <div>
        <h5 class="mb-0">Manage Bookings</h5>
        <small class="text-muted">Review and cancel active reservations</small>
      </div>
      <button class="btn btn-primary btn-sm" id="refresh-btn" type="button">Refresh</button>
    </div>
    <div class="card-body px-0">
      <div class="alert alert-danger mx-4 d-none" id="admin-error"></div>
      <div class="table-responsive text-nowrap">
        <table class="table" id="booking-table">
          <thead>
            <tr>
              <th>ID</th><th>Guest</th><th>Email</th>
              <th>Room</th><th>Check-in</th><th>Check-out</th><th>Action</th>
            </tr>
          </thead>
          <tbody class="table-border-bottom-0">
            <!-- rows injected by existing JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>
  ```

---

## Group G — Build and verify

- [x] **G1** Run `make clean && make` from the project root. Expected: zero warnings,
  binary `appbooking` produced.

- [x] **G2** Run `./appbooking -p 8080 -d bookings.db` and open
  `http://localhost:8080/` in a browser.
  - Sidebar is visible and collapsible
  - Room availability check works (test with valid dates)
  - Booking form submits and shows success message
  - Navigate to `/admin` — booking table loads and Cancel works

- [x] **G3** Confirm vendor assets are served locally: in browser DevTools Network tab,
  verify `/vendor/css/core.css` returns HTTP 200 with `Content-Type: text/css`.
