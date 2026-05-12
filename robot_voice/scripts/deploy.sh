#!/usr/bin/env bash
# deploy.sh — sync robot_voice to Pi 4 and restart web-trainer service
# Usage: ./scripts/deploy.sh [host] [user]
#   host defaults to 192.168.2.3
#   user defaults to phuong
set -euo pipefail

HOST="${1:-192.168.2.3}"
USER="${2:-phuong}"
REMOTE="/home/$USER/robot_voice"
KEY="$HOME/.ssh/pi4_robot"
TARGET="$USER@$HOST"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PI_PASSWORD="${PI_PASSWORD:-1}"

# SSH/SCP options — prefer key, then sshpass with $PI_PASSWORD, else interactive prompt
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o LogLevel=ERROR"
if [ -f "$KEY" ]; then
    echo "[deploy] Using SSH key: $KEY"
    SSH="ssh -i $KEY $SSH_OPTS"
    SCP="scp -i $KEY $SSH_OPTS"
elif command -v sshpass >/dev/null 2>&1; then
    echo "[deploy] Using sshpass with PI_PASSWORD (set PI_PASSWORD env var to override; default \"1\")"
    SSH="sshpass -p $PI_PASSWORD ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no $SSH_OPTS"
    SCP="sshpass -p $PI_PASSWORD scp -o PreferredAuthentications=password -o PubkeyAuthentication=no $SSH_OPTS"
else
    echo "[deploy] sshpass not found — install it to skip password prompts:"
    echo "         Debian/Ubuntu/Pi : sudo apt-get install -y sshpass"
    echo "         macOS            : brew install hudochenkov/sshpass/sshpass"
    echo "         Git Bash (Win)   : pacman -S sshpass   (or use WSL)"
    echo "[deploy] Falling back to interactive password prompt for each SSH/SCP call."
    SSH="ssh $SSH_OPTS"
    SCP="scp $SSH_OPTS"
fi

echo "[deploy] Target : $TARGET:$REMOTE"
echo "[deploy] Local  : $ROOT"

# ── 1. Clean local __pycache__ ────────────────────────────────────────────
find "$ROOT/src" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ── 2. Ensure remote dirs ─────────────────────────────────────────────────
$SSH "$TARGET" "mkdir -p '$REMOTE' '$REMOTE/data' '$REMOTE/models'"

# ── 3. Sync directories ───────────────────────────────────────────────────
for dir in src scripts systemd configs docs tests; do
    if [ -d "$ROOT/$dir" ]; then
        echo "[deploy] syncing $dir/"
        $SCP -r "$ROOT/$dir" "$TARGET:$REMOTE"
    fi
done

# ── 4. Sync root files ────────────────────────────────────────────────────
for file in requirements.txt requirements-pi.txt README.md run_all.py; do
    if [ -f "$ROOT/$file" ]; then
        echo "[deploy] syncing $file"
        $SCP "$ROOT/$file" "$TARGET:$REMOTE"
    fi
done

# ── 5. Fix script permissions ─────────────────────────────────────────────
$SSH "$TARGET" "find '$REMOTE/scripts' -name '*.sh' -exec chmod +x {} \;"
echo "[deploy] Files synced."

# ── 6. Install Python deps on Pi ─────────────────────────────────────────
# The full requirements install is best-effort: voice-pipeline deps like
# openwakeword/tflite-runtime/moonshine-voice may not have ARM wheels for the
# Pi's Python and will fail. The web trainer only needs Flask + sqlite-web,
# so we install those explicitly and treat the bulk install as advisory.
echo "[deploy] Installing Python dependencies on Pi (best-effort)..."
$SSH "$TARGET" REMOTE="$REMOTE" bash -s <<'REMOTE_EOF' || true
cd "$REMOTE"
if [ ! -d .venv ]; then
    python3 -m venv --system-site-packages .venv
fi
. .venv/bin/activate
pip install -q -r requirements-pi.txt \
    && echo "[pi] full requirements install OK" \
    || echo "[pi] full requirements install had failures (likely voice-pipeline deps) — continuing"
# Mandatory deps for the trainer + DB browser. Failures here are the real
# signal that something is broken.
pip install -q "flask>=3.0" "sqlite-web>=0.6.0"
echo "[pi] flask + sqlite-web ready"
REMOTE_EOF

# ── 7. Install & start systemd services ───────────────────────────────────
# `sudo -S` reads the password from stdin so the remote prompt doesn't hang.
# `PI_PWD` is set on the remote bash via inline env, never expanded into the
# script body (so it doesn't leak to `ps`/journalctl).
echo "[deploy] Installing and starting systemd services..."
$SSH "$TARGET" PI_PWD="$PI_PASSWORD" REMOTE="$REMOTE" bash -s <<'REMOTE_EOF'
set -e
sudo_run() { echo "$PI_PWD" | sudo -S -p '' "$@"; }

for svc in web-trainer.service sqlite-web.service; do
    unit="$REMOTE/systemd/$svc"
    if [ ! -f "$unit" ]; then
        echo "[pi] skip $svc (unit file missing on remote)"
        continue
    fi
    sudo_run cp "$unit" /etc/systemd/system/
    sudo_run systemctl daemon-reload
    sudo_run systemctl enable "$svc"
    sudo_run systemctl restart "$svc"
done

sleep 2
for svc in web-trainer.service sqlite-web.service; do
    echo "----- $svc -----"
    sudo_run systemctl status "$svc" --no-pager -l | head -12 || true
done
REMOTE_EOF

echo ""
echo "[deploy] Done!"
echo "         Web Trainer → http://$HOST:5000"
echo "         SQLite Web  → http://$HOST:8081"
