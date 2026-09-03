$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$source = Get-Content -LiteralPath (Join-Path $root 'src\Antigravity-ProxySupervisor.ps1') -Raw -Encoding UTF8

if ($source -notmatch '\$MaxCandidateCount\s*=\s*96') {
    throw 'candidate_cap_should_cover_current_multi_subscription_pool'
}
if ($source.Contains('for ($round = 0; $ordered.Count -lt $MaxCandidateCount; $round++)')) {
    throw 'candidate_cap_must_not_run_before_state_filter'
}
if ($source -notmatch 'fallbackReserve') {
    throw 'us_fallback_reservation_missing'
}
Write-Output 'candidate-cap-fairness.test.ps1: PASS'
