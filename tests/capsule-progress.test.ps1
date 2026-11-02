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
Write-Output 'PASS: compiled UI handles account pass, elapsed wait, location fallback, candidate reset and final success'
