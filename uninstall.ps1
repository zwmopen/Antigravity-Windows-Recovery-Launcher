[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'Antigravity\launcher')
)

$ErrorActionPreference = 'Stop'
$installRoot = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
$desktop = [Environment]::GetFolderPath('Desktop')
$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$ownedExecutables = @(
    (Join-Path $installRoot 'Antigravity-Recovery-Launcher.exe'),
    (Join-Path $installRoot 'Antigravity-AccountWatcher.exe'),
    (Join-Path $installRoot 'Antigravity-CdpLocalizationLoader.exe')
)

function Test-ShortcutOwnedByInstall {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    if (-not (Test-Path -LiteralPath $LiteralPath)) { return $false }
    try {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($LiteralPath)
        $target = [System.IO.Path]::GetFullPath([string]$shortcut.TargetPath)
        return $target.StartsWith($installRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)
    } catch {
        return $false
    }
}

$ownedProcesses = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $path = [string]$_.ExecutablePath
    -not [string]::IsNullOrWhiteSpace($path) -and
    ($ownedExecutables | Where-Object { [string]::Equals($_, $path, [System.StringComparison]::OrdinalIgnoreCase) }).Count -gt 0
})
foreach ($processInfo in $ownedProcesses) {
    Stop-Process -Id ([int]$processInfo.ProcessId) -Force -ErrorAction SilentlyContinue
}

# Stop the dedicated Mihomo only when its recorded process command line points
# to this product's private-proxy configuration. Runtime data itself is kept.
$runtimeRoot = Join-Path $env:LOCALAPPDATA 'Antigravity\private-proxy'
$pidFile = Join-Path $runtimeRoot 'mihomo.pid'
if (Test-Path -LiteralPath $pidFile) {
    $proxyPidText = (Get-Content -LiteralPath $pidFile -Raw -ErrorAction SilentlyContinue).Trim()
    $proxyPid = 0
    if ([int]::TryParse($proxyPidText, [ref]$proxyPid)) {
        $proxyProcess = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $proxyPid) -ErrorAction SilentlyContinue
        if ($null -ne $proxyProcess -and [string]$proxyProcess.CommandLine -like ('*' + $runtimeRoot + '*')) {
            Stop-Process -Id $proxyPid -Force -ErrorAction SilentlyContinue
        }
    }
}

$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
if (Test-Path -LiteralPath $runKey) {
    $runValue = (Get-ItemProperty -LiteralPath $runKey -Name 'AntigravityAccountWatcher' -ErrorAction SilentlyContinue).AntigravityAccountWatcher
    if ([string]$runValue -like ('*' + (Join-Path $installRoot 'Antigravity-AccountWatcher.exe') + '*')) {
        Remove-ItemProperty -LiteralPath $runKey -Name 'AntigravityAccountWatcher' -ErrorAction SilentlyContinue
    }
}

foreach ($shortcutPath in @(
    (Join-Path $desktop 'Antigravity 启动器.lnk'),
    (Join-Path $startMenu 'Antigravity 启动器.lnk'),
    (Join-Path $startMenu 'Antigravity 中文版.lnk'),
    (Join-Path $startMenu 'Antigravity 英文恢复.lnk')
)) {
    if (Test-ShortcutOwnedByInstall -LiteralPath $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force -ErrorAction SilentlyContinue
    }
}

$officialShortcut = Join-Path $startMenu 'Antigravity 原版.lnk'
if (Test-Path -LiteralPath $officialShortcut) {
    try {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($officialShortcut)
        if ([string]$shortcut.Description -eq 'Antigravity official app') {
            Remove-Item -LiteralPath $officialShortcut -Force -ErrorAction SilentlyContinue
        }
    } catch {}
}

Write-Output 'Antigravity launcher integration removed. User data was preserved.'
