# Kişisel deploy: MSI → Acer (parametreleri düzenle)
param(
    [string]$HostName = "192.168.1.13",
    [string]$User = "YOUR_USER",
    [string]$RemotePath = "/srv/homelab/snow"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "Syncing $Root -> ${User}@${HostName}:$RemotePath"
# .env data'sını bilinçli kopyala; secret'ı scp ediyorsan ağa dikkat
scp -r "$Root\server" "$Root\web" "$Root\personal" "$Root\docker-compose.yml" "$Root\server\Dockerfile" "${User}@${HostName}:${RemotePath}/"

# .env varsa
if (Test-Path "$Root\.env") {
    scp "$Root\.env" "${User}@${HostName}:${RemotePath}/.env"
}

ssh "${User}@${HostName}" "cd $RemotePath && docker compose up -d --build && curl -s http://127.0.0.1:8787/api/v1/health"
Write-Host "Done."
