[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $root 'src'
$release = Join-Path $root 'releases\current'
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$extensionSource = Join-Path $source 'localization-extension'
$extensionRelease = Join-Path $release 'localization-extension'
$loaderSource = Join-Path $source 'Antigravity-CdpLocalizationLoader.cs'
$loaderOutput = Join-Path $release 'Antigravity-CdpLocalizationLoader.exe'

New-Item -ItemType Directory -Path $release -Force | Out-Null
$launcherOutput = Join-Path $release 'Antigravity-Recovery-Launcher.exe'
$watcherOutput = Join-Path $release 'Antigravity-AccountWatcher.exe'
$launcherSource = Join-Path $source 'Antigravity-Recovery-Launcher.cs'
$watcherSource = Join-Path $source 'Antigravity-AccountWatcher.cs'
# The installed watcher keeps its own EXE open. Stop only the exact project
# binary before rebuilding so upgrades do not fail with CS0016/file-in-use.
$runningWatchers = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -ieq 'Antigravity-AccountWatcher.exe' -and
    [string]$_.ExecutablePath -ieq $watcherOutput
})
foreach ($processInfo in $runningWatchers) {
    Stop-Process -Id ([int]$processInfo.ProcessId) -Force -ErrorAction SilentlyContinue
}
if ($runningWatchers.Count -gt 0) {
    Start-Sleep -Milliseconds 500
}
$iconSource = Join-Path $source 'Antigravity-Launcher.ico'
$iconRelease = Join-Path $release 'Antigravity-Launcher.ico'
if (Test-Path -LiteralPath $iconSource) {
    Copy-Item -LiteralPath $iconSource -Destination $iconRelease -Force
}
$iconArg = if (Test-Path -LiteralPath $iconSource) { "/win32icon:`"$iconSource`"" } else { "" }

& $csc /nologo /target:winexe /optimize+ $iconArg /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.dll ("/out:" + $launcherOutput) $launcherSource
if ($LASTEXITCODE -ne 0) { throw 'launcher_build_failed' }
& $csc /nologo /target:winexe /optimize+ /reference:System.Management.dll ("/out:" + $watcherOutput) $watcherSource
if ($LASTEXITCODE -ne 0) { throw 'watcher_build_failed' }
& $csc /nologo /target:winexe /optimize+ /reference:System.dll ("/out:" + $loaderOutput) $loaderSource
if ($LASTEXITCODE -ne 0) { throw 'localization_loader_build_failed' }
$trayOutput = Join-Path $release 'Antigravity-NodeTray.exe'
$traySource = Join-Path $source 'Antigravity-NodeTray.cs'
& $csc /nologo /target:winexe /optimize+ $iconArg /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.dll ("/out:" + $trayOutput) $traySource
if ($LASTEXITCODE -ne 0) { throw 'nodetray_build_failed' }
Copy-Item -LiteralPath (Join-Path $source 'Antigravity-ProxySupervisor.ps1') -Destination (Join-Path $release 'Antigravity-ProxySupervisor.ps1') -Force
foreach ($helper in @('Set-AntigravityLocalization.ps1', 'Enable-Antigravity-Chinese.cmd', 'Restore-Antigravity-English.cmd')) {
    Copy-Item -LiteralPath (Join-Path $source $helper) -Destination (Join-Path $release $helper) -Force
}
if (-not (Test-Path -LiteralPath (Join-Path $extensionSource 'manifest.json'))) { throw 'localization_extension_missing' }
New-Item -ItemType Directory -Path $extensionRelease -Force | Out-Null
Copy-Item -Path (Join-Path $extensionSource '*') -Destination $extensionRelease -Recurse -Force

Get-ChildItem -LiteralPath $release -File | ForEach-Object {
    [pscustomobject]@{ file = $_.Name; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash; size = $_.Length }
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $release 'manifest.json') -Encoding UTF8

Write-Output $release
