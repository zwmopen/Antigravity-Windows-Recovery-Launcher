$ErrorActionPreference='Stop'
$s=Get-Content "$PSScriptRoot\..\src\Antigravity-ProxySupervisor.ps1" -Raw
if(-not $s.Contains('function Invoke-IsolatedCandidateProbe')){throw 'missing isolated candidate probe'}
if($s.Contains('$fastConfig = Write-PrivateConfig')){throw 'unsafe fast path'}
if(-not $s.Contains('$latencyCandidates | Sort-Object RttMs')){throw 'missing measured latency ordering'}
Write-Output 'isolated_probe_contract_pass'
