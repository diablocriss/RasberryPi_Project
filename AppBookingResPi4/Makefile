# ── AppBookingRes — Makefile ────────────────────────────────────────────────
#
#  make              → native build (x86_64, WSL2/Ubuntu)
#  make pi           → cross-compile for Raspberry Pi 4 (arm-linux-gnueabihf)
#  make deploy       → deploy to Pi #1  (admin@<PI_HOST>)
#  make deploy2      → deploy to Pi #2  (pi@<PI2_HOST>)
#  make clean        → remove all build artifacts
#  sudo make install → install native binary to /usr/local/bin

# ── Raspberry Pi #1 ──────────────────────────────────────────────────────────
PI_HOST   = phuong@100.122.45.123
PI_DIR    = ~/AppBookingResPi4
PI_CC     = arm-linux-gnueabihf-gcc

# ── Raspberry Pi #2 ──────────────────────────────────────────────────────────
PI2_HOST  = pi@192.168.3.200
PI2_DIR   = ~/AppBookingResPi4

# ── Common sources ─────────────────────────────────────────────────────────
SRCDIR  = src
SRCS    = $(SRCDIR)/main.c      \
          $(SRCDIR)/server.c    \
          $(SRCDIR)/booking.c   \
          $(SRCDIR)/storage.c   \
          $(SRCDIR)/api.c       \
          $(SRCDIR)/web.c       \
          $(SRCDIR)/sqlite3.c

CFLAGS  = -Wall -Wextra -O2 -std=c11 -D_GNU_SOURCE
LDFLAGS = -lpthread

# ── Native build (x86_64) ──────────────────────────────────────────────────
TARGET   = appbooking
OBJS     = $(patsubst $(SRCDIR)/%.c, build/obj/%.o, $(SRCS))

.PHONY: all pi pi64 deploy deploy2 deploy64 clean install

all: $(TARGET)

# ── Embedded HTML (auto-generated from web/*.html) ─────────────────────────
src/index_html.h: web/index.html
	xxd -i $< | sed 's/web_index_html/index_html/g' > $@

src/admin_html.h: web/admin.html
	xxd -i $< | sed 's/web_admin_html/admin_html/g' > $@

src/vendor_core_css.h: web/vendor/css/core.css
	xxd -i $< | sed 's/web_vendor_css_core_css/vendor_core_css/g' > $@

src/vendor_bootstrap_js.h: web/vendor/js/bootstrap.js
	xxd -i $< | sed 's/web_vendor_js_bootstrap_js/vendor_bootstrap_js/g' > $@

src/vendor_helpers_js.h: web/vendor/js/helpers.js
	xxd -i $< | sed 's/web_vendor_js_helpers_js/vendor_helpers_js/g' > $@

src/vendor_menu_js.h: web/vendor/js/menu.js
	xxd -i $< | sed 's/web_vendor_js_menu_js/vendor_menu_js/g' > $@

$(TARGET): src/index_html.h src/admin_html.h \
           src/vendor_core_css.h src/vendor_bootstrap_js.h \
           src/vendor_helpers_js.h src/vendor_menu_js.h \
           $(OBJS)
	$(CC) $(CFLAGS) -o $@ $(OBJS) $(LDFLAGS)
	@echo ""
	@echo "  [native] Build successful: ./$(TARGET)"
	@echo "  Run with:  ./$(TARGET) -p 8080"
	@echo ""

build/obj/web.o: src/index_html.h src/admin_html.h \
                 src/vendor_core_css.h src/vendor_bootstrap_js.h \
                 src/vendor_helpers_js.h src/vendor_menu_js.h
build/obj-pi/web.o: src/index_html.h src/admin_html.h \
                    src/vendor_core_css.h src/vendor_bootstrap_js.h \
                    src/vendor_helpers_js.h src/vendor_menu_js.h

build/obj/sqlite3.o: $(SRCDIR)/sqlite3.c
	@mkdir -p build/obj
	$(CC) -O2 -std=c11 -D_GNU_SOURCE -c -o $@ $<

build/obj/%.o: $(SRCDIR)/%.c
	@mkdir -p build/obj
	$(CC) $(CFLAGS) -c -o $@ $<

# ── Raspberry Pi cross-compile (arm-linux-gnueabihf) ──────────────────────
PI_TARGET = appbooking-pi
PI_OBJS   = $(patsubst $(SRCDIR)/%.c, build/obj-pi/%.o, $(SRCS))

pi: src/index_html.h src/admin_html.h \
    src/vendor_core_css.h src/vendor_bootstrap_js.h \
    src/vendor_helpers_js.h src/vendor_menu_js.h \
    $(PI_TARGET)

$(PI_TARGET): $(PI_OBJS)
	$(PI_CC) $(CFLAGS) -o $@ $(PI_OBJS) $(LDFLAGS)
	@echo ""
	@echo "  [pi] Cross-compile successful: ./$(PI_TARGET)"
	@echo "  Deploy with:  make deploy"
	@echo ""

build/obj-pi/sqlite3.o: $(SRCDIR)/sqlite3.c
	@mkdir -p build/obj-pi
	$(PI_CC) -O2 -std=c11 -D_GNU_SOURCE -c -o $@ $<

build/obj-pi/%.o: $(SRCDIR)/%.c
	@mkdir -p build/obj-pi
	$(PI_CC) $(CFLAGS) -c -o $@ $<

