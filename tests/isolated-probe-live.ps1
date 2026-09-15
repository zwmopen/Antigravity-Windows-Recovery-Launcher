param([switch]$RealModel)
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'source_parse_failed'}
foreach($stmt in $ast.EndBlock.Statements){if($stmt -is [Management.Automation.Language.FunctionDefinitionAst]){. ([scriptblock]::Create($stmt.Extent.Text))}}
function Write-SafeLog { param($Event,$Values) Write-Host $Event }
$ProxyRoot=Join-Path $env:LOCALAPPDATA 'Antigravity\private-proxy'
$ConfigPath=Join-Path $ProxyRoot 'mihomo-antigravity.yaml'
$Port=17897;$ProxyUrl='http://127.0.0.1:17897'
$MihomoPath='D:\Program Files\Clash Verge\verge-mihomo.exe'
$AgyPath=Join-Path $env:LOCALAPPDATA 'Antigravity\launcher\tools\agy\agy.exe'
$ProbeTimeoutMs=8000;$ConnectivityAttemptCount=1
$ModelProbeTimeoutSeconds=30;$ModelProbePrompt='Reply with exactly OK. Do not call tools or modify files.'
$TargetAlias='ANTIGRAVITY-VERIFIED-CANDIDATE';$script:FixedUpstream=$null
$beforePid=@(Get-NetTCPConnection -LocalPort 17897 -State Listen).OwningProcess
$beforeHash=(Get-FileHash $ConfigPath).Hash
$line=Get-Content $ConfigPath | Where-Object {$_ -match '^  - \{ name: ANTIGRAVITY-VERIFIED-CANDIDATE,'} | Select-Object -First 1
if(-not $line){throw 'unsupported_live_config_shape'}
$country=(Get-Content (Join-Path $ProxyRoot 'supervisor-state.json') -Raw | ConvertFrom-Json).egress_country
$candidate=[pscustomobject]@{Id='isolated-live';Definition=$line.Trim().Substring(2);ExpectedEgressCountry=$country}
try { $result=Invoke-IsolatedCandidateProbe -Candidate $candidate -ConnectivityOnly:(-not $RealModel); Write-Host ('probe_success rtt='+$result.Connectivity.RttMs) }
finally {
 if((Get-FileHash $ConfigPath).Hash -ne $beforeHash){throw 'production_config_changed'}
 $afterPid=@(Get-NetTCPConnection -LocalPort 17897 -State Listen).OwningProcess
 if("$beforePid" -ne "$afterPid"){throw 'production_pid_changed'}
 Write-Host 'production_pid_and_config_unchanged'
}
