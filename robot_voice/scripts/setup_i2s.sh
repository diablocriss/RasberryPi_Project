#!/usr/bin/env bash
set -euo pipefail

BOOT_CONFIG="${BOOT_CONFIG:-/boot/firmware/config.txt}"
APPLY="${1:-check}"

cat <<'INFO'
[setup-i2s] Target wiring:
  GPIO18 BCLK -> INMP441 SCK + MAX98357 BCLK
  GPIO19 LRCLK -> INMP441 WS + MAX98357 LRC
  GPIO21 DIN <- INMP441 SD
  GPIO20 DOUT -> MAX98357 DIN
INFO

if [[ "$APPLY" != "--apply" ]]; then
  echo "[setup-i2s] Dry run only. Use: sudo bash scripts/setup_i2s.sh --apply"
  echo "[setup-i2s] Current boot audio lines:"
  grep -Ei '^(dtparam=audio|dtoverlay=.*(i2s|hifi|dac|mic|audio))' "$BOOT_CONFIG" || true
  exit 0
fi

if [[ $EUID -ne 0 ]]; then
  echo "[setup-i2s] Must run as root for --apply" >&2
  exit 1
fi

cp "$BOOT_CONFIG" "${BOOT_CONFIG}.bak.$(date +%Y%m%d%H%M%S)"
if ! grep -q '^dtoverlay=hifiberry-dac' "$BOOT_CONFIG"; then
  echo 'dtoverlay=hifiberry-dac' >> "$BOOT_CONFIG"
fi

echo "[setup-i2s] Added MAX98357-compatible DAC overlay if missing."
echo "[setup-i2s] INMP441 capture may require a board-specific/custom overlay; inspect available overlays with:"
echo "  ls /boot/firmware/overlays | grep -Ei 'i2s|mic|adc|hifi'"
echo "[setup-i2s] Reboot, then run: bash scripts/pi_process.sh check"