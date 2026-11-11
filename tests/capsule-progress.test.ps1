$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$a = [Reflection.Assembly]::LoadFile((Join-Path $root 'releases\current\Antigravity-Recovery-Launcher.exe'))
$t = $a.GetType('AntigravityLauncher.AntigravityLaunchCapsuleForm')
$flags = [Reflection.BindingFlags]'NonPublic,Static,Instance'
$parse = $t.GetMethod('ParseLogState',$flags)
function Check-State($log,$field,$expected) {
    $s = $parse.Invoke($null,@($log))
    $actual = $s.GetType().GetField($field,$flags).GetValue($s)
    if ([string]$actual -notlike $expected) { throw ('unexpected_progress:' + $field + ':' + $actual) }
}
Check-State 'preflight_account_check_completed action=reused' AccountPassed True
Check-State 'formal_model_gate_started' ModelText '*正在请求真实 AI*'
Check-State 'model_probe_waiting elapsed_seconds=15' ModelText '*15 秒*40 秒*'
Check-State 'model_probe_aborted reason=model_location' FooterText '*地区限制*换线*'
Check-State "model_generation_probe_passed`ncandidate_preflight_started candidate_index=2 candidate_total=23" ModelPassed False
Check-State "model_generation_probe_failed failure_kind=model_location`nformal_model_gate_started`nmodel_generation_probe_passed" ModelPassed True
Check-State 'preflight_account_check_completed plan=PRO gemini_5h=83 gemini_weekly=61' AccountText '*PRO*83%*61%*'
Check-State 'candidate_discovery_completed candidate_count=42' LineText '*发现 42 条候选*准备测速*'
Check-State 'latency_probe_started candidate_index=2 candidate_total=6 region=JP' LineText '*测速 2/6*JP*'
Check-State 'latency_probe_passed candidate_index=2 candidate_total=6 region=JP rtt_ms=186' LineText '*186ms*'
Check-State 'google_probe_completed service=ModelAPI status=403 rtt_ms=62' GooglePassed False
Check-State 'google_connectivity_passed google=204 api=404 oauth=404' GoogleText '*端点已响应*API 404*OAuth 404*'
Check-State 'model_generation_probe_passed duration_ms=2450' ModelText '*2450ms*'
Check-State 'antigravity_ready' WorkspacePassed True
Write-Output 'PASS: compiled UI handles account pass, elapsed wait, location fallback, candidate reset and final success'
