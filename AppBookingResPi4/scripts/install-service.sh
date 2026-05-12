#!/bin/bash
# Installs appbooking as a systemd service on the Raspberry Pi.
set -e

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=/etc/systemd/system/appbooking.service

cat > "$SERVICE" <<EOF
[Unit]
Description=AppBookingRes HTTP server
After=network.target

[Service]
ExecStart=$APP_DIR/appbooking -p 8080 -d $APP_DIR/bookings.db
Restart=on-failure
User=${SUDO_USER:-$USER}
WorkingDirectory=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable appbooking
systemctl restart appbooking
systemctl status appbooking --no-pager
echo "Service installed and started."
