param(
    [string]$PiHost  = "Pi4phuong.local",
    [string]$User    = "phuong",
    [string]$KeyFile = "$env:USERPROFILE\.ssh\pi4_robot",
    [string]$Remote  = "/home/phuong/robot_voice",
    [switch]$InstallService
)

$ErrorActionPreference = "Stop"
$Root      = Resolve-Path (Join-Path $PSScriptRoot "..")
$Target    = "${User}@${PiHost}"
$SshOpts   = "-i `"$KeyFile`" -o StrictHostKeyChecking=no"

Write-Host "[deploy] $Target`:$Remote"

# Remove __pycache__ before transfer
Get-ChildItem -Path "$Root\src" -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force

Invoke-Expression "ssh $SshOpts $Target `"mkdir -p '$Remote'`""

$Dirs  = @("src", "scripts", "systemd", "configs", "docs", "tests")
$Files = @("requirements.txt", "requirements-pi.txt", "README.md")

foreach ($dir in $Dirs) {
    $local = Join-Path $Root $dir
    if (Test-Path $local) {
        Write-Host "[deploy] $dir/"
        Invoke-Expression "scp -r $SshOpts `"$local`" `"${Target}:${Remote}`""
    }
}

foreach ($file in $Files) {
    $local = Join-Path $Root $file
    if (Test-Path $local) {
        Write-Host "[deploy] $file"
        Invoke-Expression "scp $SshOpts `"$local`" `"${Target}:${Remote}`""
    }
}

Invoke-Expression "ssh $SshOpts $Target `"find '$Remote/scripts' -name '*.sh' -exec chmod +x {} \;`""

if ($InstallService) {
    Write-Host "[deploy] Installing systemd services..."
    Invoke-Expression "ssh $SshOpts $Target `"sudo cp '$Remote/systemd/wifi-portal.service' /etc/systemd/system/ && sudo cp '$Remote/systemd/ollama-robot.service' /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable wifi-portal.service`""
    Write-Host "[deploy] Services installed."
}

Write-Host "[deploy] Done."
