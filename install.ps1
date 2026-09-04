[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'Antigravity\launcher'),
    [string]$SourceApp = '',
    [string]$DesktopShortcutName = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$app = if ([string]::IsNullOrWhiteSpace($SourceApp)) { Join-Path $root 'releases\current' } else { [System.IO.Path]::GetFullPath($SourceApp) }
$installRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$sourceLauncher = Join-Path $app 'Antigravity-Recovery-Launcher.exe'
$sourceWatcher = Join-Path $app 'Antigravity-AccountWatcher.exe'
$launcher = Join-Path $installRoot 'Antigravity-Recovery-Launcher.exe'
$watcher = Join-Path $installRoot 'Antigravity-AccountWatcher.exe'
$sourceTray = Join-Path $app 'Antigravity-NodeTray.exe'
$installedTray = Join-Path $installRoot 'Antigravity-NodeTray.exe'
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
$sourceIcon = Join-Path $app 'Antigravity-Launcher.ico'
$installedIcon = Join-Path $installRoot 'Antigravity-Launcher.ico'
$sourceManifest = Join-Path $app 'manifest.json'
$installedManifest = Join-Path $installRoot 'manifest.json'
$agyDirectory = Join-Path $installRoot 'tools\agy'
$agyPath = Join-Path $agyDirectory 'agy.exe'
$agyManifestUri = 'https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/windows_amd64.json'
$desktop = [Environment]::GetFolderPath('Desktop')
$officialApp = Join-Path $env:LOCALAPPDATA 'Programs\antigravity\Antigravity.exe'

