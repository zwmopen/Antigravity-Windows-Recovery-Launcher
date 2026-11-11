$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$launcher = Get-Content -LiteralPath (Join-Path $root 'src\Antigravity-Recovery-Launcher.cs') -Raw -Encoding UTF8
$supervisor = Get-Content -LiteralPath (Join-Path $root 'src\Antigravity-ProxySupervisor.ps1') -Raw -Encoding UTF8

foreach ($requiredText in @(
    'AntigravityLaunchCapsuleForm',
    'AntigravityHotLaunchChoiceForm',
    'ActivateExistingAntigravity',
    'TopMost = false',
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
# Account-first startup is logged before the fast network path starts.
$networkFastPath = $supervisor.IndexOf('$fastStartupPassed = $false')
$bootstrap = $supervisor.LastIndexOf('Repair-DesktopShortcut', $networkFastPath)
$accountFirst = $supervisor.IndexOf('Invoke-AccountAdmissionGate', $bootstrap)
if ($bootstrap -lt 0 -or $accountFirst -lt $bootstrap -or $networkFastPath -lt $accountFirst) {
    throw 'account_gate_must_run_before_network_selection'
}
foreach ($probeEvent in @(
    'latency_probe_started', 'latency_probe_passed',
    'google_connectivity_started', 'google_probe_started', 'google_probe_completed',
    'gemini_weekly = [math]::Round'
)) {
    if (-not $supervisor.Contains($probeEvent)) { throw ('real_probe_event_missing:' + $probeEvent) }
}
foreach ($uiContract in @(
    'DrawStepRow(e.Graphics, 1, 88',
    'DrawStepRow(e.Graphics, 5, 320',
    'GetValue(line, "candidate_count")',
    'GetValue(line, "duration_ms")',
    'GetValue(line, "api")',
    'candidate_preflight_started',
    'google_probe_completed',
    'state.WorkspacePassed = true',
    'Visible = false'
)) {
    if (-not $launcher.Contains($uiContract)) { throw ('truthful_startup_ui_missing:' + $uiContract) }
}
$uiStart = $launcher.IndexOf('internal class AntigravityLaunchCapsuleForm')
$uiEnd = $launcher.IndexOf('private void InitializeComponent()', $uiStart)
if ($uiStart -lt 0 -or $uiEnd -lt $uiStart) { throw 'capsule_paint_method_missing' }
$paint = $launcher.Substring($uiStart, $uiEnd - $uiStart)
if ($paint.Contains('DrawPillBadge(e.Graphics')) { throw 'decorative_startup_badges_must_not_be_drawn' }

Write-Output 'launcher-ui.test.ps1: PASS'
