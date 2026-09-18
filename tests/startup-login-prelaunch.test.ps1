$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$supervisorPath = Join-Path $root 'src\Antigravity-ProxySupervisor.ps1'
$launcherPath = Join-Path $root 'src\Antigravity-Recovery-Launcher.cs'
$supervisor = Get-Content -LiteralPath $supervisorPath -Raw -Encoding UTF8
$launcher = Get-Content -LiteralPath $launcherPath -Raw -Encoding UTF8

if (-not $supervisor.Contains('[switch]$PrelaunchClient')) {
    throw 'regression: foreground prelaunch switch missing'
}
if (-not $supervisor.Contains('function Start-AntigravityBeforeModelGate')) {
    throw 'regression: login-window prelaunch helper missing'
}
$prelaunchIndex = $supervisor.IndexOf('function Start-AntigravityBeforeModelGate')
$gateIndex = $supervisor.IndexOf("Write-SafeLog -Event 'formal_model_gate_started'")
$callIndex = $supervisor.IndexOf('$null = Start-AntigravityBeforeModelGate')
if ($prelaunchIndex -lt 0 -or $gateIndex -lt 0 -or $callIndex -lt 0 -or $callIndex -gt $gateIndex) {
    throw 'regression: client must be opened before the formal model gate'
}
if (-not $supervisor.Contains("Write-SafeLog -Event 'antigravity_prelaunched_before_model_gate'")) {
    throw 'regression: prelaunch evidence event missing'
}
if (-not $launcher.Contains(' + " -PrelaunchClient"')) {
    throw 'regression: foreground launcher does not request client prelaunch'
}

Write-Output 'startup_login_prelaunch_contract_ok'
