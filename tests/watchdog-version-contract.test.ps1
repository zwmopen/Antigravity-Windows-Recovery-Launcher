$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$watchdogSourcePath = Join-Path $root 'src\watchdog-restore-fix.ps1'
$supervisorSourcePath = Join-Path $root 'src\Antigravity-ProxySupervisor.ps1'
$watchdogSource = Get-Content -LiteralPath $watchdogSourcePath -Raw

if ($watchdogSource -match '\$ProbeTimeoutMs\s*=\s*3000') { throw 'watchdog_must_not_scan_local_probe_timeout' }
foreach ($required in @('Get-SupervisorVersion', '$currentVersion -lt $fixedVersion', 'no action needed')) {
    if (-not $watchdogSource.Contains($required)) { throw ('watchdog_contract_missing:' + $required) }
}

# Exercise the no-action path with the real supervisor source. It intentionally
# contains a 3000ms local probe override, which used to trigger a false restore.
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('agy-watchdog-contract-' + [guid]::NewGuid().ToString('N'))
$launcherRoot = Join-Path $tempRoot 'Antigravity\launcher'
$proxyRoot = Join-Path $tempRoot 'Antigravity\private-proxy'
$launcherPath = Join-Path $launcherRoot 'Antigravity-ProxySupervisor.ps1'
$fixedPath = Join-Path $proxyRoot 'Antigravity-ProxySupervisor.fixed.ps1'
$manifestPath = Join-Path $launcherRoot 'manifest.json'
$watchdogPath = Join-Path $proxyRoot 'watchdog-restore-fix.ps1'
$oldLocalAppData = $env:LOCALAPPDATA
try {
    New-Item -ItemType Directory -Path $launcherRoot,$proxyRoot -Force | Out-Null
    Copy-Item -LiteralPath $supervisorSourcePath -Destination $launcherPath -Force
    Copy-Item -LiteralPath $supervisorSourcePath -Destination $fixedPath -Force
    Copy-Item -LiteralPath $watchdogSourcePath -Destination $watchdogPath -Force
    $hash = (Get-FileHash -LiteralPath $launcherPath -Algorithm SHA256).Hash
    $size = (Get-Item -LiteralPath $launcherPath).Length
    @([pscustomobject]@{ file = 'Antigravity-ProxySupervisor.ps1'; sha256 = $hash; size = $size }) |
        ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    $env:LOCALAPPDATA = $tempRoot
    $beforeHash = (Get-FileHash -LiteralPath $launcherPath -Algorithm SHA256).Hash
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $watchdogPath
    if ($LASTEXITCODE -ne 0) { throw 'watchdog_no_action_process_failed' }
    $afterHash = (Get-FileHash -LiteralPath $launcherPath -Algorithm SHA256).Hash
    if ($beforeHash -ne $afterHash) { throw 'watchdog_false_positive_restore' }
    if (-not ((Get-Content -LiteralPath (Join-Path $proxyRoot 'watchdog.log') -Raw) -match 'no action needed')) {
        throw 'watchdog_no_action_not_logged'
    }
} finally {
    $env:LOCALAPPDATA = $oldLocalAppData
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}

Write-Output 'watchdog_version_contract_pass'
