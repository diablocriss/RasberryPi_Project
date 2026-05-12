# Skill: deploy-pi

---

## Purpose

Cross-compile and deploy the `appbooking-pi` binary to Raspberry Pi 4 targets via `make deploy` / `make deploy2`, and install the systemd service with `scripts/install-service.sh`.

---

## When to use

- Deploying a new binary to a Pi
- Changing deploy targets (hostname, path, user) in the Makefile
- Installing or updating the systemd service on the Pi
- Debugging deploy failures (SSH, scp, permission errors)

---

## Files involved

| File | Role |
|---|---|
| `Makefile` | `deploy` and `deploy2` targets; defines `PI_HOST`, `PI_DIR`, `PI2_HOST`, `PI2_DIR` |
| `appbooking-pi` | ARM binary produced by `make pi` |
| `scripts/install-service.sh` | Creates and enables `appbooking.service` via systemd |
| `scripts/backup-db.sh` | Backs up `bookings.db` to `~/backups/appbooking/` on the Pi |

---

## Constraints and gotchas

- Requires SSH key auth to Pi hosts — no interactive password prompts during `make deploy`.
- Pi #1: `admin@100.66.44.107` (Tailscale), Pi directory: `~/AppBookingResPi4`
- Pi #2: `pi@192.168.3.200`, Pi directory: `~/AppBookingResPi4`
- Cross-compiler must be installed locally: `sudo apt install gcc-arm-linux-gnueabihf`
- The binary is uploaded to `/tmp/appbooking_new` first, then atomically moved — avoids partial writes.
- `scripts/install-service.sh` must run as root on the Pi (`sudo ./scripts/install-service.sh`).
- `libsqlite3` must be installed on the Pi: `sudo apt install libsqlite3-2`
- The systemd service runs as user `pi` — change `User=` in the service template if needed.

---

## Patterns

### Full deploy sequence
```bash
# 1. Cross-compile
make pi

# 2. Deploy to Pi #1
make deploy

# 3. On Pi #1 — install or restart service
ssh admin@100.66.44.107 "cd ~/AppBookingResPi4 && sudo ./scripts/install-service.sh"

# 4. Verify service is running
ssh admin@100.66.44.107 "systemctl status appbooking --no-pager"
```

### Changing a deploy target
Edit `Makefile`:
```makefile
PI_HOST  = admin@<new-ip-or-hostname>
PI_DIR   = ~/AppBookingResPi4
```

### Manual backup before deploy
```bash
ssh admin@100.66.44.107 "cd ~/AppBookingResPi4 && ./scripts/backup-db.sh"
```

---

## Step-by-step: first-time Pi setup

1. Install SQLite on Pi: `sudo apt install libsqlite3-2`
2. `make pi` locally — produces `appbooking-pi`
3. `make deploy` — uploads binary and scripts
4. SSH to Pi: `ssh admin@100.66.44.107`
5. `cd ~/AppBookingResPi4 && sudo ./scripts/install-service.sh`
6. Verify: `curl http://100.66.44.107:8080/`

---

## Tests and verification

```bash
make pi
```
**Pass:** `[pi] Cross-compile successful: ./appbooking-pi`
**Fail:** `arm-linux-gnueabihf-gcc: not found` → install cross-compiler.

```bash
make deploy
```
**Pass:** No SSH errors; "Done. On the Pi:" message printed.
**Fail:** `ssh: connect to host ... port 22: Connection refused` → check Pi host is reachable.

After service install on Pi:
```bash
ssh admin@100.66.44.107 "curl -s http://localhost:8080/ | grep -c AppBookingRes"
```
**Pass:** `1`
**Fail:** `0` or connection refused → check `systemctl status appbooking` on Pi.