function Get-Sha512Hex {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    $stream = [System.IO.File]::OpenRead($LiteralPath)
    try {
        $algorithm = [System.Security.Cryptography.SHA512]::Create()
        try {
            return ([System.BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
        } finally {
            $algorithm.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}

$actualDesktopShortcutName = if (-not [string]::IsNullOrWhiteSpace($DesktopShortcutName)) {
    $DesktopShortcutName
} else {
    'Antigravity 智能启动器.lnk'
}
if (-not $actualDesktopShortcutName.EndsWith('.lnk', [System.StringComparison]::OrdinalIgnoreCase)) {
    $actualDesktopShortcutName += '.lnk'
}

$shortcutTargets = @(
    @{ Path = (Join-Path $desktop $actualDesktopShortcutName); Target = $launcher; Arguments = ''; Description = 'Antigravity 智能启动器'; Key = 'desktop-launcher' },
    @{ Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 智能启动器.lnk'); Target = $launcher; Arguments = ''; Description = 'Antigravity 智能启动器'; Key = 'start-menu-launcher' },
    @{ Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 节点中控台.lnk'); Target = $launcher; Arguments = '--show-panel'; Description = 'Antigravity 节点中控台'; Key = 'start-menu-nodetray' },
    @{ Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 中文版.lnk'); Target = $installedEnableChinese; Arguments = ''; Description = 'Enable Antigravity Simplified Chinese UI'; Key = 'start-menu-chinese' },
    @{ Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 英文恢复.lnk'); Target = $installedRestoreEnglish; Arguments = ''; Description = 'Restore the original English UI'; Key = 'start-menu-english' },
    @{ Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 原版.lnk'); Target = $officialApp; Arguments = ''; Description = 'Antigravity official app'; Key = 'start-menu-official' }
)
$runtime = Join-Path $env:LOCALAPPDATA 'Antigravity'
$backupRoot = Join-Path $runtime 'shortcut-backups'
$localizationPendingMarker = Join-Path $runtime 'localization-extension-pending.flag'

$previousWatcherPath = ''
$previousRunValue = (Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'AntigravityAccountWatcher' -ErrorAction SilentlyContinue).AntigravityAccountWatcher
if (-not [string]::IsNullOrWhiteSpace([string]$previousRunValue)) {
    $previousWatcherPath = ([string]$previousRunValue).Trim().Trim('"')
}

if (-not (Test-Path -LiteralPath $sourceLauncher) -or -not (Test-Path -LiteralPath $sourceWatcher) -or -not (Test-Path -LiteralPath $sourceLocalizationLoader) -or -not (Test-Path -LiteralPath $sourceSupervisor) -or -not (Test-Path -LiteralPath $sourceLocalizationHelper) -or -not (Test-Path -LiteralPath $sourceEnableChinese) -or -not (Test-Path -LiteralPath $sourceRestoreEnglish) -or -not (Test-Path -LiteralPath (Join-Path $sourceExtension 'manifest.json'))) { throw 'build_first' }

# Stop only old copies owned by this project before replacing the installed
# runtime. This keeps the desktop entry independent of the source checkout.
$watcherPaths = @($sourceWatcher, $watcher, $previousWatcherPath)
foreach ($watcherPath in ($watcherPaths | Select-Object -Unique)) {
    if ([string]::IsNullOrWhiteSpace($watcherPath)) { continue }
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
$previousLauncherPath = ''
if (-not [string]::IsNullOrWhiteSpace($previousWatcherPath)) {
    $previousLauncherPath = Join-Path (Split-Path -Parent $previousWatcherPath) 'Antigravity-Recovery-Launcher.exe'
}
$launcherPaths = @($sourceLauncher, $launcher, $previousLauncherPath)
foreach ($launcherPath in ($launcherPaths | Select-Object -Unique)) {
    if ([string]::IsNullOrWhiteSpace($launcherPath)) { continue }
    $runningLaunchers = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -ieq 'Antigravity-Recovery-Launcher.exe' -and
        [string]$_.ExecutablePath -ieq $launcherPath
    })
    foreach ($processInfo in $runningLaunchers) {
        Stop-Process -Id ([int]$processInfo.ProcessId) -Force -ErrorAction SilentlyContinue
    }
}
$runningTrays = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -ieq 'Antigravity-NodeTray.exe'
})
foreach ($processInfo in $runningTrays) {
    Stop-Process -Id ([int]$processInfo.ProcessId) -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 300
New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
$sourceAppFull = [System.IO.Path]::GetFullPath($app).TrimEnd('\')
$installRootFull = [System.IO.Path]::GetFullPath($installRoot).TrimEnd('\')
if (-not [string]::Equals($sourceAppFull, $installRootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    Copy-Item -LiteralPath $sourceLauncher -Destination $launcher -Force
    Copy-Item -LiteralPath $sourceWatcher -Destination $watcher -Force
    Copy-Item -LiteralPath $sourceLocalizationLoader -Destination $installedLocalizationLoader -Force
    Copy-Item -LiteralPath $sourceSupervisor -Destination $installedSupervisor -Force
    Copy-Item -LiteralPath $sourceLocalizationHelper -Destination $installedLocalizationHelper -Force
    Copy-Item -LiteralPath $sourceEnableChinese -Destination $installedEnableChinese -Force
    Copy-Item -LiteralPath $sourceRestoreEnglish -Destination $installedRestoreEnglish -Force
    New-Item -ItemType Directory -Path $installedExtension -Force | Out-Null
    Copy-Item -Path (Join-Path $sourceExtension '*') -Destination $installedExtension -Recurse -Force
    if (Test-Path -LiteralPath $sourceTray) {
        Copy-Item -LiteralPath $sourceTray -Destination $installedTray -Force
    }
    if (Test-Path -LiteralPath $sourceIcon) {
        Copy-Item -LiteralPath $sourceIcon -Destination $installedIcon -Force
    }
    Remove-Item (Join-Path $installRoot 'Antigravity-Panel.py'), (Join-Path $installRoot 'Antigravity-Tray.py'), (Join-Path $installRoot 'Antigravity-SmartLauncher.py'), (Join-Path $installRoot 'Antigravity-TrayManager.py') -Force -ErrorAction SilentlyContinue
}

# The official CLI does not currently declare a redistribution license. Do
# not bundle it in this project. Download the current Windows binary from the
# official updater manifest and require its published SHA-512 before use.
New-Item -ItemType Directory -Path $agyDirectory -Force | Out-Null

$agyReady = $false
if (Test-Path -LiteralPath $agyPath) {
    $agyReady = $true
} else {
    $candidateAgys = @(
        (Join-Path $env:LOCALAPPDATA 'Antigravity\launcher\tools\agy\agy.exe'),
        (Join-Path $env:LOCALAPPDATA 'Antigravity\launcher-v0.9.1\tools\agy\agy.exe'),
        (Join-Path $app 'tools\agy\agy.exe')
    )
    foreach ($cand in $candidateAgys) {
        if ((Test-Path -LiteralPath $cand) -and (Get-Item -LiteralPath $cand).Length -gt 100000000) {
            Copy-Item -LiteralPath $cand -Destination $agyPath -Force
            $agyReady = $true
            break
        }
    }
}

if (-not $agyReady) {
    try {
        $agyManifest = Invoke-RestMethod -Uri $agyManifestUri -TimeoutSec 15
    } catch {
        $agyManifest = $null
    }
    if ($agyManifest -ne $null -and -not [string]::IsNullOrWhiteSpace([string]$agyManifest.url)) {
        $agyStaging = Join-Path $agyDirectory 'agy.download'
        $agyExpectedHash = ([string]$agyManifest.sha512).ToLowerInvariant()
        Invoke-WebRequest -Uri ([string]$agyManifest.url) -OutFile $agyStaging -TimeoutSec 180
        $agyActualHash = Get-Sha512Hex -LiteralPath $agyStaging
        if ($agyActualHash -eq $agyExpectedHash) {
            Move-Item -LiteralPath $agyStaging -Destination $agyPath -Force
            $agyReady = $true
        } else {
            Remove-Item -LiteralPath $agyStaging -Force -ErrorAction SilentlyContinue
            throw 'agy_sha512_mismatch'
        }
    }
}
# Do not interrupt an already open Antigravity window just because the files
# were installed. The first explicit language/recovery launch applies the new
# extension; the watcher ignores this one pending window in the meantime.
Set-Content -LiteralPath $localizationPendingMarker -Value 'Localization installed; waiting for an explicit launch.' -Encoding ASCII
if ((Test-Path -LiteralPath $sourceManifest) -and
    -not [string]::Equals($sourceManifest, $installedManifest, [System.StringComparison]::OrdinalIgnoreCase)) {
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
    $shortcut.Arguments = if ($shortcutTarget.ContainsKey('Arguments')) { [string]$shortcutTarget.Arguments } else { '' }
    $shortcut.WorkingDirectory = $installRoot
    $shortcut.IconLocation = if (Test-Path -LiteralPath $installedIcon) { $installedIcon + ',0' } else { $launcher + ',0' }
    $shortcut.Description = [string]$shortcutTarget.Description
    $shortcut.Save()
}

# Remove the old ambiguous entry only after preserving it.
foreach ($legacyShortcut in @(
    (Join-Path $desktop 'Antigravity.lnk'),
    (Join-Path $desktop 'Antigravity 启动器.lnk'),
    (Join-Path $desktop 'Antigravity 启动器 (v1.0 体验版).lnk'),
    (Join-Path $desktop 'Antigravity 启动器 (v0.9.1 稳定版).lnk'),
    (Join-Path $desktop 'Antigravity 节点中控台.lnk'),
    (Join-Path $desktop 'Antigravity 中文版.lnk'),
    (Join-Path $desktop 'Antigravity 英文恢复.lnk'),
    (Join-Path $desktop 'Antigravity 原版.lnk'),
    (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity.lnk'),
    (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 启动器.lnk')
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
