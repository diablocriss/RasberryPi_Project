param(
    [string]$HostName = "robothead.local",
    [string]$User = "darkzero",
    [string]$RemotePath = "/home/darkzero/robot_voice"
)

$ErrorActionPreference = "Stop"

Write-Host "Deploying robot_voice to ${User}@${HostName}:${RemotePath}"
ssh "$User@$HostName" "mkdir -p '$RemotePath'"
scp -r "$PSScriptRoot\..\src" "${User}@${HostName}:${RemotePath}"
scp "$PSScriptRoot\..\requirements.txt" "${User}@${HostName}:${RemotePath}"
Write-Host "Deploy complete"
