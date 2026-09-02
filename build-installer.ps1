[CmdletBinding()]
param(
    [string]$IsccPath = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$version = (Get-Content -LiteralPath (Join-Path $root 'VERSION') -Raw).Trim()
$iss = Join-Path $root 'installer\Antigravity-Recovery-Setup.iss'
$expectedOutput = Join-Path $root ('releases\public\Antigravity-Windows-Recovery-Setup-' + $version + '-windows-x64.exe')
$innoVersion = '7.1.0'
$innoSha256 = '0362A383ED217D4C4239B5933866DD96D3EB2102737DA92F80F6057A4B40DF2F'
$toolRoot = Join-Path $root '.work\tools'
$localInnoRoot = Join-Path $toolRoot 'Inno Setup 7'
$localIscc = Join-Path $localInnoRoot 'ISCC.exe'
$innoInstaller = Join-Path $toolRoot ('innosetup-' + $innoVersion + '-x64.exe')
$innoUri = 'https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe'

& (Join-Path $root 'build.ps1') | Out-Null

function Test-IsccCandidate {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return $false
    }

    # The hosted Windows image may expose an older/minimal Inno Setup on PATH
    # without the Chinese language file. Selecting it makes an otherwise valid
    # build fail at [Languages]. Only accept compilers that can produce the
    # promised Chinese installer UI.
    $languageFile = Join-Path (Split-Path -Parent $Path) 'Languages\ChineseSimplified.isl'
    return (Test-Path -LiteralPath $languageFile)
}

$candidates = @()
if (-not [string]::IsNullOrWhiteSpace($IsccPath)) { $candidates += $IsccPath }
$candidates += @(
    $localIscc,
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 7\ISCC.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 7\ISCC.exe')
)
$command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($null -ne $command) { $candidates += $command.Source }
$iscc = $candidates | Where-Object { Test-IsccCandidate -Path ([string]$_) } | Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($iscc)) {
    New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
    if (-not (Test-Path -LiteralPath $innoInstaller)) {
        Invoke-WebRequest -Uri $innoUri -OutFile $innoInstaller -TimeoutSec 180
    }
    if ((Get-FileHash -LiteralPath $innoInstaller -Algorithm SHA256).Hash -ne $innoSha256) {
        throw 'inno_setup_installer_sha256_mismatch'
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $innoInstaller
    if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
        throw 'inno_setup_installer_signature_invalid'
    }
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', ('/DIR="' + $localInnoRoot + '"'))
    $installerProcess = Start-Process -FilePath $innoInstaller -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
    if ($installerProcess.ExitCode -ne 0 -or -not (Test-IsccCandidate -Path $localIscc)) {
        throw ('inno_setup_local_install_failed:' + $installerProcess.ExitCode)
    }
    $iscc = $localIscc
}

$issText = Get-Content -LiteralPath $iss -Raw
if (-not $issText.Contains('#define MyAppVersion "' + $version + '"')) {
    throw 'installer_version_not_synced'
}

$packageInputs = @(
    (Join-Path $root 'releases\current'),
    (Join-Path $root 'install.ps1'),
    (Join-Path $root 'uninstall.ps1'),
    (Join-Path $root 'LICENSE'),
    (Join-Path $root 'SECURITY.md'),
    (Join-Path $root 'docs\THIRD-PARTY-NOTICES.txt')
)
$inputFiles = @($packageInputs | ForEach-Object {
    if (Test-Path -LiteralPath $_ -PathType Container) { Get-ChildItem -LiteralPath $_ -Recurse -File } else { Get-Item -LiteralPath $_ }
})
if ($inputFiles.Name -contains 'agy.exe') { throw 'setup_must_not_bundle_agy' }
foreach ($pattern in @('(?i)vmess://|vless://|trojan://|ss://', '(?i)api/rest\?token=', '(?i)(refresh[_-]?token|client[_-]?secret)\s*[:=]\s*[^<\s]')) {
    $match = $inputFiles | Select-String -Pattern $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $match) { throw ('setup_secret_scan_failed:' + $match.Path) }
}

& $iscc $iss
if ($LASTEXITCODE -ne 0) { throw 'inno_setup_compile_failed' }
if (-not (Test-Path -LiteralPath $expectedOutput)) { throw 'setup_output_missing' }

[pscustomobject]@{
    version = $version
    setup = $expectedOutput
    sha256 = (Get-FileHash -LiteralPath $expectedOutput -Algorithm SHA256).Hash
    size = (Get-Item -LiteralPath $expectedOutput).Length
} | ConvertTo-Json
