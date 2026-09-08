$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$source = Get-Content -Raw (Join-Path $root 'src\Antigravity-ProxySupervisor.ps1')
$start = $source.IndexOf('foreach ($candidate in $orderedCandidates)')
if ($start -lt 0) { throw 'candidate_loop_missing' }
$loop = $source.Substring($start)
$probe = $loop.IndexOf('$candidateConnectivity = Test-GoogleConnectivity')
$launch = $loop.IndexOf('Start-OrReuseMihomo -ExpectedConfigHash $candidateConfig.ConfigHash')
if ($launch -lt 0 -or $launch -gt $probe) { throw 'regression: candidate proxy must start before Google handshake' }
Write-Output 'proxy_start_order_ok'
if ($source.Contains('$refreshed = Update-ClashSubscriptionProfiles')) { throw 'regression: recovery must not refresh global subscriptions' }
if ($source.Contains("'model_generation_fast_passed'")) { throw 'regression: connectivity cannot pass the model gate' }
Write-Output 'recovery_boundaries_ok'
