$ErrorActionPreference = 'Stop'
$sourcePath = Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1'
$source = Get-Content -LiteralPath $sourcePath -Raw -Encoding UTF8

if (-not $source.Contains('function Get-LaunchedLanguageServerProcess')) {
    throw 'regression: fresh language server discovery helper missing'
}
if (-not $source.Contains('function Test-LanguageServerInitializedAfter')) {
    throw 'regression: fresh language server initialization marker helper missing'
}
$helperStart = $source.IndexOf('function Get-LaunchedLanguageServerProcess')
$helperEnd = $source.IndexOf('function Wait-AntigravityReady', $helperStart)
if ($helperEnd -lt $helperStart) { throw 'regression: readiness helper boundary missing' }
$helperBody = $source.Substring($helperStart, $helperEnd - $helperStart)
if ($helperBody -match '\$matches\s*=') {
    throw 'regression: startup helper must not reuse PowerShell automatic $Matches variable'
}
if (-not $helperBody.Contains('$createdAt = [datetime]$candidate.CreationDate')) {
    throw 'regression: startup helper must consume CIM CreationDate as DateTime'
}

$waitStart = $source.IndexOf('function Wait-AntigravityReady')
if ($waitStart -lt 0) { throw 'regression: readiness function missing' }
$waitBody = $source.Substring($waitStart)

if (-not $waitBody.Contains('Get-LaunchedLanguageServerProcess -MainPid $MainPid -LaunchTime $LaunchTime')) {
    throw 'regression: readiness still requires a direct language server child lookup'
}
if (-not $waitBody.Contains('Test-LanguageServerInitializedAfter -LogPath $languageLog -LaunchTime $LaunchTime')) {
    throw 'regression: readiness still uses a bounded tail that can lose the fresh initialization marker'
}
if ($waitBody -match '\$main\.MainWindowHandle\s*-ne\s*0') {
    throw 'regression: readiness still requires the Electron parent window handle'
}

Write-Output 'startup_health_discovery_contract_ok'
