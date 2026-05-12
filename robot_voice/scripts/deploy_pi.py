#!/usr/bin/env python3
"""
deploy_pi.py — Deploy robot_voice to Pi 4 and start web-trainer service.
Usage: python scripts/deploy_pi.py
Requires: pip install paramiko scp
"""
import os
import sys
import time
from pathlib import Path

try:
    import paramiko
    from scp import SCPClient
except ImportError:
    print("[deploy] Installing paramiko + scp for SSH transport...")
    os.system(f"{sys.executable} -m pip install -q paramiko scp")
    import paramiko
    from scp import SCPClient

# ── Config ─────────────────────────────────────────────────────────────────
PI_HOST   = "192.168.2.3"
PI_USER   = "phuong"
PI_PASS   = "1"
REMOTE    = f"/home/{PI_USER}/robot_voice"
ROOT      = Path(__file__).resolve().parent.parent

SYNC_DIRS  = ["src", "scripts", "systemd", "configs", "docs", "tests"]
SYNC_FILES = ["requirements.txt", "requirements-pi.txt", "README.md", "run_all.py"]

# ── Helpers ────────────────────────────────────────────────────────────────
def run(client: paramiko.SSHClient, cmd: str, show=True) -> str:
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if show and out.strip():
        print(out.strip())
    if show and err.strip():
        print("[stderr]", err.strip())
    return out

def progress(filename, size, sent):
    pct = int(sent / size * 100) if size else 100
    print(f"\r  {Path(filename).name:<40} {pct:3d}%", end="", flush=True)

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    print(f"[deploy] Connecting to {PI_USER}@{PI_HOST} ...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(PI_HOST, username=PI_USER, password=PI_PASS, timeout=15)
    print("[deploy] Connected.")

    # 1. Create remote dirs
    run(client, f"mkdir -p {REMOTE} {REMOTE}/data {REMOTE}/models", show=False)

    # 2. Clean local __pycache__
    for p in (ROOT / "src").rglob("__pycache__"):
        import shutil; shutil.rmtree(p, ignore_errors=True)

    # 3. SCP files
    with SCPClient(client.get_transport(), progress=progress) as scp:
        for d in SYNC_DIRS:
            local = ROOT / d
            if local.exists():
                print(f"[deploy] syncing {d}/")
                scp.put(str(local), remote_path=REMOTE, recursive=True)
                print()
        for f in SYNC_FILES:
            local = ROOT / f
            if local.exists():
                print(f"[deploy] syncing {f}")
                scp.put(str(local), remote_path=REMOTE)
                print()

    # 4. Fix permissions
    run(client, f"find {REMOTE}/scripts -name '*.sh' -exec chmod +x {{}} \\;", show=False)
    print("[deploy] Files synced.")

    # 5. Install Flask (fast — already cached usually)
    print("[deploy] Installing Flask on Pi...")
    run(client, (
        f"cd {REMOTE} && "
        f"[ ! -d .venv ] && python3 -m venv --system-site-packages .venv || true && "
        f". .venv/bin/activate && pip install -q flask && echo '[pi] Flask ready'"
    ))

    # 6. Install & start systemd service
    print("[deploy] Installing web-trainer.service ...")
    run(client, f"sudo cp {REMOTE}/systemd/web-trainer.service /etc/systemd/system/")
    run(client, "sudo systemctl daemon-reload")
    run(client, "sudo systemctl enable web-trainer.service")
    run(client, "sudo systemctl restart web-trainer.service")
    time.sleep(3)
    status = run(client, "sudo systemctl status web-trainer.service --no-pager -l")
    print()

    if "active (running)" in status:
        print(f"[deploy] ✅ web-trainer is RUNNING")
    else:
        print(f"[deploy] ⚠️  Service may not be running — check: sudo journalctl -u web-trainer -n 30")

    client.close()
    print()
    print(f"[deploy] Done!  Web Trainer → http://{PI_HOST}:5000")
    print(f"         Access from any device on your network.")

if __name__ == "__main__":
    main()
