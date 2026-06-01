# Skill: deploy-pi

> Cross-compile and deploy robot_voice or AppBookingResPi4 to Raspberry Pi targets.
> Last updated: 2026-05-31 | Confidence: high | Status: active

---

## Purpose
Cross-compile and deploy both subsystems to Raspberry Pi targets via SSH/SCP.

## Deploy targets

| Name | Host | User | Path | Arch | Subsystem |
|------|------|------|------|------|-----------|
| Robot Pi | 192.168.1.66 | phuong | ~ | ARMv8 (Pi 4) | robot_voice (Python) |
| Booking Pi #1 | 100.122.45.123 | phuong | ~/AppBookingResPi4 | ARMv7 (armhf) | AppBookingResPi4 (C) |
| Booking Pi #2 | 192.168.3.200 | pi | ~/AppBookingResPi4 | ARMv7 (armhf) | AppBookingResPi4 (C) |

## Deploy commands

### Python subsystem (robot_voice/)

```powershell
# From Windows — deploys via rsync over SSH
.\robot_voice\scripts\deploy.ps1 -Password "1"
```

```bash
# On the Pi — runtime modes
bash scripts/pi_process.sh check         # one-time setup check
bash scripts/pi_process.sh pi-audio-live # live mode (real UART)
```

### C subsystem (AppBookingResPi4/)

```bash
# Cross-compile for Pi 4 (32-bit armhf)
cd AppBookingResPi4 && make pi

# Cross-compile for Pi 4 (64-bit aarch64)
cd AppBookingResPi4 && make pi64

# Deploy to Pi #1
cd AppBookingResPi4 && make deploy      # uses armhf binary
cd AppBookingResPi4 && make deploy64    # uses aarch64 binary

# Deploy to Pi #2
cd AppBookingResPi4 && make deploy2

# Install as systemd service (run on the Pi after deploy)
cd ~/AppBookingResPi4 && sudo ./scripts/install-service.sh
```

## Post-deploy verification

```bash
# Robot Pi
ssh phuong@192.168.1.66 "ROBOT_WORKFLOW=text_hybrid ROBOT_DRY_RUN=1 python3 -c 'import src.main'"

# Booking Pi
curl http://100.122.45.123:8080/api/bookings
```

## Prerequisites
- Cross-compiler: `sudo apt install gcc-arm-linux-gnueabihf` (armhf) or `aarch64-linux-gnu-gcc` (aarch64)
- SSH key auth configured to both Pi targets
- `xxd` installed for HTML embedding: `sudo apt install xxd`
