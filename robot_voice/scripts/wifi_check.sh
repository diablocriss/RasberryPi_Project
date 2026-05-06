#!/usr/bin/env bash
# Start WiFi captive portal if not connected to any network.
# Runs as root via systemd.
set -euo pipefail

AP_SSID="RobotAP"
AP_PASS="robot1234"
PORTAL="$(dirname "$0")/wifi_portal.py"
IFACE="wlan0"

echo "[wifi-check] Checking WiFi connection..."

if nmcli -t -f STATE general | grep -q "^connected$"; then
    # Verify it's actual WiFi, not just tailscale/loopback
    if nmcli -t -f TYPE,STATE dev | grep -q "wifi:connected"; then
        echo "[wifi-check] WiFi connected, no portal needed."
        exit 0
    fi
fi

echo "[wifi-check] Not connected to WiFi."
echo "[wifi-check] Creating hotspot: SSID='$AP_SSID' password='$AP_PASS'"

# Remove any stale hotspot connection first
nmcli connection delete "Hotspot" 2>/dev/null || true

nmcli dev wifi hotspot \
    ifname "$IFACE" \
    ssid "$AP_SSID" \
    password "$AP_PASS" \
    band bg

echo "[wifi-check] Hotspot active."
echo "[wifi-check] Connect to '$AP_SSID' then open http://10.42.0.1"

exec python3 "$PORTAL"
