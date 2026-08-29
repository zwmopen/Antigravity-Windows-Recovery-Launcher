[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $root 'src'
$release = Join-Path $root 'releases\current'
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'

New-Item -ItemType Directory -Path $release -Force | Out-Null
$launcherOutput = Join-Path $release 'Antigravity-Recovery-Launcher.exe'
$watcherOutput = Join-Path $release 'Antigravity-AccountWatcher.exe'
$launcherSource = Join-Path $source 'Antigravity-Recovery-Launcher.cs'
$watcherSource = Join-Path $source 'Antigravity-AccountWatcher.cs'
& $csc /nologo /target:winexe /optimize+ /reference:System.Drawing.dll /reference:System.Windows.Forms.dll ("/out:" + $launcherOutput) $launcherSource
if ($LASTEXITCODE -ne 0) { throw 'launcher_build_failed' }
& $csc /nologo /target:winexe /optimize+ /reference:System.Management.dll ("/out:" + $watcherOutput) $watcherSource
if ($LASTEXITCODE -ne 0) { throw 'watcher_build_failed' }
Copy-Item -LiteralPath (Join-Path $source 'Antigravity-ProxySupervisor.ps1') -Destination (Join-Path $release 'Antigravity-ProxySupervisor.ps1') -Force

Get-ChildItem -LiteralPath $release -File | ForEach-Object {
    [pscustomobject]@{ file = $_.Name; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash; size = $_.Length }
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $release 'manifest.json') -Encoding UTF8

Write-Output $release