# ── Raspberry Pi aarch64 64-bit ────────────────────────────────────────────
PI64_CC     = aarch64-linux-gnu-gcc
PI64_TARGET = appbooking-pi64
PI64_OBJS   = $(patsubst $(SRCDIR)/%.c, build/obj-pi64/%.o, $(SRCS))

pi64: src/index_html.h src/admin_html.h \
      src/vendor_core_css.h src/vendor_bootstrap_js.h \
      src/vendor_helpers_js.h src/vendor_menu_js.h \
      $(PI64_TARGET)

$(PI64_TARGET): $(PI64_OBJS)
	$(PI64_CC) $(CFLAGS) -o $@ $(PI64_OBJS) $(LDFLAGS)
	@echo ""
	@echo "  [pi64] Cross-compile successful: ./$(PI64_TARGET)"
	@echo "  Deploy with:  make deploy64"
	@echo ""

build/obj-pi64/sqlite3.o: $(SRCDIR)/sqlite3.c
	@mkdir -p build/obj-pi64
	$(PI64_CC) -O2 -std=c11 -D_GNU_SOURCE -c -o $@ $<

build/obj-pi64/%.o: $(SRCDIR)/%.c
	@mkdir -p build/obj-pi64
	$(PI64_CC) $(CFLAGS) -c -o $@ $<</

build/obj-pi64/web.o: src/index_html.h src/admin_html.h \
                      src/vendor_core_css.h src/vendor_bootstrap_js.h \
                      src/vendor_helpers_js.h src/vendor_menu_js.h

# ── Deploy pi64 to Pi #1 ───────────────────────────────────────────────────
deploy64: $(PI64_TARGET)
	@echo "  Uploading to $(PI_HOST):$(PI_DIR) ..."
	ssh $(PI_HOST) "mkdir -p $(PI_DIR)/scripts"
	scp $(PI64_TARGET)             $(PI_HOST):/tmp/appbooking_new
	ssh $(PI_HOST) "mv /tmp/appbooking_new $(PI_DIR)/appbooking && chmod +x $(PI_DIR)/appbooking"
	scp scripts/install-service.sh $(PI_HOST):$(PI_DIR)/scripts/install-service.sh
	scp scripts/backup-db.sh       $(PI_HOST):$(PI_DIR)/scripts/backup-db.sh
	ssh $(PI_HOST) "chmod +x $(PI_DIR)/scripts/*.sh"
	@echo ""
	@echo "  Done. On the Pi:"
	@echo "    cd $(PI_DIR) && sudo ./scripts/install-service.sh"
	@echo ""


# ── Deploy to Pi #1 via scp ────────────────────────────────────────────────
deploy: $(PI_TARGET)
	@echo "  Uploading to $(PI_HOST):$(PI_DIR) ..."
	ssh $(PI_HOST) "mkdir -p $(PI_DIR)/scripts"
	scp $(PI_TARGET)               $(PI_HOST):/tmp/appbooking_new
	ssh $(PI_HOST) "mv /tmp/appbooking_new $(PI_DIR)/appbooking && chmod +x $(PI_DIR)/appbooking"
	scp scripts/install-service.sh $(PI_HOST):$(PI_DIR)/scripts/install-service.sh
	scp scripts/backup-db.sh       $(PI_HOST):$(PI_DIR)/scripts/backup-db.sh
	ssh $(PI_HOST) "chmod +x $(PI_DIR)/scripts/*.sh"
	@echo ""
	@echo "  Done. On the Pi:"
	@echo "    cd $(PI_DIR) && sudo ./scripts/install-service.sh"
	@echo ""

# ── Deploy to Pi #2 ────────────────────────────────────────────────────────
deploy2: $(PI_TARGET)
	@echo "  Uploading to $(PI2_HOST):$(PI2_DIR) ..."
	ssh $(PI2_HOST) "mkdir -p $(PI2_DIR)/scripts"
	scp $(PI_TARGET)               $(PI2_HOST):/tmp/appbooking_new
	ssh $(PI2_HOST) "mv /tmp/appbooking_new $(PI2_DIR)/appbooking && chmod +x $(PI2_DIR)/appbooking"
	scp scripts/install-service.sh $(PI2_HOST):$(PI2_DIR)/scripts/install-service.sh
	scp scripts/backup-db.sh       $(PI2_HOST):$(PI2_DIR)/scripts/backup-db.sh
	ssh $(PI2_HOST) "chmod +x $(PI2_DIR)/scripts/*.sh"
	@echo ""
	@echo "  Done. On Pi #2:"
	@echo "    cd $(PI2_DIR) && sudo ./scripts/install-service.sh"
	@echo ""

# ── Clean ──────────────────────────────────────────────────────────────────
clean:
	rm -f $(OBJS) $(PI_OBJS) $(PI64_OBJS) \
	      $(TARGET) $(PI_TARGET) $(PI64_TARGET) \
	      src/index_html.h src/admin_html.h \
	      src/vendor_core_css.h src/vendor_bootstrap_js.h \
	      src/vendor_helpers_js.h src/vendor_menu_js.h
	rm -rf build/obj build/obj-pi build/obj-pi64

# ── Install native binary ──────────────────────────────────────────────────
install: $(TARGET)
	install -m 755 $(TARGET) /usr/local/bin/$(TARGET)
	@echo "Installed to /usr/local/bin/$(TARGET)"
