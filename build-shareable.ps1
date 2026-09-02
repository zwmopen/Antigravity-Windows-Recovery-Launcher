[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $root 'src'
$version = (Get-Content -LiteralPath (Join-Path $root 'ASSISTANT_VERSION') -Raw).Trim()
$releaseRoot = Join-Path $root 'releases\shareable'
$packageName = 'Antigravity-Chinese-Assistant-' + $version
$packageRoot = Join-Path $releaseRoot $packageName
$zipPath = Join-Path $releaseRoot ($packageName + '-windows-x64.zip')
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'

if (-not (Test-Path -LiteralPath $csc)) { throw 'csc_missing' }
$resolvedReleaseRoot = [System.IO.Path]::GetFullPath($releaseRoot).TrimEnd('\') + '\'
$resolvedPackageRoot = [System.IO.Path]::GetFullPath($packageRoot)
if (-not $resolvedPackageRoot.StartsWith($resolvedReleaseRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'unsafe_package_path'
}
if (Test-Path -LiteralPath $resolvedPackageRoot) {
    Remove-Item -LiteralPath $resolvedPackageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null

$assistantOutput = Join-Path $packageRoot 'Antigravity-Chinese-Assistant.exe'
$loaderOutput = Join-Path $packageRoot 'Antigravity-CdpLocalizationLoader.exe'
& $csc /nologo /target:winexe /optimize+ /reference:System.Core.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:Microsoft.CSharp.dll ("/win32manifest:" + (Join-Path $source 'Antigravity-Chinese-Assistant.exe.manifest')) ("/out:" + $assistantOutput) (Join-Path $source 'Antigravity-Chinese-Assistant.cs')
if ($LASTEXITCODE -ne 0) { throw 'assistant_build_failed' }
& $csc /nologo /target:winexe /optimize+ /reference:System.dll ("/out:" + $loaderOutput) (Join-Path $source 'Antigravity-CdpLocalizationLoader.cs')
if ($LASTEXITCODE -ne 0) { throw 'localization_loader_build_failed' }

$extensionOutput = Join-Path $packageRoot 'localization-extension'
New-Item -ItemType Directory -Path $extensionOutput -Force | Out-Null
Copy-Item -Path (Join-Path $source 'localization-extension\*') -Destination $extensionOutput -Recurse -Force
Copy-Item -LiteralPath (Join-Path $root 'docs\SHAREABLE-README.txt') -Destination (Join-Path $packageRoot '使用说明.txt') -Force
Copy-Item -LiteralPath (Join-Path $root 'docs\THIRD-PARTY-NOTICES.txt') -Destination (Join-Path $packageRoot '第三方说明.txt') -Force

$manifestPath = Join-Path $packageRoot '文件校验.json'
$manifest = Get-ChildItem -LiteralPath $packageRoot -Recurse -File | Where-Object {
    $_.FullName -ne $manifestPath
} | ForEach-Object {
    [pscustomobject]@{
        file = $_.FullName.Substring($packageRoot.Length + 1)
        sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        size = $_.Length
    }
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8

if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
Compress-Archive -LiteralPath $packageRoot -DestinationPath $zipPath -CompressionLevel Optimal

[pscustomobject]@{
    package = $packageRoot
    zip = $zipPath
    sha256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
    size = (Get-Item -LiteralPath $zipPath).Length
}
