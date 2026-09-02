[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$source = Join-Path $root 'src\Antigravity-ProxySupervisor.ps1'
$raw = & $source -PolicyTest
if ([string]::IsNullOrWhiteSpace(($raw -join ''))) { throw 'failover_policy_probe_failed' }
$policy = $raw | ConvertFrom-Json

if ([int]$policy.candidate_count -lt 2) { throw 'failover_requires_at_least_two_current_candidates' }
if ([int]$policy.unique_count -ne [int]$policy.candidate_count) { throw 'failover_candidate_ids_not_unique' }
if (-not [bool]$policy.preferred_first) { throw 'verified_primary_not_first' }
if ([int]$policy.max_candidate_count -lt 12 -or [int]$policy.max_candidate_count -gt 32) { throw 'cross_subscription_pool_size_invalid' }
if ([int]$policy.cooldown_minutes -lt 15) { throw 'candidate_cooldown_too_short' }
if (-not [bool]$policy.real_model_gate) { throw 'real_model_gate_required' }
if ([int]$policy.model_probe_timeout_seconds -lt 30) { throw 'real_model_probe_timeout_too_short' }
if ([int]$policy.stop_process_timeout_seconds -lt 15) { throw 'antigravity_process_tree_exit_wait_too_short' }
if (-not [bool]$policy.log_failure_nonfatal) { throw 'supervisor_log_contention_must_not_abort_recovery' }

Write-Output ('PASS failover policy candidates=' + [int]$policy.candidate_count +
    ' cooldown_minutes=' + [int]$policy.cooldown_minutes +
    ' real_model_gate=' + [bool]$policy.real_model_gate)
