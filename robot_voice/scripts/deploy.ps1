param(
    [string]$PiHost  = "192.168.2.3",
    [string]$User    = "phuong",
    [string]$KeyFile = "$env:USERPROFILE\.ssh\pi4_robot",
    [string]$Remote  = "/home/phuong/robot_voice",
    [switch]$InstallService,
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"
$Root   = Resolve-Path (Join-Path $PSScriptRoot "..")
$Target = "${User}@${PiHost}"

if (Test-Path $KeyFile) {
    $SshOpts = "-i `"$KeyFile`" -o StrictHostKeyChecking=no -o ConnectTimeout=10"
} else {
    Write-Host "[deploy] SSH key not found — using password auth"
    $SshOpts = "-o StrictHostKeyChecking=no -o ConnectTimeout=10"
}

function Remote-Run([string]$cmd) {
    Invoke-Expression "ssh $SshOpts $Target `"$cmd`""
}
function Remote-Copy([string]$local, [string]$dest) {
    Invoke-Expression "scp -r $SshOpts `"$local`" `"${Target}:${dest}`""
}

Write-Host "[deploy] Target : $Target`:$Remote"
Write-Host "[deploy] Local  : $Root"

# 1. Clean local __pycache__
Get-ChildItem -Path "$Root\src" -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force

# 2. Ensure remote dirs
Remote-Run "mkdir -p '$Remote' '$Remote/data' '$Remote/models'"

# 3. Sync directories
foreach ($dir in @("src","scripts","systemd","configs","docs","tests")) {
    $local = Join-Path $Root $dir
    if (Test-Path $local) {
        Write-Host "[deploy] syncing $dir/"
        Remote-Copy $local $Remote
    }
}

# 4. Sync root files
foreach ($file in @("requirements.txt","requirements-pi.txt","README.md","run_all.py")) {
    $local = Join-Path $Root $file
    if (Test-Path $local) {
        Write-Host "[deploy] syncing $file"
        Remote-Copy $local $Remote
    }
}

# 5. Fix script permissions
Remote-Run "find '$Remote/scripts' -name '*.sh' -exec chmod +x {} \;"
Write-Host "[deploy] Files synced."

# 6. Install Python deps on Pi
if (-not $NoInstall) {
    Write-Host "[deploy] Installing Python dependencies on Pi (this may take a while)..."
    Remote-Run "bash -lc 'cd $Remote && [ ! -d .venv ] && python3 -m venv --system-site-packages .venv || true && . .venv/bin/activate && pip install -q flask && echo pip-done'"
}

# 7. Install & start web-trainer.service
Write-Host "[deploy] Installing web-trainer systemd service..."
Remote-Run "sudo cp '$Remote/systemd/web-trainer.service' /etc/systemd/system/"
Remote-Run "sudo systemctl daemon-reload"
Remote-Run "sudo systemctl enable web-trainer.service"
Remote-Run "sudo systemctl restart web-trainer.service"
Start-Sleep 3
Remote-Run "sudo systemctl status web-trainer.service --no-pager -l" 2>&1 | Select-Object -First 20 | Write-Host

if ($InstallService) {
    foreach ($svc in @("wifi-portal.service","ollama-robot.service")) {
        $f = "$Remote/systemd/$svc"
        Remote-Run "[ -f '$f' ] && sudo cp '$f' /etc/systemd/system/ || true"
    }
    Remote-Run "sudo systemctl daemon-reload && sudo systemctl enable wifi-portal.service 2>/dev/null || true"
}

Write-Host ""
Write-Host "[deploy] Done!"
Write-Host "         Web Trainer -> http://${PiHost}:5000"
