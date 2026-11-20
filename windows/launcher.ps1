# Local SAIN launcher. Never writes team secrets; guest tokens stay in the browser process only.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
function Python {
  $options = @(
    @{Exe='py'; Args=@('-3.11')}, @{Exe='py'; Args=@('-3.12')},
    @{Exe='py'; Args=@('-3.13')}, @{Exe='py'; Args=@('-3.14')},
    @{Exe='py'; Args=@('-3')}, @{Exe='python'; Args=@()}
  )
  foreach ($option in $options) {
    try {
      $args1=@($option.Args)
      $output=& $option.Exe @args1 -c 'import sys;print(int(sys.version_info >= (3,11)))' 2>$null
      if ($LASTEXITCODE -eq 0 -and "$output".Trim() -eq '1') { return $option }
    } catch { }
  }
  throw 'Python 3.11+ не найден. Установите с https://www.python.org/downloads/windows/ и повторите запуск.'
}
function Open-Port([int]$port) {
  $socket=New-Object System.Net.Sockets.TcpClient
  try { $socket.Connect('127.0.0.1',$port); return $false }
  catch { return $true }
  finally { $socket.Dispose() }
}
Write-Host 'SAIN SMART ROOM · 4SAIN · WINDOWS RELEASE CANDIDATE' -ForegroundColor Cyan
Write-Host '1 = REHEARSAL / автономный синтетический номер, FakeLLM, без API организаторов'
Write-Host '2 = STAND / официальный стенд (только временный ГОСТЕВОЙ токен)'
$choice=Read-Host 'Выберите режим (1 / 2)'
if ($choice -notin @('1','2')) { throw 'Введите 1 или 2.' }
$py=Python
if (-not (Test-Path -LiteralPath (Join-Path $root 'frontend\dist\index.html'))) { throw 'Не найден frontend\dist\index.html.' }
if (-not (Open-Port 4173)) { throw 'Порт 4173 занят. Остановите предыдущий сервер через STOP.cmd.' }
$runDir=Join-Path $root '.runtime'
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
$mode='stand'
$pythonExe=$py.Exe
$pythonArgs=@($py.Args)
$rehearsal=$null
if ($choice -eq '1') {
  $mode='rehearsal'
  if (-not (Open-Port 8765)) { throw 'Порт 8765 занят. Запустите STOP.cmd.' }
  $venv=Join-Path $root '.venv'
  $venvPy=Join-Path $venv 'Scripts\python.exe'
  if (-not (Test-Path -LiteralPath $venvPy)) {
    Write-Host 'Создаю локальное окружение Python...'
    & $pythonExe @pythonArgs -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось создать .venv.' }
  }
  & $venvPy -c 'import fastapi,httpx,uvicorn,jsonschema,pytest' 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host 'Устанавливаю зависимости (для первого запуска нужен интернет)...'
    & $venvPy -m pip install --disable-pip-version-check -r (Join-Path $root 'requirements-dev.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить Python-зависимости.' }
  }
  $pythonExe=$venvPy
  $pythonArgs=@()
  $rehearsal=Start-Process -FilePath $venvPy -ArgumentList @('-m','scripts.rehearse_client') -WorkingDirectory $root -PassThru -RedirectStandardOutput (Join-Path $runDir 'rehearsal.out') -RedirectStandardError (Join-Path $runDir 'rehearsal.err')
  $ready=$false
  for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 250
    if (-not (Open-Port 8765)) { $ready=$true; break }
    if ($rehearsal.HasExited) { break }
  }
  if (-not $ready) { throw 'Сервер репетиции не запустился. См. .runtime\rehearsal.err.' }
}
$server=Join-Path $root 'frontend\serve.py'
$serverArgs=@($pythonArgs) + @('"' + $server + '"','--mode',$mode,'--port','4173')
$proxy=Start-Process -FilePath $pythonExe -ArgumentList $serverArgs -WorkingDirectory $root -PassThru -RedirectStandardOutput (Join-Path $runDir 'client.out') -RedirectStandardError (Join-Path $runDir 'client.err')
@{ mode=$mode; proxy_pid=$proxy.Id; rehearsal_pid=$(if($rehearsal){$rehearsal.Id}else{$null}) } |
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runDir 'owned-pids.json') -Encoding UTF8
Start-Sleep -Seconds 1
if ($proxy.HasExited) { throw 'Клиентский сервер не запустился. См. .runtime\client.err.' }
Write-Host ('SAIN работает: http://127.0.0.1:4173 (' + $mode + ')') -ForegroundColor Green
if ($mode -eq 'rehearsal') {
  Write-Host 'Синтетический токен: откройте CMD в этой папке и запустите:'
  Write-Host '.venv\Scripts\python.exe -m scripts.client_access dev --stay stay_test'
} else {
  Write-Host 'Вводите только разрешённый временный клиентский токен. Командный ключ в браузер не вводить.'
}
Start-Process 'http://127.0.0.1:4173'
Write-Host 'Для завершения используйте STOP.cmd.'
