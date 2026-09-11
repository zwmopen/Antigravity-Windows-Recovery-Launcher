$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $root 'src\Antigravity-ProxySupervisor.ps1'
$source = Get-Content -Raw $sourcePath

# 1. Assert LocationFailure is NOT in forceRestartRequested
$restartLines = ($source -split "`r?`n") | Where-Object { $_ -match '\$forceRestartRequested\s*=' }
if ($restartLines -match "'LocationFailure'") {
    throw 'regression: LocationFailure must not force restart Antigravity process tree'
}
Write-Output 'contract_seamless_location_failure_ok'

# 2. Test Get-OrderedCandidates behavior under LocationFailure
$candidates = @(
    [pscustomobject]@{ Id = 'jp-historically-verified'; SourceId = 'src-jp'; Priority = 0; Region = 'JP'; RegionRank = 1; Name = 'jp-historically-verified' },
    [pscustomobject]@{ Id = 'us-unverified'; SourceId = 'src-us'; Priority = 0; Region = 'US'; RegionRank = 0; Name = 'us-unverified' }
)

$state = [pscustomobject]@{
    successful_nodes = @([pscustomobject]@{
        node_id = 'jp-historically-verified'
        source_id = 'src-jp'
        last_passed_at = (Get-Date).ToString('o')
        success_count = 5
    })
    retired_nodes = @()
    failed_nodes = @()
    active_node_id = 'jp-failed-active'
}

$functionExtract = @'
function New-EmptyFailoverState { [pscustomobject]@{ successful_nodes=@(); retired_nodes=@(); failed_nodes=@(); active_node_id='' } }
function Get-RetiredNodeIds { @() }
function Get-SuccessfulNodeEntries { $state.successful_nodes }
$MaxCandidateCount = 32
'@

$startPos = $source.IndexOf('function Get-OrderedCandidates {')
$endPos = $source.IndexOf('function Get-ListeningOwner {')
$fnCode = $source.Substring($startPos, $endPos - $startPos)

$sb = [ScriptBlock]::Create($functionExtract + "`n" + $fnCode)
. $sb

$resLocation = Get-OrderedCandidates -Candidates $candidates -State $state -RecoveryReason 'LocationFailure'
if ($resLocation.Count -lt 2) { throw 'failed to order candidates' }
if ($resLocation[0].Id -ne 'us-unverified') {
    throw 'regression: LocationFailure must prioritize US candidate over historically verified JP candidate'
}
Write-Output 'location_failure_us_priority_ok'

$resStartup = Get-OrderedCandidates -Candidates $candidates -State $state -RecoveryReason 'Startup'
if ($resStartup[0].Id -ne 'jp-historically-verified') {
    throw 'regression: fresh Startup must prioritize verified low-latency route'
}
Write-Output 'startup_verified_speed_priority_ok'
$resAccount = Get-OrderedCandidates -Candidates $candidates -State $state -RecoveryReason 'AccountChange'
if ($resAccount[0].Id -ne 'jp-historically-verified') { throw 'account change must preserve verified route' }
Write-Output 'account_change_verified_priority_preserved_ok'
Write-Output 'ALL_SEAMLESS_FAILOVER_TESTS_PASS'
