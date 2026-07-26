# Snow — Acer'da tamamen sil + sıfırdan deploy
#
# PowerShell (MSI):
#   cd C:\Users\Xelma123\Desktop\Homelab\snow
#   .\scripts\redeploy-clean.ps1 -User UBUNTU_KULLANICI_ADIN
#
# Varsayılan sunucu: 192.168.1.13

param(
    [string]$HostName = "192.168.1.13",
    [Parameter(Mandatory = $true)]
    [string]$User,
    [string]$RemotePath = "/srv/homelab/snow",
    [switch]$SkipWipe
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Test-Path "$Root\docker-compose.yml")) {
    throw "docker-compose.yml bulunamadı: $Root"
}
if (-not (Test-Path "$Root\.env")) {
    throw ".env yok: $Root\.env  (personal\env.example kopyala ve doldur)"
}

$target = "${User}@${HostName}"
Write-Host ""
Write-Host "=== Snow clean redeploy ===" -ForegroundColor Cyan
Write-Host "Local : $Root"
Write-Host "Remote: ${target}:${RemotePath}"
Write-Host ""

function Invoke-Remote([string]$Cmd) {
    ssh -o StrictHostKeyChecking=accept-new $target $Cmd
    if ($LASTEXITCODE -ne 0) {
        throw "SSH komutu basarisiz (exit $LASTEXITCODE): $Cmd"
    }
}

# --- 1) Wipe ---
if (-not $SkipWipe) {
    Write-Host "[1/4] Eski Snow siliniyor..." -ForegroundColor Yellow
    # Tek satir bash: compose down + klasor sil + yeniden olustur
    $wipe = "bash -lc 'set -e; if [ -d $RemotePath ]; then cd $RemotePath && (docker compose down --remove-orphans || true) && (docker rm -f snow || true); fi; sudo rm -rf $RemotePath; sudo mkdir -p $RemotePath; sudo chown -R `$(whoami):`$(whoami) /srv/homelab; echo WIPE_OK'"
    Invoke-Remote $wipe
} else {
    Write-Host "[1/4] Wipe atlandi (-SkipWipe)" -ForegroundColor DarkYellow
    Invoke-Remote "bash -lc 'sudo mkdir -p $RemotePath; sudo chown -R `$(whoami):`$(whoami) /srv/homelab'"
}

# --- 2) Pack local tree ---
Write-Host "[2/4] Paket hazirlaniyor..." -ForegroundColor Yellow
$staging = Join-Path $env:TEMP "snow-deploy-staging"
$tar = Join-Path $env:TEMP "snow-deploy.tgz"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
if (Test-Path $tar) { Remove-Item $tar -Force }
New-Item -ItemType Directory -Path $staging | Out-Null
New-Item -ItemType Directory -Path "$staging\data" -Force | Out-Null

Copy-Item "$Root\server"         "$staging\server" -Recurse
Copy-Item "$Root\web"            "$staging\web" -Recurse
Copy-Item "$Root\personal"       "$staging\personal" -Recurse
Copy-Item "$Root\docker-compose.yml" "$staging\docker-compose.yml"
Copy-Item "$Root\.env"           "$staging\.env"

Push-Location $staging
try {
    tar -czf $tar .
    if ($LASTEXITCODE -ne 0) { throw "tar basarisiz" }
} finally {
    Pop-Location
}

# --- 3) Upload ---
Write-Host "[3/4] scp ile yukleniyor..." -ForegroundColor Yellow
scp -o StrictHostKeyChecking=accept-new $tar "${target}:/tmp/snow-deploy.tgz"
if ($LASTEXITCODE -ne 0) { throw "scp basarisiz" }

Invoke-Remote "bash -lc 'set -e; cd $RemotePath; tar -xzf /tmp/snow-deploy.tgz; rm -f /tmp/snow-deploy.tgz; chmod 600 .env; ls -la'"

Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $tar -Force -ErrorAction SilentlyContinue

# --- 4) Docker ---
Write-Host "[4/4] docker compose up -d --build ..." -ForegroundColor Yellow
$boot = "bash -lc 'set -e; cd $RemotePath; docker compose up -d --build; sleep 3; docker compose ps; echo ---health---; curl -sS http://127.0.0.1:8787/api/v1/health; echo; echo ---deep---; curl -sS \"http://127.0.0.1:8787/api/v1/health?deep=1\"; echo'"
Invoke-Remote $boot

Write-Host ""
Write-Host "Bitti." -ForegroundColor Green
Write-Host "  Panel : http://${HostName}:8787/"
Write-Host "  Ses   : http://${HostName}:8787/voice"
Write-Host "  APK   : Snow-Ses-release.apk (IP 192.168.1.13)"
Write-Host ""
