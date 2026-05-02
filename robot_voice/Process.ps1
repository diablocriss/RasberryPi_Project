param(
    [switch]$Install,
    [switch]$Smoke,
    [switch]$AllCommands
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path $VenvPython)) {
    py -3 -m venv .venv
    $Install = $true
}

if ($Install) {
    & $VenvPython -m pip install -r requirements.txt
}

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

Write-Host "Running compile check..."
& $VenvPython -m compileall -q src tests

Write-Host "Running tests..."
& $VenvPython -m pytest -q

if ($Smoke -or $AllCommands) {
    Write-Host "Running text workflow command test..."
    $env:ROBOT_WORKFLOW = "text_hybrid"
    $env:ROBOT_DRY_RUN = "1"
    $env:ROBOT_UART_PORT = "COM3"

    if ($AllCommands) {
        @"
move forward
move foward
go forward
forward
foward
move backward
go backward
backward
move left
turn left
left
move right
turn right
right
speed up
slow down
emergency stop
stop
exit
"@ | & $VenvPython src/main.py
    } else {
        "move forward`nexit`n" | & $VenvPython src/main.py
    }
}
