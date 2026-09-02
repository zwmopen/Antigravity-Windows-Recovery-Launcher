[CmdletBinding()]
param(
    [ValidateSet('zh', 'en')]
    [string]$Mode = 'zh'
)

$ErrorActionPreference = 'Stop'

$runtimeRoot = Join-Path $env:LOCALAPPDATA 'Antigravity'
$disabledMarker = Join-Path $runtimeRoot 'localization-extension-disabled.flag'
$pendingMarker = Join-Path $runtimeRoot 'localization-extension-pending.flag'
$launcherCandidates = @(
    (Join-Path $PSScriptRoot 'Antigravity-Recovery-Launcher.exe'),
    (Join-Path $PSScriptRoot '..\releases\current\Antigravity-Recovery-Launcher.exe'),
    (Join-Path $runtimeRoot 'launcher\Antigravity-Recovery-Launcher.exe')
)
$launcher = $launcherCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ([string]::IsNullOrWhiteSpace([string]$launcher)) {
    throw 'recovery_launcher_missing'
}

New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
Remove-Item -LiteralPath $pendingMarker -Force -ErrorAction SilentlyContinue
if ($Mode -eq 'zh') {
    Remove-Item -LiteralPath $disabledMarker -Force -ErrorAction SilentlyContinue
} else {
    Set-Content -LiteralPath $disabledMarker -Value 'English mode enabled by user.' -Encoding ASCII
}

Start-Process -FilePath $launcher -WorkingDirectory (Split-Path -Parent $launcher)
