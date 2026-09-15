$ErrorActionPreference='Stop'
$t=$null;$e=$null
$a=[Management.Automation.Language.Parser]::ParseFile("$PSScriptRoot\..\src\Antigravity-ProxySupervisor.ps1",[ref]$t,[ref]$e)
$f=$a.EndBlock.Statements | Where-Object {$_ -is [Management.Automation.Language.FunctionDefinitionAst] -and $_.Name -eq 'Invoke-IsolatedCandidateProbe'}
. ([scriptblock]::Create($f.Extent.Text))
$ProxyRoot=$env:TEMP;$ConfigPath='production.yaml';$Port=17897;$ProxyUrl='http://127.0.0.1:17897';$MihomoPath='mock';$script:FixedUpstream=$null
$script:stopped=0
function Write-PrivateConfig {param($ProfileId,$Candidate) if($Port -eq 17897 -or $ConfigPath -eq 'production.yaml'){throw 'PRODUCTION_TOUCHED'};return @{}}
function Test-PrivateConfig {}
function Start-Process {param($FilePath,$ArgumentList,$WindowStyle,[switch]$PassThru) $p=[pscustomobject]@{Id=12;HasExited=$false};$p|Add-Member ScriptMethod Kill {$script:stopped++;$this.HasExited=$true};$p|Add-Member ScriptMethod WaitForExit {param($ms) return $true};return $p}
function Test-LocalPort {param($TestPort) return $true}
function Write-SafeLog {param($Event,$Values)}
function Test-GoogleConnectivity {if($ProxyUrl -eq 'http://127.0.0.1:17897'){throw 'PRODUCTION_TOUCHED'};throw 'network_failure'}
foreach($i in 1..2){try{Invoke-IsolatedCandidateProbe -Candidate @{};throw 'expected failure'}catch{if($_.Exception.Message -ne 'network_failure'){throw}}}
if($script:stopped -ne 2 -or $Port -ne 17897 -or $ConfigPath -ne 'production.yaml'){throw 'cleanup_or_scope_failed'}
function Test-GoogleConnectivity {return @{RttMs=50}}
function Test-ProxyEgress {param($ExpectedCountry,$ExpectedIp) return 'JP'}
function Test-RealModelGeneration {return $true}
$result=Invoke-IsolatedCandidateProbe -Candidate @{ExpectedEgressCountry='JP'}
if($result.Country -ne 'JP' -or $script:stopped -ne 3){throw 'success_cleanup_failed'}
Write-Output 'two_failures_and_success_isolated_cleanup_pass'
