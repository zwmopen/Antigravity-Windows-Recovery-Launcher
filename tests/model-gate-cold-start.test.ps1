$ErrorActionPreference = 'Stop'
$sourcePath = Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1'
$source = Get-Content -LiteralPath $sourcePath -Raw

$modelStart = $source.IndexOf('function Test-RealModelGeneration')
$modelEnd = $source.IndexOf('function Sync-AntigravityProxySetting', $modelStart)
if ($modelStart -lt 0 -or $modelEnd -lt $modelStart) { throw 'model_gate_function_missing' }
$modelFunction = $source.Substring($modelStart, $modelEnd - $modelStart)

if ($modelFunction -match 'language_server_wait_started|language_server_wait_timeout|lsWaitSeconds') {
    throw 'cold_start_must_not_wait_for_existing_language_server'
}
$skipLog = $modelFunction.IndexOf("language_server_wait_skipped")
$agyInvoke = $modelFunction.IndexOf('$probeOutput = @(& $AgyPath')
if ($skipLog -lt 0 -or $agyInvoke -lt 0 -or $skipLog -gt $agyInvoke) {
    throw 'agy_bootstrap_path_missing'
}

$candidateLoop = $source.IndexOf('foreach ($candidate in $orderedCandidates)')
if ($candidateLoop -lt 0) { throw 'candidate_loop_missing' }
$preflightCall = $source.IndexOf('Invoke-IsolatedCandidateProbe -Candidate $candidate -SkipModelGeneration', $candidateLoop)
if ($preflightCall -lt 0) { throw 'candidate_preflight_must_not_consume_model_quota' }
$formalGate = $source.IndexOf('$null = Test-RealModelGeneration', $candidateLoop)
if ($formalGate -lt 0 -or $formalGate -lt $preflightCall) { throw 'formal_production_model_gate_missing' }

Write-Output 'model_gate_cold_start_contract_pass'
