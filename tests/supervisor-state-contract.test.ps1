$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$source = Get-Content -LiteralPath (Join-Path $root 'src\Antigravity-ProxySupervisor.ps1') -Raw -Encoding UTF8

if (-not $source.Contains('function Save-SupervisorFailureState')) {
    throw 'failure_state_writer_missing'
}

$stopMatch = [regex]::Match($source, '(?s)function Stop-WithMessage\s*\{.*?\n\}')
if (-not $stopMatch.Success -or $stopMatch.Value.IndexOf('Save-SupervisorFailureState', [System.StringComparison]::Ordinal) -lt 0) {
    throw 'stop_path_must_persist_failure_state'
}
if (-not $source.Contains("status = 'failed'")) { throw 'failure_state_status_missing' }
if (-not $source.Contains('failure_event = $Event')) { throw 'failure_event_missing' }
if ($source -notmatch 'candidate_index\s*=\s*\[int\]\$script:CandidateIndex') { throw 'failure_candidate_index_missing' }
if ($source -notmatch 'candidate_total\s*=\s*\[int\]\$script:CandidateTotal') { throw 'failure_candidate_total_missing' }

Write-Output 'supervisor-state-contract.test.ps1: PASS'
