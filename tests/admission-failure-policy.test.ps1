$ErrorActionPreference='Stop'
$patch=Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1'
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($patch,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$t=Get-Content -LiteralPath $patch -Raw -Encoding UTF8
$from=$t.IndexOf('    $maxFormalModelAttempts = 8')
$to=$t.IndexOf('if ($null -eq $selectedCandidate) {',$from)
$block=$t.Substring($from,$to-$from)
# Run the actual admission loop with network/process dependencies replaced.
function Write-SafeLog {param($Event,$Values) if($Event -eq 'candidate_preflight_passed'){$script:FalsePass++}}
function Invoke-IsolatedCandidateProbe {param($Candidate,[switch]$SkipModelGeneration) @{Connectivity=@{};Country=$Candidate.Region}}
function Write-PrivateConfig {param($ProfileId,$Candidate) @{ConfigHash='x'}}
function Test-PrivateConfig {}
function Start-OrReuseMihomo {param($ExpectedConfigHash)}
function Test-GoogleConnectivity {}
function Invoke-AccountAdmissionGate {}
function Start-AntigravityBeforeModelGate {}
function Test-RealModelGeneration {$script:ProbeRegions+=$region;throw 'model_location'}
function Get-CandidateFailureKind {param($ErrorRecord) 'model_location'}
function Get-CandidateFailureDisposition {param($FailureKind) 'cooldown'}
function Add-NodeCooldown {param($State,$NodeId,$Reason)}
function Add-NodeRetirement {param($State,$NodeId,$Reason,$Candidate)}
function Mark-NodeSuccess {param($State,$Candidate) $script:FalsePass++}
$script:AdmissionStartedAt=Get-Date
$script:AttemptedCandidateIds=@{};$script:AttemptedCandidateFailureKinds=@{}
$script:FalsePass=0;$script:ProbeRegions=@()
$orderedCandidates=@(); foreach($r in @('JP','JP','JP','JP','JP','US','US','US','US','US')){$orderedCandidates+=[pscustomobject]@{Id=[guid]::NewGuid().ToString();Region=$r;SourceId='mock'}}
$orderFn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Get-AdmissionRoundOrder'},$true)
Invoke-Expression $orderFn.Extent.Text
$orderedCandidates=@(Get-AdmissionRoundOrder -Candidates $orderedCandidates)
$selectedCandidate=$null;$candidateIndex=0;$candidateTotal=8;$RecoveryReason='LocationFailure';$failoverState=@{};$Port=17897;$ConfigPath=Join-Path $PSScriptRoot 'not-present.mock'
& ([scriptblock]::Create(($block.Substring(0,$block.LastIndexOf('}')))))
if($null -ne $selectedCandidate -or $script:FalsePass -ne 0){throw 'model failure was marked successful'}
if(($script:ProbeRegions -join ',') -ne 'JP,JP,US,US,JP,JP,US,US'){throw ('wrong bounded region sequence: '+($script:ProbeRegions -join ','))}
'PASS: all model failures produce no admission and no success history; bounded JP,JP,US,US,JP,JP,US,US fallback'
if($t.Contains('formal_model_gate_fallback')){throw 'fail-open fallback remains'}
if($t.Contains('$RuntimeDirectory')){throw 'undefined account path remains'}
if($t.Contains("real_model_probe = 'passed'")){throw 'hardcoded passed state remains'}
if($t -notmatch 'if \(\$status204 -eq 204\) \{\s*Invoke-AccountAdmissionGate\s*\$null = Test-RealModelGeneration'){throw 'warm startup skips real model gate'}
'PASS: warm-start revalidation, account path and truthful model state checks'

$diversityPool = @(
 [pscustomobject]@{Id='a1';Region='JP';SourceId='a'},
 [pscustomobject]@{Id='a2';Region='JP';SourceId='a'},
 [pscustomobject]@{Id='b1';Region='JP';SourceId='b'},
 [pscustomobject]@{Id='u1';Region='US';SourceId='u'}
)
$diverseOrder = @(Get-AdmissionRoundOrder -Candidates $diversityPool)
if (($diverseOrder.Id -join ',') -ne 'a1,b1,u1,a2') { throw 'source_diversity_or_round_order_failed' }
'PASS: different subscription sources get first-round opportunities'

$restartLine = ($t -split "`n" | Where-Object { $_ -match '^\$forceRestartRequested =' })
if ($restartLine -match 'UserRequestedRepair|NetworkFailure|LocationFailure') { throw 'network_repair_must_not_restart_editor' }
'PASS: network repair does not request editor restart'
