[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$app = Join-Path $root 'releases\current'
$installRoot = Join-Path $env:LOCALAPPDATA 'Antigravity\launcher'
$sourceLauncher = Join-Path $app 'Antigravity-Recovery-Launcher.exe'
$sourceWatcher = Join-Path $app 'Antigravity-AccountWatcher.exe'
$launcher = Join-Path $installRoot 'Antigravity-Recovery-Launcher.exe'
$watcher = Join-Path $installRoot 'Antigravity-AccountWatcher.exe'
$sourceLocalizationLoader = Join-Path $app 'Antigravity-CdpLocalizationLoader.exe'
$installedLocalizationLoader = Join-Path $installRoot 'Antigravity-CdpLocalizationLoader.exe'
$sourceSupervisor = Join-Path $app 'Antigravity-ProxySupervisor.ps1'
$installedSupervisor = Join-Path $installRoot 'Antigravity-ProxySupervisor.ps1'
$sourceLocalizationHelper = Join-Path $app 'Set-AntigravityLocalization.ps1'
$installedLocalizationHelper = Join-Path $installRoot 'Set-AntigravityLocalization.ps1'
$sourceEnableChinese = Join-Path $app 'Enable-Antigravity-Chinese.cmd'
$installedEnableChinese = Join-Path $installRoot 'Enable-Antigravity-Chinese.cmd'
$sourceRestoreEnglish = Join-Path $app 'Restore-Antigravity-English.cmd'
$installedRestoreEnglish = Join-Path $installRoot 'Restore-Antigravity-English.cmd'
$sourceExtension = Join-Path $app 'localization-extension'
$installedExtension = Join-Path $installRoot 'localization-extension'
$sourceManifest = Join-Path $app 'manifest.json'
$installedManifest = Join-Path $installRoot 'manifest.json'
$agyDirectory = Join-Path $installRoot 'tools\agy'
$agyPath = Join-Path $agyDirectory 'agy.exe'
$agyManifestUri = 'https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/windows_amd64.json'
$desktop = [Environment]::GetFolderPath('Desktop')
$officialApp = Join-Path $env:LOCALAPPDATA 'Programs\antigravity\Antigravity.exe'
$shortcutTargets = @(
    @{ Path = (Join-Path $desktop 'Antigravity 启动器.lnk'); Target = $launcher; Description = 'Antigravity recovery launcher'; Key = 'desktop-launcher' },
    @{ Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 启动器.lnk'); Target = $launcher; Description = 'Antigravity recovery launcher'; Key = 'start-menu-launcher' },
    @{ Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 中文版.lnk'); Target = $installedEnableChinese; Description = 'Enable Antigravity Simplified Chinese UI'; Key = 'start-menu-chinese' },
    @{ Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 英文恢复.lnk'); Target = $installedRestoreEnglish; Description = 'Restore the original English UI'; Key = 'start-menu-english' },
    @{ Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 原版.lnk'); Target = $officialApp; Description = 'Antigravity official app'; Key = 'start-menu-official' }
)
$runtime = Join-Path $env:LOCALAPPDATA 'Antigravity'
$backupRoot = Join-Path $runtime 'shortcut-backups'
$localizationPendingMarker = Join-Path $runtime 'localization-extension-pending.flag'

if (-not (Test-Path -LiteralPath $sourceLauncher) -or -not (Test-Path -LiteralPath $sourceWatcher) -or -not (Test-Path -LiteralPath $sourceLocalizationLoader) -or -not (Test-Path -LiteralPath $sourceSupervisor) -or -not (Test-Path -LiteralPath $sourceLocalizationHelper) -or -not (Test-Path -LiteralPath $sourceEnableChinese) -or -not (Test-Path -LiteralPath $sourceRestoreEnglish) -or -not (Test-Path -LiteralPath (Join-Path $sourceExtension 'manifest.json'))) { throw 'build_first' }

# Stop only old copies owned by this project before replacing the installed
# runtime. This keeps the desktop entry independent of the source checkout.
$watcherPaths = @($sourceWatcher, $watcher)
foreach ($watcherPath in ($watcherPaths | Select-Object -Unique)) {
    $runningWatchers = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -ieq 'Antigravity-AccountWatcher.exe' -and
        [string]$_.ExecutablePath -ieq $watcherPath
    })
    foreach ($processInfo in $runningWatchers) {
        Stop-Process -Id ([int]$processInfo.ProcessId) -Force -ErrorAction SilentlyContinue
    }
}
# A failed launch can leave the GUI launcher open while showing its error
# dialog. Stop only this project's installed/source launcher before replacing
# the binary, otherwise upgrades silently leave the desktop on an old build.
$launcherPaths = @($sourceLauncher, $launcher)
foreach ($launcherPath in ($launcherPaths | Select-Object -Unique)) {
    $runningLaunchers = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -ieq 'Antigravity-Recovery-Launcher.exe' -and
        [string]$_.ExecutablePath -ieq $launcherPath
    })
    foreach ($processInfo in $runningLaunchers) {
        Stop-Process -Id ([int]$processInfo.ProcessId) -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Milliseconds 300
New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
Copy-Item -LiteralPath $sourceLauncher -Destination $launcher -Force
Copy-Item -LiteralPath $sourceWatcher -Destination $watcher -Force
Copy-Item -LiteralPath $sourceLocalizationLoader -Destination $installedLocalizationLoader -Force
Copy-Item -LiteralPath $sourceSupervisor -Destination $installedSupervisor -Force
Copy-Item -LiteralPath $sourceLocalizationHelper -Destination $installedLocalizationHelper -Force
Copy-Item -LiteralPath $sourceEnableChinese -Destination $installedEnableChinese -Force
Copy-Item -LiteralPath $sourceRestoreEnglish -Destination $installedRestoreEnglish -Force
New-Item -ItemType Directory -Path $installedExtension -Force | Out-Null
Copy-Item -Path (Join-Path $sourceExtension '*') -Destination $installedExtension -Recurse -Force

# The official CLI does not currently declare a redistribution license. Do
# not bundle it in this project. Download the current Windows binary from the
# official updater manifest and require its published SHA-512 before use.
New-Item -ItemType Directory -Path $agyDirectory -Force | Out-Null
$agyManifest = Invoke-RestMethod -Uri $agyManifestUri -TimeoutSec 30
if ([string]::IsNullOrWhiteSpace([string]$agyManifest.url) -or [string]::IsNullOrWhiteSpace([string]$agyManifest.sha512)) {
    throw 'agy_manifest_invalid'
}
$agyStaging = Join-Path $agyDirectory 'agy.download'
$agyExpectedHash = ([string]$agyManifest.sha512).ToLowerInvariant()
$agyReady = $false
if (Test-Path -LiteralPath $agyPath) {
    $agyReady = ((Get-FileHash -LiteralPath $agyPath -Algorithm SHA512).Hash.ToLowerInvariant() -eq $agyExpectedHash)
}
if (-not $agyReady) {
    Invoke-WebRequest -Uri ([string]$agyManifest.url) -OutFile $agyStaging -TimeoutSec 180
    $agyActualHash = (Get-FileHash -LiteralPath $agyStaging -Algorithm SHA512).Hash.ToLowerInvariant()
    if ($agyActualHash -ne $agyExpectedHash) {
        Remove-Item -LiteralPath $agyStaging -Force -ErrorAction SilentlyContinue
        throw 'agy_sha512_mismatch'
    }
    Move-Item -LiteralPath $agyStaging -Destination $agyPath -Force
}
# Do not interrupt an already open Antigravity window just because the files
# were installed. The first explicit language/recovery launch applies the new
# extension; the watcher ignores this one pending window in the meantime.
Set-Content -LiteralPath $localizationPendingMarker -Value 'Localization installed; waiting for an explicit launch.' -Encoding ASCII
if (Test-Path -LiteralPath $sourceManifest) {
    Copy-Item -LiteralPath $sourceManifest -Destination $installedManifest -Force
}

$shell = New-Object -ComObject WScript.Shell
foreach ($shortcutTarget in $shortcutTargets) {
    $shortcutPath = [string]$shortcutTarget.Path
    if (Test-Path -LiteralPath $shortcutPath) {
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        Copy-Item -LiteralPath $shortcutPath -Destination (Join-Path $backupRoot ('Antigravity-' + [string]$shortcutTarget.Key + '-before-install-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.lnk'))
    } else {
        New-Item -ItemType Directory -Path (Split-Path -Parent $shortcutPath) -Force | Out-Null
    }

    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = [string]$shortcutTarget.Target
    $shortcut.Arguments = ''
    $shortcut.WorkingDirectory = $installRoot
    $shortcut.IconLocation = $officialApp + ',0'
    $shortcut.Description = [string]$shortcutTarget.Description
    $shortcut.Save()
}

# Remove the old ambiguous entry only after preserving it. The two explicit
# entries above are the supported desktop/start-menu contract.
foreach ($legacyShortcut in @(
    (Join-Path $desktop 'Antigravity.lnk'),
    (Join-Path $desktop 'Antigravity 中文版.lnk'),
    (Join-Path $desktop 'Antigravity 英文恢复.lnk'),
    (Join-Path $desktop 'Antigravity 原版.lnk'),
    (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity.lnk')
)) {
    if (Test-Path -LiteralPath $legacyShortcut) {
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        $legacyName = [System.IO.Path]::GetFileNameWithoutExtension($legacyShortcut) -replace '[^A-Za-z0-9\u4e00-\u9fff-]', '_'
        Copy-Item -LiteralPath $legacyShortcut -Destination (Join-Path $backupRoot ($legacyName + '-before-single-entry-' + (Get-Date -Format 'yyyyMMdd-HHmmssfff') + '.lnk'))
        Remove-Item -LiteralPath $legacyShortcut -Force
    }
}

Set-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'AntigravityAccountWatcher' -Value ('"' + $watcher + '"')

$watcherProcesses = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -ieq 'Antigravity-AccountWatcher.exe' -and
    [string]$_.ExecutablePath -ieq $watcher
})
foreach ($processInfo in $watcherProcesses) {
    Stop-Process -Id ([int]$processInfo.ProcessId) -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 500
Start-Process -FilePath $watcher -WorkingDirectory $installRoot -WindowStyle Hidden

Write-Output $launcher
