# Restore an older supervisor only when its version is behind the golden copy.
# Do not inspect local timeout values: isolated probes intentionally use a
# shorter timeout than the production listener.
$launcherScript = Join-Path $env:LOCALAPPDATA 'Antigravity\launcher\Antigravity-ProxySupervisor.ps1'
$fixedBackup = Join-Path $env:LOCALAPPDATA 'Antigravity\private-proxy\Antigravity-ProxySupervisor.fixed.ps1'
$manifestPath = Join-Path $env:LOCALAPPDATA 'Antigravity\launcher\manifest.json'
$logPath = Join-Path $env:LOCALAPPDATA 'Antigravity\private-proxy\watchdog.log'

function Write-WatchdogLog([string]$message) {
    try {
        New-Item -ItemType Directory -Path (Split-Path -Parent $logPath) -Force | Out-Null
        Add-Content -LiteralPath $logPath -Value ("{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message)
    } catch { }
}

function Get-SupervisorVersion([string]$path) {
    try {
        if (-not (Test-Path -LiteralPath $path)) { return $null }
        $content = Get-Content -LiteralPath $path -Raw
        $match = [regex]::Match($content, '(?m)^\s*#\s*Version:\s*([0-9]+(?:\.[0-9]+){1,3})\s*$')
        if (-not $match.Success) { return $null }
        return [version]$match.Groups[1].Value
    } catch { return $null }
}

if (-not (Test-Path -LiteralPath $fixedBackup)) {
    Write-WatchdogLog 'golden supervisor copy missing; no action'
    exit 0
}

$fixedVersion = Get-SupervisorVersion -path $fixedBackup
if ($null -eq $fixedVersion) {
    Write-WatchdogLog 'golden supervisor version unreadable; no action'
    exit 0
}

$currentVersion = Get-SupervisorVersion -path $launcherScript
$needsRestore = ($null -eq $currentVersion -or $currentVersion -lt $fixedVersion)
if (-not $needsRestore) {
    Write-WatchdogLog ("launcher script version={0}; golden={1}; no action needed" -f $currentVersion, $fixedVersion)
    exit 0
}

Write-WatchdogLog ("older or unreadable launcher script detected current={0}; restoring golden={1}" -f $currentVersion, $fixedVersion)
try {
    New-Item -ItemType Directory -Path (Split-Path -Parent $launcherScript) -Force | Out-Null
    Copy-Item -LiteralPath $fixedBackup -Destination $launcherScript -Force
    $hash = (Get-FileHash -LiteralPath $launcherScript -Algorithm SHA256).Hash
    $size = (Get-Item -LiteralPath $launcherScript).Length
    if (Test-Path -LiteralPath $manifestPath) {
        $json = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        $entry = @($json | Where-Object { $_.file -eq 'Antigravity-ProxySupervisor.ps1' }) | Select-Object -First 1
        if ($null -ne $entry) {
            $entry.sha256 = $hash
            $entry.size = $size
            $json | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
        }
    }
    Write-WatchdogLog ("restored fixed script sha256={0} size={1}" -f $hash, $size)
} catch {
    Write-WatchdogLog ("restore failed: {0}" -f $_.Exception.Message)
}
