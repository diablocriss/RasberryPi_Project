param(
    [string]$HostName = "192.168.1.66",
    [string]$User = "phuong",
    [string]$RemotePath = "/home/phuong/robot_voice",
    [string]$Password = "",
    [string]$HostKey = "SHA256:0SrDYZk2EcWwSeZEQDh5rq3r/VM8b2Rwjcti3YGZsSs"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "Deploying robot_voice to ${User}@${HostName}:${RemotePath}"

Get-ChildItem -Path "$ProjectRoot\src", "$ProjectRoot\tests" -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force

if ($Password) {
    $Plink = "C:\Program Files\PuTTY\plink.exe"
    $Pscp = "C:\Program Files\PuTTY\pscp.exe"

    & $Plink -ssh "${User}@${HostName}" -hostkey $HostKey -pw $Password -batch "mkdir -p '$RemotePath'"
    & $Pscp -r -hostkey $HostKey -pw $Password "$ProjectRoot\src" "${User}@${HostName}:${RemotePath}"
    & $Pscp -r -hostkey $HostKey -pw $Password "$ProjectRoot\tests" "${User}@${HostName}:${RemotePath}"
    & $Pscp -r -hostkey $HostKey -pw $Password "$ProjectRoot\scripts" "${User}@${HostName}:${RemotePath}"
    & $Pscp -r -hostkey $HostKey -pw $Password "$ProjectRoot\configs" "${User}@${HostName}:${RemotePath}"
    & $Pscp -r -hostkey $HostKey -pw $Password "$ProjectRoot\docs" "${User}@${HostName}:${RemotePath}"
    & $Pscp -r -hostkey $HostKey -pw $Password "$ProjectRoot\models" "${User}@${HostName}:${RemotePath}"
    & $Pscp -r -hostkey $HostKey -pw $Password "$ProjectRoot\logs" "${User}@${HostName}:${RemotePath}"
    & $Pscp -hostkey $HostKey -pw $Password "$ProjectRoot\requirements.txt" "${User}@${HostName}:${RemotePath}"
    & $Pscp -hostkey $HostKey -pw $Password "$ProjectRoot\requirements-pi.txt" "${User}@${HostName}:${RemotePath}"
    & $Pscp -hostkey $HostKey -pw $Password "$ProjectRoot\README.md" "${User}@${HostName}:${RemotePath}"
    & $Pscp -hostkey $HostKey -pw $Password "$ProjectRoot\.env.example" "${User}@${HostName}:${RemotePath}"
    & $Pscp -hostkey $HostKey -pw $Password "$ProjectRoot\project_map.yaml" "${User}@${HostName}:${RemotePath}"
    & $Pscp -hostkey $HostKey -pw $Password "$ProjectRoot\progress_tracker.yaml" "${User}@${HostName}:${RemotePath}"
    & $Pscp -hostkey $HostKey -pw $Password "$ProjectRoot\quick_commands.sh" "${User}@${HostName}:${RemotePath}"
    & $Plink -ssh "${User}@${HostName}" -hostkey $HostKey -pw $Password -batch "chmod +x '$RemotePath/scripts/'*.sh '$RemotePath/quick_commands.sh'"
} else {
    ssh "$User@$HostName" "mkdir -p '$RemotePath'"
    scp -r "$ProjectRoot\src" "${User}@${HostName}:${RemotePath}"
    scp -r "$ProjectRoot\tests" "${User}@${HostName}:${RemotePath}"
    scp -r "$ProjectRoot\scripts" "${User}@${HostName}:${RemotePath}"
    scp -r "$ProjectRoot\configs" "${User}@${HostName}:${RemotePath}"
    scp -r "$ProjectRoot\docs" "${User}@${HostName}:${RemotePath}"
    scp -r "$ProjectRoot\models" "${User}@${HostName}:${RemotePath}"
    scp -r "$ProjectRoot\logs" "${User}@${HostName}:${RemotePath}"
    scp "$ProjectRoot\requirements.txt" "${User}@${HostName}:${RemotePath}"
    scp "$ProjectRoot\requirements-pi.txt" "${User}@${HostName}:${RemotePath}"
    scp "$ProjectRoot\README.md" "${User}@${HostName}:${RemotePath}"
    scp "$ProjectRoot\.env.example" "${User}@${HostName}:${RemotePath}"
    scp "$ProjectRoot\project_map.yaml" "${User}@${HostName}:${RemotePath}"
    scp "$ProjectRoot\progress_tracker.yaml" "${User}@${HostName}:${RemotePath}"
    scp "$ProjectRoot\quick_commands.sh" "${User}@${HostName}:${RemotePath}"
    ssh "$User@$HostName" "chmod +x '$RemotePath/scripts/'*.sh '$RemotePath/quick_commands.sh'"
}

Write-Host "Deploy complete"
