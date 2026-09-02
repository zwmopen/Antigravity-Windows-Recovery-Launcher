$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$launcher = Get-Content -LiteralPath (Join-Path $root 'src\Antigravity-Recovery-Launcher.cs') -Raw -Encoding UTF8
$supervisor = Get-Content -LiteralPath (Join-Path $root 'src\Antigravity-ProxySupervisor.ps1') -Raw -Encoding UTF8

foreach ($requiredText in @(
    'Antigravity 智能启动器',
    '已建立 Antigravity 独立代理 127.0.0.1:17897',
    '条候选线路',
    '正在验证 ',
    'discoveredTotal > 0 ? discoveredTotal.ToString() : totalLabel',
    '已发现 " + discoveredLabel + " 条候选线路 · 正在验证',
    'candidate_index',
    'candidate_total',
    '真实模型 OK 验证通过',
    '中文翻译注入成功，Antigravity 已就绪',
    '✅ 已建立 Antigravity 独立代理',
    'Clash 7897 保持不变',
    'ReadLogSince(logStartOffset)',
    'WaitForConcurrentRecovery',
    'HasFreshReadyState',
    'IsOwnWatcherRunning',
    '后台检查已占用恢复通道，等待它完成',
    'displayedProgress < status.Ceiling',
    'animationTick % 2 == 0'
)) {
    if (-not $launcher.Contains($requiredText)) { throw ('launcher_ui_missing:' + $requiredText) }
}
if (-not $supervisor.Contains("'candidate_discovery_completed'")) { throw 'candidate_discovery_event_missing' }
if (-not $supervisor.Contains('candidate_count = $candidates.Count')) { throw 'candidate_count_missing' }
if (-not $supervisor.Contains('candidate_index = $candidateIndex')) { throw 'candidate_index_missing' }
if (-not $supervisor.Contains('candidate_total = $candidateTotal')) { throw 'candidate_total_missing' }
Write-Output 'launcher-ui.test.ps1: PASS'
