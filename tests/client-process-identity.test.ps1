$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$source = Get-Content (Join-Path $root 'src/Antigravity-ProxySupervisor.ps1') -Raw -Encoding UTF8
$tokens = $null; $parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) {throw ($parseErrors | Out-String)}
foreach ($name in @('Test-AntigravityMainProcess','Get-AntigravityMainProcess')) {
 $functionAst = $ast.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$true)
 Invoke-Expression $functionAst.Extent.Text
}
$AntigravityPath = Join-Path $env:LOCALAPPDATA 'Programs/antigravity/Antigravity.exe'
$session = [Diagnostics.Process]::GetCurrentProcess().SessionId
function New-ProcessFixture([string]$Command) {
 [pscustomobject]@{Name='Antigravity.exe';ExecutablePath=$AntigravityPath;CommandLine=$Command;SessionId=$session}
}
foreach ($command in @('"Antigravity.exe" --import=file:///sdk/register_loader.js main.mjs','"Antigravity.exe" --import file:///sdk/register_loader.js dist/server.cjs','"Antigravity.exe" --type=renderer','"Antigravity.exe" --type=gpu-process','"Antigravity.exe" launch.mjs device-hub','"Antigravity.exe" -e "code"','')) {
 if (Test-AntigravityMainProcess (New-ProcessFixture $command)) {throw ('sidecar classified as main: '+$command)}
}
foreach ($command in @('"Antigravity.exe"','"Antigravity.exe" --proxy-server=http://127.0.0.1:17897 --antigravity-localization-loader')) {
 if (-not (Test-AntigravityMainProcess (New-ProcessFixture $command))) {throw 'valid main rejected'}
}
$otherSession=New-ProcessFixture '"Antigravity.exe"';$otherSession.SessionId=$session+1
if (Test-AntigravityMainProcess $otherSession) {throw 'other session accepted'}
$otherPath=New-ProcessFixture '"Antigravity.exe"';$otherPath.ExecutablePath='C:\other\Antigravity.exe'
if (Test-AntigravityMainProcess $otherPath) {throw 'other executable accepted'}
$launcher=Get-Content (Join-Path $root 'src/Antigravity-Recovery-Launcher.cs') -Raw -Encoding UTF8
if (-not $launcher.Contains('return FindAntigravityMainWindow() != IntPtr.Zero;')) {throw 'process-only hot entry returned'}
if (-not $launcher.Contains('if (activated) return 0;')) {throw 'failed activation silently exits'}
if (-not $launcher.Contains('if (GetForegroundWindow() == hWnd)')) {throw 'activation success not verified'}
if (-not $source.Contains('if ($forceRestartRequested) { Stop-ExistingAntigravity }')) {throw 'cold launch kills unrelated sidecars'}
Write-Output 'client-process-identity.test.ps1: PASS (sidecars, Chromium helpers, wrong session/path rejected; main accepted; failure fallback and foreground check)'
