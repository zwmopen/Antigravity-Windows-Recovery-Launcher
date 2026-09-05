<#
.SYNOPSIS
    Antigravity 智能切号与平滑重启工具 (PowerShell 调度入口)

.DESCRIPTION
    1. 优雅退出当前 Antigravity 客户端（WM_CLOSE 留出 3 秒保存并释放凭据锁）；
    2. 智能评估当前 7 个账号的有效额度，自动挑选大于阈值（默认 5%）的最高健康账号；
    3. 连接 Cockpit WebSocket 接口写入目标账号凭据（静默不启动）；
    4. 拉起桌面智能启动器（绑定 17897 纯正专线 + 模型响应门禁 + 汉化扩展 + 极速置顶）。

.PARAMETER Threshold
    切号阈值（百分比，默认 5.0）。

.PARAMETER Target
    指定切入的目标账号（邮箱或 ID，可选）。

.PARAMETER Force
    强制执行切号（即使当前账号额度充足）。

.PARAMETER StatusOnly
    仅打印当前账号池各账号的配额状态，不执行任何切换或退出动作。

.PARAMETER DryRun
    演练模式，仅计算选号与链路，不退出或切换。
#>
[CmdletBinding()]
param(
    [double]$Threshold = 5.0,
    [string]$Target = '',
    [switch]$Force,
    [switch]$StatusOnly,
    [switch]$DryRun,
    [switch]$Watch,
    [switch]$StartDaemon,
    [switch]$StopDaemon
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PyScript = Join-Path $ScriptDir 'antigravity_smart_switch.py'

if (-not (Test-Path -LiteralPath $PyScript)) {
    # 尝试从安装目录定位
    $InstalledPy = Join-Path $env:LOCALAPPDATA 'Antigravity\launcher\antigravity_smart_switch.py'
    if (Test-Path -LiteralPath $InstalledPy) {
        $PyScript = $InstalledPy
    } else {
        throw "未找到核心脚本: $PyScript"
    }
}

if ($StopDaemon) {
    & python $PyScript --stop-watch
    exit $LASTEXITCODE
}

if ($StartDaemon) {
    $pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
    if (-not $pythonw) { $pythonw = 'python.exe' }
    Start-Process -FilePath $pythonw -ArgumentList @($PyScript, '--watch', '--threshold', [string]$Threshold) -WindowStyle Hidden
    Write-Host "【小老虎自动续航守护神】已在后台静默启动！(阈值: <= $Threshold%)" -ForegroundColor Green
    exit 0
}

$pyArgs = @($PyScript)

if ($StatusOnly) {
    $pyArgs += '--status'
} elseif ($Watch) {
    $pyArgs += @('--watch', '--threshold', [string]$Threshold)
} else {
    $pyArgs += @('--threshold', [string]$Threshold)
    if (-not [string]::IsNullOrWhiteSpace($Target)) {
        $pyArgs += @('--target', $Target)
    }
    if ($Force) {
        $pyArgs += '--force'
    }
    if ($DryRun) {
        $pyArgs += '--dry-run'
    }
}

& python @pyArgs
exit $LASTEXITCODE
