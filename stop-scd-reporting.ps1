# stop-scd-reporting.ps1 — gracefully stop the running SCD Effort Reporting server
#
# Usage:
#   .\stop-scd-reporting.ps1 [-Tail]
#
# Options:
#   -Tail   Print the last 20 lines of the server log before stopping

param([switch]$Tail)

$ScriptDir       = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile         = Join-Path $ScriptDir '.scd-reporting.pid'
$TailwindPidFile = Join-Path $ScriptDir '.scd-tailwind.pid'
$LogFile         = Join-Path $ScriptDir 'logs\scd-reporting.log'

function Write-Info($t)  { Write-Host "==> $t" -ForegroundColor Cyan }
function Write-Ok($t)    { Write-Host "✓  $t"  -ForegroundColor Green }
function Write-Warn($t)  { Write-Host "!  $t"  -ForegroundColor Yellow }

if ($Tail -and (Test-Path $LogFile)) {
    Write-Host ""
    Write-Info "Last 20 lines of server log:"
    Write-Host ""
    Get-Content $LogFile -Tail 20
    Write-Host ""
}

# ── Stop Django server ────────────────────────────────────────────────────────
if (-not (Test-Path $PidFile)) {
    Write-Warn "No PID file found — server may not be running."
} else {
    $pid = [int](Get-Content $PidFile)
    try {
        $proc = Get-Process -Id $pid -ErrorAction Stop
        Write-Info "Stopping server (PID $pid)..."
        Stop-Process -Id $pid -Force
        $proc.WaitForExit(5000) | Out-Null
        Write-Ok "Server stopped"
    } catch {
        Write-Warn "Process $pid is no longer running (stale PID file removed)"
    }
    Remove-Item $PidFile -Force
}

# ── Stop Tailwind watcher (if running) ───────────────────────────────────────
if (Test-Path $TailwindPidFile) {
    $twPid = [int](Get-Content $TailwindPidFile)
    try {
        Get-Process -Id $twPid -ErrorAction Stop | Out-Null
        Write-Info "Stopping Tailwind watcher (PID $twPid)..."
        Stop-Process -Id $twPid -Force
        Write-Ok "Tailwind watcher stopped"
    } catch { }
    Remove-Item $TailwindPidFile -Force
}
