#!/bin/bash
# Backs up bookings.db to a timestamped file in ~/backups/.
set -e

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$HOME/backups/appbooking"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DEST="$BACKUP_DIR/bookings-$TIMESTAMP.db"

mkdir -p "$BACKUP_DIR"
cp "$APP_DIR/bookings.db" "$DEST"
echo "Backup saved to $DEST"

# Keep only the last 10 backups
ls -t "$BACKUP_DIR"/*.db 2>/dev/null | tail -n +11 | xargs rm -f
