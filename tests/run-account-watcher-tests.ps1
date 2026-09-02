[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$source = Join-Path $root 'src\Antigravity-AccountWatcher.cs'
$testSource = Join-Path $root 'tests\AccountWatcher.PolicyTests.cs'
$outputDirectory = Join-Path $root '.work\tests'
$output = Join-Path $outputDirectory 'AccountWatcher.PolicyTests.exe'
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $csc)) {
    $csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
}
if (-not (Test-Path -LiteralPath $csc)) { throw 'csc_not_found' }

New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
& $csc /nologo /target:exe /optimize+ /reference:System.Management.dll /main:AccountWatcherPolicyTests ("/out:" + $output) $source $testSource
if ($LASTEXITCODE -ne 0) { throw 'watcher_policy_test_build_failed' }
& $output
if ($LASTEXITCODE -ne 0) { throw 'watcher_policy_tests_failed' }
