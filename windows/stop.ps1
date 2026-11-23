# Stop only PIDs recorded by this particular SAIN folder.
$ErrorActionPreference='Continue'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$record=Join-Path $root '.runtime\owned-pids.json'
if (-not (Test-Path -LiteralPath $record)) { Write-Host 'Запущенные процессы SAIN не обнаружены.'; exit 0 }
$data=Get-Content -Raw -LiteralPath $record | ConvertFrom-Json
foreach ($processId in @($data.proxy_pid,$data.rehearsal_pid)) {
  if (-not $processId) { continue }
  $p=Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
  if (-not $p) { continue }
  $command=[string]$p.CommandLine
  $exe=[string]$p.ExecutablePath
  $owned=$command.Contains((Join-Path $root 'frontend\serve.py')) -or
    (($command.Contains('scripts.rehearse_client') -or $command.Contains('scripts.live_client')) -and $exe.StartsWith((Join-Path $root '.venv'),[StringComparison]::OrdinalIgnoreCase))
  if ($owned) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    Write-Host "Остановлен процесс SAIN $processId"
  } else {
    Write-Warning "PID $processId не принадлежит этому экземпляру SAIN, остановка пропущена."
  }
}
Remove-Item -LiteralPath $record -Force -ErrorAction SilentlyContinue
