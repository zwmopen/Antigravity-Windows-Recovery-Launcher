$ErrorActionPreference = 'Stop'
$sourcePath = Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1'
$source = Get-Content -LiteralPath $sourcePath -Raw

$promotion = $source.IndexOf("Write-SafeLog -Event 'candidate_promoting'")
if ($promotion -lt 0) { throw 'candidate promotion block missing' }

$start = $source.IndexOf('Start-OrReuseMihomo -ExpectedConfigHash $candidateConfig.ConfigHash', $promotion)
if ($start -lt 0) { throw 'formal proxy start missing' }

$formalGate = $source.IndexOf('$null = Test-RealModelGeneration', $start)
if ($formalGate -lt 0) { throw 'formal production model gate missing' }

$selected = $source.IndexOf('$selectedCandidate = $candidate', $formalGate)
if ($selected -lt 0 -or $formalGate -gt $selected) {
    throw 'formal model gate must precede candidate selection'
}

$passed = $source.IndexOf("candidate_preflight_passed", $formalGate)
if ($passed -lt 0 -or $formalGate -gt $passed) {
    throw 'formal model gate must precede candidate success event'
}

$catch = $source.IndexOf('} catch {', $formalGate)
if ($catch -lt 0) { throw 'candidate promotion rollback catch missing' }
$failedEvent = $source.IndexOf("formal_model_gate_failed", $catch)
if ($failedEvent -lt 0) { throw 'formal model gate failure event missing in rollback path' }

Write-Output 'formal_model_gate_contract_pass'
