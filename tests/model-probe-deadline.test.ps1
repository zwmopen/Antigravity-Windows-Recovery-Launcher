$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1'
$ast = [Management.Automation.Language.Parser]::ParseFile($source,[ref]$null,[ref]$null)
$fn = $ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Invoke-BoundedModelProcess'},$true)
Invoke-Expression $fn.Extent.Text
function Write-SafeLog { param($Event,$Values) }
$testRoot = Join-Path $env:TEMP ('agy-deadline-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$worker = Join-Path $testRoot 'worker.ps1'
$diag = Join-Path $testRoot 'probe.log'
$exe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$clock = [Diagnostics.Stopwatch]::StartNew()
[IO.File]::WriteAllText($worker, "Set-Content -LiteralPath '$diag' -Value 'UNSUPPORTED_LOCATION'; Start-Sleep -Seconds 20")
$result = Invoke-BoundedModelProcess $exe ('-NoProfile -File "' + $worker + '"') $diag 10
if ($result.AbortReason -ne 'model_location' -or $clock.Elapsed.TotalSeconds -gt 8) { throw 'location_did_not_abort_early' }
# A new log path ensures no stale location from the previous request can abort this one.
$diag = Join-Path $testRoot 'timeout.log'
[IO.File]::WriteAllText($worker, 'Start-Sleep -Seconds 20')
$clock.Restart()
$result = Invoke-BoundedModelProcess $exe ('-NoProfile -File "' + $worker + '"') $diag 1
if ($result.AbortReason -ne 'model_timeout' -or $clock.Elapsed.TotalSeconds -gt 8) { throw 'external_deadline_failed' }
[IO.File]::WriteAllText($worker, "Write-Output '{`"status`":`"SUCCESS`",`"response`":`"OK`"}'")
$result = Invoke-BoundedModelProcess $exe ('-NoProfile -File "' + $worker + '"') $diag 5
if ($result.AbortReason -or $result.ExitCode -ne 0 -or $result.Output -notmatch 'SUCCESS') { throw 'success_path_failed' }
Write-Output 'PASS: actual child processes stop early on location errors, obey external deadline, and preserve success output'
