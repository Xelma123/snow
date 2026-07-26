# Snow PC Agent launcher (Scheduled Task / Startup)
# Acer Snow server is NOT required for local health on :8790

$ErrorActionPreference = "Stop"
$AgentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $AgentDir

$LogDir = Join-Path $AgentDir "logs"
if (-not (Test-Path -Path $LogDir)) {
  New-Item -ItemType Directory -Path $LogDir | Out-Null
}
$stamp = Get-Date -Format "yyyyMMdd"
$LogFile = Join-Path $LogDir "agent-$stamp.log"
$ErrFile = Join-Path $LogDir "agent-$stamp.err.log"

function Write-Log([string]$msg) {
  $line = "{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $msg
  Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

# Load .env
$EnvFile = Join-Path $AgentDir ".env"
if (Test-Path -Path $EnvFile) {
  Get-Content -Path $EnvFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $i = $line.IndexOf("=")
    if ($i -lt 1) { return }
    $k = $line.Substring(0, $i).Trim()
    $v = $line.Substring($i + 1).Trim().Trim('"').Trim("'")
    [Environment]::SetEnvironmentVariable($k, $v, "Process")
  }
}

if (-not $env:SNOW_PC_AGENT_TOKEN) {
  Write-Log "FATAL: SNOW_PC_AGENT_TOKEN missing in .env"
  exit 2
}

$port = "8790"
if ($env:SNOW_PC_AGENT_PORT) { $port = $env:SNOW_PC_AGENT_PORT }

$bind = "0.0.0.0"
if ($env:SNOW_PC_AGENT_HOST) { $bind = $env:SNOW_PC_AGENT_HOST }

$py = Join-Path $AgentDir ".venv\Scripts\python.exe"
if (-not (Test-Path -Path $py)) {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { $py = $cmd.Source }
}
if (-not $py -or -not (Test-Path -Path $py)) {
  Write-Log "FATAL: python not found"
  exit 3
}

# Free stale listener if any
try {
  Get-NetTCPConnection -LocalPort ([int]$port) -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object {
      if ($_ -and $_ -gt 0) {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        Write-Log "Killed old PID $_ on port $port"
      }
    }
}
catch {}

Write-Log "Starting: $py -m uvicorn main:app --host $bind --port $port"

# Start-Process keeps native stdio clean (PowerShell *>> often breaks uvicorn)
$args = @(
  "-m", "uvicorn", "main:app",
  "--host", $bind,
  "--port", $port,
  "--log-level", "info"
)

$proc = Start-Process `
  -FilePath $py `
  -ArgumentList $args `
  -WorkingDirectory $AgentDir `
  -PassThru `
  -WindowStyle Hidden `
  -RedirectStandardOutput $LogFile `
  -RedirectStandardError $ErrFile

if (-not $proc) {
  Write-Log "FATAL: Start-Process returned null"
  exit 4
}

Write-Log "PID=$($proc.Id) started; waiting (service mode)"

# Stay alive while uvicorn runs (task stays "Running")
Wait-Process -Id $proc.Id
$code = $proc.ExitCode
Add-Content -Path $LogFile -Value ("{0:yyyy-MM-dd HH:mm:ss} exited code={1}" -f (Get-Date), $code) -Encoding UTF8
exit $(if ($null -eq $code) { 0 } else { $code })
