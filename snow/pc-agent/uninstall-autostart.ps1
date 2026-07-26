# Remove Snow PC Agent auto-start (task + Startup + process on 8790)
param([string]$TaskName = "SnowPcAgent")

$ErrorActionPreference = "Continue"
$AgentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Scheduled Task
try {
  $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if ($null -ne $t) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[OK] Removed task $TaskName"
  }
  else {
    Write-Host "[*] Task $TaskName not found"
  }
}
catch {
  Write-Host "[!] Task remove: $($_.Exception.Message)"
}

# Startup folder
$startupVbs = Join-Path ([Environment]::GetFolderPath("Startup")) "SnowPcAgent.vbs"
if (Test-Path -Path $startupVbs) {
  Remove-Item -Path $startupVbs -Force
  Write-Host "[OK] Removed $startupVbs"
}

# Kill port 8790
try {
  $pids = Get-NetTCPConnection -LocalPort 8790 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($procId in $pids) {
    if ($procId -and $procId -gt 0) {
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      Write-Host "[OK] Stopped PID $procId on port 8790"
    }
  }
}
catch {}

# Also stop any leftover python uvicorn for this agent (best effort)
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match '8790' } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Stopped python PID $($_.ProcessId)"
  }

Write-Host "Done. Agent will not auto-start until install-autostart.ps1 again."
