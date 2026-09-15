$ErrorActionPreference = 'Stop'
$source = Get-Content (Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1') -Raw
if ($source.Contains('$isFastAccountChange =')) { throw 'AccountChange must not fabricate connectivity results' }
if ($source.Contains('$skipModelProbe =')) { throw 'AccountChange must not bypass real generation gate' }
if ($source -notmatch '(?m)Test-RealModelGeneration') { throw 'real gate missing' }
Write-Output 'account_change_real_gate_pass'
