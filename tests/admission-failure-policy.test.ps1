$ErrorActionPreference='Stop'
$patch=Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1'
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($patch,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors|Out-String)}
$t=Get-Content -LiteralPath $patch -Raw -Encoding UTF8
$from=$t.IndexOf('    $maxFormalModelAttempts = 4')
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
$orderedCandidates=@(); foreach($r in @('JP','JP','JP','US','US','US')){$orderedCandidates+=[pscustomobject]@{Id=[guid]::NewGuid().ToString();Region=$r;SourceId='mock'}}
$selectedCandidate=$null;$candidateIndex=0;$candidateTotal=6;$RecoveryReason='LocationFailure';$failoverState=@{};$Port=17897;$ConfigPath=Join-Path $PSScriptRoot 'not-present.mock'
& ([scriptblock]::Create(($block.Substring(0,$block.LastIndexOf('}')))))
if($null -ne $selectedCandidate -or $script:FalsePass -ne 0){throw 'model failure was marked successful'}
if(($script:ProbeRegions -join ',') -ne 'JP,JP,US,US'){throw ('wrong bounded region sequence: '+($script:ProbeRegions -join ','))}
'PASS: all model failures produce no admission and no success history; bounded JP,JP,US,US fallback'
if($t.Contains('formal_model_gate_fallback')){throw 'fail-open fallback remains'}
if($t.Contains('$RuntimeDirectory')){throw 'undefined account path remains'}
if($t.Contains("real_model_probe = 'passed'")){throw 'hardcoded passed state remains'}
if($t -notmatch 'if \(\$status204 -eq 204\) \{\s*Invoke-AccountAdmissionGate\s*\$null = Test-RealModelGeneration'){throw 'warm startup skips real model gate'}
'PASS: warm-start revalidation, account path and truthful model state checks'
