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
# Truthful account-first startup contract (network checks must not claim login success).
$bootstrap = $supervisor.IndexOf('Repair-DesktopShortcut')
$accountFirst = $supervisor.IndexOf('Invoke-AccountAdmissionGate', $bootstrap)
$networkFastPath = $supervisor.IndexOf('$fastStartupPassed = $false', $bootstrap)
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
    'DrawStepRow(e.Graphics, 1, 88, "当前账号"',
    'DrawStepRow(e.Graphics, 5, 320, "启动工作区"',
    'state.LineText = "发现 " + total + " 条候选 · 正在准备测速"',
    'candidate_preflight_started',
    '端点已响应 · Google',
    '正在请求真实 AI 回复',
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
