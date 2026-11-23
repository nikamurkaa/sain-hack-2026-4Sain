$root=Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host 'SAIN SMART ROOM: ПРОВЕРКА ОКРУЖЕНИЯ' -ForegroundColor Cyan
Write-Host ('Папка: ' + $root)
foreach ($f in @('frontend\dist\index.html','frontend\serve.py','scripts\rehearse_client.py','requirements-dev.txt','BUILD_INFO.txt')) {
  Write-Host ($f + ': ' + (Test-Path -LiteralPath (Join-Path $root $f)))
}
foreach ($name in @('py','python')) {
  try { $cmd=Get-Command $name -ErrorAction Stop; Write-Host ($name + ': ' + $cmd.Source); if($name -eq 'py'){ & py -0p }else{ & python --version } }
  catch { Write-Host ($name + ': не установлен') }
}
Write-Host 'Если Python отсутствует: https://www.python.org/downloads/windows/ (Python 3.11+).'
