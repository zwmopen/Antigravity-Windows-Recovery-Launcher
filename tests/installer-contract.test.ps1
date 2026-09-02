$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$install = Get-Content -LiteralPath (Join-Path $root 'install.ps1') -Raw
$uninstall = Get-Content -LiteralPath (Join-Path $root 'uninstall.ps1') -Raw
$iss = Get-Content -LiteralPath (Join-Path $root 'installer\Antigravity-Recovery-Setup.iss') -Raw

foreach ($required in @('$InstallRoot', '$SourceApp', 'OrdinalIgnoreCase', 'agy_sha512_mismatch')) {
    if (-not $install.Contains($required)) { throw ('install_contract_missing:' + $required) }
}
foreach ($required in @('PrivilegesRequired=lowest', 'UsePreviousAppDir=yes', 'DisableDirPage=no', 'DefaultDirName={localappdata}\Antigravity\launcher', '立即启动', '打开安装目录', '[UninstallRun]')) {
    if (-not $iss.Contains($required)) { throw ('iss_contract_missing:' + $required) }
}
foreach ($preserved in @('Antigravity\private-proxy', 'Test-ShortcutOwnedByInstall', 'AntigravityAccountWatcher')) {
    if (-not $uninstall.Contains($preserved)) { throw ('uninstall_contract_missing:' + $preserved) }
}
foreach ($forbidden in @('Remove-Item -LiteralPath $runtimeRoot -Recurse', 'Remove-Item -LiteralPath $env:APPDATA', 'clash-verge-rev')) {
    if ($uninstall.Contains($forbidden)) { throw ('unsafe_uninstall_contract:' + $forbidden) }
}

Write-Output 'installer_contract_ok'
