$ErrorActionPreference = 'Stop'
$sourcePath = Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1'
$source = Get-Content -LiteralPath $sourcePath -Raw -Encoding UTF8

if ($source -match '\$priority\s*=\s*\(\$regionRank\s*\*\s*1000\)') {
    throw 'candidate priority must not encode a US-first region weight'
}
if ($source -match 'keep US first|Prefer US; use JP') {
    throw 'latency-first policy must not advertise US-first behavior'
}
if ($source -notmatch '(?i)lowest[- ]latency') {
    throw 'subscription report must describe lowest-latency selection'
}
if ($source -notmatch 'regionBuckets') {
    throw 'candidate cap must preserve a region-neutral pool'
}

Write-Output 'latency_first_policy_pass'
