[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$version = (Get-Content -LiteralPath (Join-Path $root 'VERSION') -Raw).Trim()
$releaseRoot = Join-Path $root 'releases\current'
$outRoot = Join-Path $root 'releases\public'
$stage = Join-Path $root ('.work\public-release-' + $version)
$archive = Join-Path $outRoot ('Antigravity-Windows-Recovery-Launcher-' + $version + '-windows-x64.zip')

& (Join-Path $root 'build.ps1') | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $releaseRoot 'Antigravity-Recovery-Launcher.exe'))) {
    throw 'release_build_missing'
}

if (Test-Path -LiteralPath $stage) {
    Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Path (Join-Path $stage 'releases\current') -Force | Out-Null
New-Item -ItemType Directory -Path $outRoot -Force | Out-Null

Copy-Item -Path (Join-Path $releaseRoot '*') -Destination (Join-Path $stage 'releases\current') -Recurse -Force
foreach ($file in @('install.ps1', 'README.md', 'LICENSE', 'SECURITY.md')) {
    Copy-Item -LiteralPath (Join-Path $root $file) -Destination (Join-Path $stage $file) -Force
}
Copy-Item -LiteralPath (Join-Path $root 'docs\THIRD-PARTY-NOTICES.txt') -Destination (Join-Path $stage 'THIRD-PARTY-NOTICES.txt') -Force

$forbiddenPatterns = @(
    '(?i)subscription.{0,20}(https?|token)',
    '(?i)(password|passwd|secret|refresh[_-]?token)\s*[:=]\s*[^<\s]',
    '(?i)vmess://|vless://|trojan://|ss://',
    '(?i)api/rest\?token='
)
foreach ($pattern in $forbiddenPatterns) {
    $match = Get-ChildItem -LiteralPath $stage -Recurse -File | Select-String -Pattern $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $match) { throw ('release_secret_scan_failed:' + $match.Path) }
}

$hashManifest = Get-ChildItem -LiteralPath $stage -Recurse -File | Sort-Object FullName | ForEach-Object {
    [pscustomobject]@{
        file = $_.FullName.Substring($stage.Length + 1).Replace('\', '/')
        sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        size = $_.Length
    }
}
$hashManifest | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $stage 'SHA256SUMS.json') -Encoding UTF8

if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $archive -CompressionLevel Optimal
[pscustomobject]@{
    version = $version
    archive = $archive
    sha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
    size = (Get-Item -LiteralPath $archive).Length
} | ConvertTo-Json
