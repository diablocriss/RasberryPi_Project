#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-Pi4phuong.local}"
USER="${2:-phuong}"
REMOTE="/home/$USER/robot_voice"
KEY="$HOME/.ssh/pi4_robot"
TARGET="$USER@$HOST"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SSH="ssh -i $KEY -o StrictHostKeyChecking=no"
SCP="scp -i $KEY -o StrictHostKeyChecking=no"

echo "[deploy] $TARGET:$REMOTE"

find "$ROOT/src" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

$SSH "$TARGET" "mkdir -p '$REMOTE'"

for dir in src scripts systemd configs docs; do
    [ -d "$ROOT/$dir" ] && echo "[deploy] $dir/" && $SCP -r "$ROOT/$dir" "$TARGET:$REMOTE"
done

for file in requirements.txt requirements-pi.txt README.md; do
    [ -f "$ROOT/$file" ] && echo "[deploy] $file" && $SCP "$ROOT/$file" "$TARGET:$REMOTE"
done

$SSH "$TARGET" "find '$REMOTE/scripts' -name '*.sh' -exec chmod +x {} \;"

echo "[deploy] Done."
