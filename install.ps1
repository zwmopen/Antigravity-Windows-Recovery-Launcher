[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$app = Join-Path $root 'releases\current'
$launcher = Join-Path $app 'Antigravity-Recovery-Launcher.exe'
$watcher = Join-Path $app 'Antigravity-AccountWatcher.exe'
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'Antigravity.lnk'
$runtime = Join-Path $env:LOCALAPPDATA 'Antigravity'
$backupRoot = Join-Path $runtime 'shortcut-backups'

if (-not (Test-Path -LiteralPath $launcher) -or -not (Test-Path -LiteralPath $watcher)) { throw 'build_first' }

if (Test-Path -LiteralPath $shortcutPath) {
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    Copy-Item -LiteralPath $shortcutPath -Destination (Join-Path $backupRoot ('Antigravity-before-standalone-app-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.lnk'))
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcher
$shortcut.Arguments = ''
$shortcut.WorkingDirectory = $app
$shortcut.IconLocation = (Join-Path $env:LOCALAPPDATA 'Programs\antigravity\Antigravity.exe') + ',0'
$shortcut.Description = 'Antigravity recovery launcher'
$shortcut.Save()

Set-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'AntigravityAccountWatcher' -Value ('"' + $watcher + '"')

Get-Process -Name 'Antigravity-AccountWatcher' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500
Start-Process -FilePath $watcher -WorkingDirectory $app -WindowStyle Hidden

Write-Output $launcher
