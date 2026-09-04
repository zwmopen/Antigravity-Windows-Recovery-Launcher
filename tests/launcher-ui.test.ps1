$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$launcher = Get-Content -LiteralPath (Join-Path $root 'src\Antigravity-Recovery-Launcher.cs') -Raw -Encoding UTF8
$supervisor = Get-Content -LiteralPath (Join-Path $root 'src\Antigravity-ProxySupervisor.ps1') -Raw -Encoding UTF8

foreach ($requiredText in @(
    'AntigravityLaunchCapsuleForm',
    'AntigravityHotLaunchChoiceForm',
    'ActivateExistingAntigravity',
    'TopMost = true',
    'ReadLogSince(logStartOffset)',
    'WaitForExistingSupervisor',
    'IsOwnWatcherRunning',
    'displayedProgress < state.TargetProgress',
    'animationTick % 2 == 0'
)) {
    if (-not $launcher.Contains($requiredText)) { throw ('launcher_ui_missing:' + $requiredText) }
}
if (-not $supervisor.Contains("'candidate_discovery_completed'")) { throw 'candidate_discovery_event_missing' }
if (-not $supervisor.Contains('candidate_count = $candidates.Count')) { throw 'candidate_count_missing' }
if (-not $supervisor.Contains('candidate_index = $candidateIndex')) { throw 'candidate_index_missing' }
if (-not $supervisor.Contains('candidate_total = $candidateTotal')) { throw 'candidate_total_missing' }
Write-Output 'launcher-ui.test.ps1: PASS'
