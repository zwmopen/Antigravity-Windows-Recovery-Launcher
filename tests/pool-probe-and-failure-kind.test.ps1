$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$root = Split-Path -Parent $PSScriptRoot
$supervisorPath = Join-Path $root 'src\Antigravity-ProxySupervisor.ps1'
$source = Get-Content -LiteralPath $supervisorPath -Raw -Encoding UTF8

# 1. Verify concurrent pool & parallel probe helpers exist and bind clean free ports
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($supervisorPath, [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw ('supervisor_parse_error:' + $errors[0].Message) }

foreach ($fnName in @('Get-FreeTcpPorts', 'Invoke-ParallelEndpointProbes', 'Invoke-ConcurrentNodePoolProbe', 'Test-RealModelGeneration')) {
    $fn = $ast.Find({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $fnName }, $true)
    if ($null -eq $fn) { throw ('missing_function:' + $fnName) }
    Invoke-Expression $fn.Extent.Text
}

$ports = @(Get-FreeTcpPorts -Count 5 -StartPort 43900)
if ($ports.Count -ne 5 -or @($ports | Select-Object -Unique).Count -ne 5) {
    throw 'free_tcp_ports_not_distinct'
}

# 2. Verify Test-RealModelGeneration classifies model_timeout (even if status=SUCCESS) and 429 quota as model_transport, not model_non_ok
$testRoot = Join-Path $env:TEMP ('pool-failure-kind-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
try {
    $fakeAgy = Join-Path $testRoot 'agy.exe'
    Set-Content -LiteralPath $fakeAgy -Value 'stub' -Encoding ASCII
    $AgyPath = $fakeAgy
    $ProxyRoot = $testRoot
    $ProxyUrl = 'http://127.0.0.1:17897'
    $ModelProbePrompt = 'Reply with exactly OK.'
    $ModelProbeTimeoutSeconds = 30
    $RecoveryReason = 'Startup'
    $script:LastModelProbeState = ''
    function Write-SafeLog { param($Event, $Values) }
    function Test-IsLanguageServerReady { return $false }
    function Restore-ProcessEnvironment { param($Previous) }

    # Case A: timeout right after partial SUCCESS JSON must throw model_transport, NOT model_non_ok
    function Invoke-BoundedModelProcess {
        return @{ Output = '{"status":"SUCCESS","response":"OK"}'; ExitCode = 1; AbortReason = 'model_timeout' }
    }
    $caught = ''
    try { $null = Test-RealModelGeneration } catch { $caught = [string]$_.Exception.Message }
    if ($caught -ne 'model_transport') { throw ('timeout_must_be_model_transport_got:' + $caught) }

    # Case B: account-level 429 RESOURCE_EXHAUSTED must throw model_transport, NOT permanently retire proxy node
    function Invoke-BoundedModelProcess {
        return @{ Output = '{"status":"ERROR","response":"","error":"RESOURCE_EXHAUSTED (code 429): Individual quota reached"}'; ExitCode = 1; AbortReason = '' }
    }
    $caught429 = ''
    try { $null = Test-RealModelGeneration } catch { $caught429 = [string]$_.Exception.Message }
    if ($caught429 -ne 'model_transport') { throw ('quota_429_must_be_model_transport_got:' + $caught429) }

    # Case C: true location failure must still throw model_location
    function Invoke-BoundedModelProcess {
        return @{ Output = '{"status":"ERROR","response":"","error":"FAILED_PRECONDITION (code 400): User location is not supported for the API use."}'; ExitCode = 1; AbortReason = 'model_location' }
    }
    $caughtLoc = ''
    try { $null = Test-RealModelGeneration } catch { $caughtLoc = [string]$_.Exception.Message }
    if ($caughtLoc -ne 'model_location') { throw ('location_must_be_model_location_got:' + $caughtLoc) }

    # Case D: punctuation variant "OK." passes cleanly
    function Invoke-BoundedModelProcess {
        return @{ Output = '{"status":"SUCCESS","response":"OK."}'; ExitCode = 0; AbortReason = '' }
    }
    if (-not (Test-RealModelGeneration)) { throw 'normalized_ok_should_pass' }
} finally {
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}

# 3. Verify compiled Launcher ParseLogState handles concurrent pool and warm reuse states cleanly
$exePath = Join-Path $root 'releases\current\Antigravity-Recovery-Launcher.exe'
$asm = [Reflection.Assembly]::LoadFile($exePath)
$capsule = $asm.GetType('AntigravityLauncher.AntigravityLaunchCapsuleForm')
$flags = [Reflection.BindingFlags]'NonPublic,Static,Instance'
$parse = $capsule.GetMethod('ParseLogState', $flags)
function Assert-State($log, $field, $pattern) {
    $st = $parse.Invoke($null, @($log))
    $val = [string]$st.GetType().GetField($field, $flags).GetValue($st)
    if ($val -notlike $pattern) { throw ('unexpected_pool_state:' + $field + ':' + $val) }
}

Assert-State 'pool_probe_started pool_size=20 mode=concurrent_pool' 'LineText' '*多核并发探活*20 条*'
Assert-State 'pool_probe_completed pool_size=20 winners=14 elapsed_ms=2840 mode=concurrent_pool' 'LineText' '*2840ms*14 条*'
Assert-State 'latency_probe_started candidate_index=3 candidate_total=20 region=US mode=concurrent_pool' 'LineText' '*测速 3/20*US*'
Assert-State 'proxy_reused pid=1234 port=17897 mode=warm_fast_path' 'LinePassed' 'True'
Assert-State 'warm_proxy_api_unhealthy api=0 cloudcode=0 oauth=404 rtt_ms=110' 'LinePassed' 'False'

Write-Output 'PASS: concurrent pool helpers, timeout/429 failure classification, and compiled capsule pool states verified'
