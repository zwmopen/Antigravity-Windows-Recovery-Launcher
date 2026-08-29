[CmdletBinding()]
param()

# Antigravity private proxy supervisor
# Version: 1.6.0
# Purpose: run one private Mihomo listener for Antigravity only.
# The executable core is ASCII-only for Windows PowerShell 5.1 compatibility.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeRoot = Join-Path $env:LOCALAPPDATA 'Antigravity'
$MihomoPath = 'D:\Program Files\Clash Verge\verge-mihomo.exe'
$AntigravityPath = Join-Path $env:LOCALAPPDATA 'Programs\antigravity\Antigravity.exe'
$ClashRoot = Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev'
$ProfilesIndex = Join-Path $ClashRoot 'profiles.yaml'
$ProfilesRoot = Join-Path $ClashRoot 'profiles'
$ProxyRoot = Join-Path $RuntimeRoot 'private-proxy'
$ConfigPath = Join-Path $ProxyRoot 'mihomo-antigravity.yaml'
$StatePath = Join-Path $ProxyRoot 'supervisor-state.json'
$PidPath = Join-Path $ProxyRoot 'mihomo.pid'
$LogPath = Join-Path $ProxyRoot 'supervisor.log'
$Port = 17897
$ProxyUrl = 'http://127.0.0.1:17897'
$TargetAlias = 'ANTIGRAVITY-GLOBAL-UPSTREAM'
$UpstreamPort = 7897
$SettingsPath = Join-Path $env:APPDATA 'Antigravity\User\settings.json'
$SettingsBackupRoot = Join-Path $RuntimeRoot 'settings-backups'
$LauncherPath = Join-Path $ScriptRoot 'Antigravity-Recovery-Launcher.exe'
$ShortcutBackupRoot = Join-Path $RuntimeRoot 'shortcut-backups'

function Write-SafeLog {
    param(
        [Parameter(Mandatory = $true)][string]$Event,
        [hashtable]$Values = @{}
    )

    $parts = @((Get-Date).ToString('o'), $Event)
    foreach ($key in ($Values.Keys | Sort-Object)) {
        $value = [string]$Values[$key]
        if ($key -match '(?i)password|passwd|token|secret|uuid|url|server|host|path|config|command') {
            $value = '<redacted>'
        }
        $value = $value -replace '[\r\n\t ]+', '_'
        $parts += ($key + '=' + $value)
    }
    Add-Content -LiteralPath $LogPath -Value ($parts -join ' ') -Encoding UTF8
}

function Stop-WithMessage {
    param([Parameter(Mandatory = $true)][string]$Event)

    Write-SafeLog -Event $Event
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
        [System.Windows.Forms.MessageBox]::Show(
            'Antigravity private proxy is not ready. Check the local supervisor log.',
            'Antigravity launch stopped',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    } catch {
        # A visible message is best effort only. The safe log is authoritative.
    }
    throw $Event
}

function Test-LocalPort {
    param([int]$TestPort)

    $client = New-Object System.Net.Sockets.TcpClient
    $async = $null
    try {
        $async = $client.BeginConnect('127.0.0.1', $TestPort, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(1500)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $async -and $null -ne $async.AsyncWaitHandle) {
            $async.AsyncWaitHandle.Close()
        }
        $client.Close()
    }
}

function Get-FileSha256 {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    $stream = $null
    $sha = $null
    try {
        $stream = [System.IO.File]::OpenRead($LiteralPath)
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $bytes = $sha.ComputeHash($stream)
        return ([System.BitConverter]::ToString($bytes) -replace '-', '')
    } finally {
        if ($null -ne $sha) {
            $sha.Dispose()
        }
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }
}

function Get-ListeningOwner {
    param([int]$ListenPort)

    try {
        return @(Get-NetTCPConnection -State Listen -LocalPort $ListenPort -ErrorAction Stop | Select-Object -First 1)
    } catch {
        return @()
    }
}

function Get-OwnedMihomoProcess {
    if (-not (Test-Path -LiteralPath $PidPath)) {
        return $null
    }

    $pidText = (Get-Content -LiteralPath $PidPath -Raw).Trim()
    $ownedPid = 0
    if (-not [int]::TryParse($pidText, [ref]$ownedPid)) {
        return $null
    }

    $processInfo = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $ownedPid) -ErrorAction SilentlyContinue
    if ($null -eq $processInfo) {
        return $null
    }
    if ($processInfo.Name -notmatch '^verge-mihomo(\.exe)?$') {
        return $null
    }

    $commandLine = [string]$processInfo.CommandLine
    if ($commandLine -notmatch '(?i)mihomo-antigravity\.yaml') {
        return $null
    }
    return $processInfo
}

function Get-MihomoProcessForPort {
    param([int]$ListenPort)

    $owner = @(Get-ListeningOwner -ListenPort $ListenPort)
    if ($owner.Count -eq 0) { return $null }
    $processInfo = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + [int]$owner[0].OwningProcess) -ErrorAction SilentlyContinue
    if ($null -eq $processInfo -or $processInfo.Name -notmatch '^verge-mihomo(\.exe)?$') { return $null }
    if ([string]$processInfo.CommandLine -notmatch '(?i)mihomo-antigravity\.yaml') { return $null }
    return $processInfo
}

function Stop-OwnedMihomo {
    $owned = Get-OwnedMihomoProcess
    if ($null -ne $owned) {
        Stop-Process -Id ([int]$owned.ProcessId) -Force -ErrorAction SilentlyContinue
        Write-SafeLog -Event 'proxy_stopped' -Values @{ pid = [int]$owned.ProcessId }
    }
    Remove-Item -LiteralPath $PidPath -Force -ErrorAction SilentlyContinue
}

function Write-PrivateConfig {
    param([Parameter(Mandatory = $true)][string]$ProfileId)

    New-Item -ItemType Directory -Path $ProxyRoot -Force | Out-Null
    $configLines = @(
        '# Generated by Antigravity-ProxySupervisor.ps1',
        '# Do not edit manually. Upstream: existing local Clash Verge proxy.',
        'mixed-port: 17897',
        'allow-lan: false',
        'bind-address: 127.0.0.1',
        'mode: rule',
        'log-level: silent',
        'ipv6: false',
        'tun:',
        '  enable: false',
        'proxies:',
        ('  - name: ' + $TargetAlias),
        '    type: http',
        '    server: 127.0.0.1',
        ('    port: ' + $UpstreamPort),
        'proxy-groups:',
        '  - name: ANTIGRAVITY-ROUTE',
        '    type: select',
        '    proxies:',
        ('      - ' + $TargetAlias),
        'rules:',
        '  - MATCH,ANTIGRAVITY-ROUTE'
    )

    $tempPath = Join-Path $ProxyRoot 'mihomo-antigravity.yaml.tmp'
    Set-Content -LiteralPath $tempPath -Value $configLines -Encoding UTF8
    Move-Item -LiteralPath $tempPath -Destination $ConfigPath -Force

    $hash = Get-FileSha256 -LiteralPath $ConfigPath
    return @{
        ProfileId = $ProfileId
        ConfigHash = $hash
    }
}

function Test-PrivateConfig {
    $output = @(& $MihomoPath -t -d $ProxyRoot -f $ConfigPath 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-SafeLog -Event 'config_test_failed' -Values @{ code = $exitCode }
        Stop-WithMessage -Event 'config_test_failed'
    }
    Write-SafeLog -Event 'config_test_passed'
}

function Start-OrReuseMihomo {
    param(
        [Parameter(Mandatory = $true)][string]$ExpectedConfigHash,
        [bool]$ForceRestart = $false
    )

    $owner = @(Get-ListeningOwner -ListenPort $Port)
    $owned = Get-OwnedMihomoProcess
    if ($owner.Count -gt 0 -and $null -eq $owned) {
        $owned = Get-MihomoProcessForPort -ListenPort $Port
        if ($null -ne $owned) {
            Set-Content -LiteralPath $PidPath -Value ([string]$owned.ProcessId) -Encoding ASCII
            Write-SafeLog -Event 'proxy_ownership_recovered' -Values @{ pid = [int]$owned.ProcessId; port = $Port }
        }
    }
    if ($owner.Count -gt 0 -and ($null -eq $owned -or [int]$owner[0].OwningProcess -ne [int]$owned.ProcessId)) {
        Stop-WithMessage -Event 'private_port_already_owned'
    }

    $reuse = $false
    $loadedHash = ''
    if (Test-Path -LiteralPath $StatePath) {
        try {
            $loadedHash = [string]((Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json).config_hash)
        } catch {
            $loadedHash = ''
        }
    }
    if ($null -ne $owned -and ($loadedHash -ne $ExpectedConfigHash -or $ForceRestart)) {
        if ($ForceRestart) {
            Write-SafeLog -Event 'proxy_restart_requested_after_location_error'
        }
        Stop-OwnedMihomo
        $owned = $null
        for ($i = 0; $i -lt 20 -and (Test-LocalPort -TestPort $Port); $i++) {
            Start-Sleep -Milliseconds 250
        }
    }
    if ($null -ne $owned -and (Test-LocalPort -TestPort $Port)) {
        $reuse = $true
    } elseif ($null -ne $owned) {
        Stop-OwnedMihomo
    }

    if (-not $reuse) {
        $started = Start-Process -FilePath $MihomoPath -ArgumentList @('-d', $ProxyRoot, '-f', $ConfigPath) -WorkingDirectory $ProxyRoot -WindowStyle Hidden -PassThru
        Set-Content -LiteralPath $PidPath -Value ([string]$started.Id) -Encoding ASCII
        for ($i = 0; $i -lt 60; $i++) {
            Start-Sleep -Milliseconds 500
            if ($started.HasExited) {
                Write-SafeLog -Event 'proxy_process_exited' -Values @{ code = $started.ExitCode }
                Stop-WithMessage -Event 'proxy_process_exited'
            }
            if (Test-LocalPort -TestPort $Port) {
                break
            }
        }
        if (-not (Test-LocalPort -TestPort $Port)) {
            Stop-WithMessage -Event 'proxy_port_timeout'
        }
        Write-SafeLog -Event 'proxy_started' -Values @{ pid = $started.Id; port = $Port }
    } else {
        Write-SafeLog -Event 'proxy_reused' -Values @{ pid = [int]$owned.ProcessId; port = $Port }
    }
}

function Get-HttpStatusThroughProxy {
    param([Parameter(Mandatory = $true)][string]$Uri)

    $request = $null
    $response = $null
    try {
        $request = [System.Net.HttpWebRequest]::Create($Uri)
        $request.Proxy = New-Object -TypeName System.Net.WebProxy -ArgumentList @($ProxyUrl)
        $request.Timeout = 20000
        $request.ReadWriteTimeout = 20000
        $request.Method = 'GET'
        $response = $request.GetResponse()
        return [int]$response.StatusCode
    } catch [System.Net.WebException] {
        if ($null -ne $_.Exception.Response) {
            return [int]$_.Exception.Response.StatusCode
        }
        return 0
    } catch {
        return 0
    } finally {
        if ($null -ne $response) {
            $response.Close()
        }
    }
}

function Test-GoogleConnectivity {
    $googleStatus = Get-HttpStatusThroughProxy -Uri 'https://www.google.com/generate_204'
    $apiStatus = Get-HttpStatusThroughProxy -Uri 'https://generativelanguage.googleapis.com/'
    if ($googleStatus -le 0 -or $apiStatus -le 0) {
        Write-SafeLog -Event 'google_connectivity_failed' -Values @{ google = $googleStatus; api = $apiStatus }
        Stop-WithMessage -Event 'google_connectivity_failed'
    }
    Write-SafeLog -Event 'google_connectivity_passed' -Values @{ google = $googleStatus; api = $apiStatus }
    return @{
        GoogleStatus = $googleStatus
        ApiStatus = $apiStatus
    }
}

function Sync-AntigravityProxySetting {
    if (-not (Test-Path -LiteralPath $SettingsPath)) {
        Stop-WithMessage -Event 'settings_missing'
    }

    try {
        $settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
    } catch {
        Stop-WithMessage -Event 'settings_invalid_json'
    }

    $changed = $false
    if ($settings.PSObject.Properties.Name -notcontains 'http.proxy') {
        $settings | Add-Member -NotePropertyName 'http.proxy' -NotePropertyValue $ProxyUrl
        $changed = $true
    } elseif ([string]$settings.'http.proxy' -ne $ProxyUrl) {
        $settings.'http.proxy' = $ProxyUrl
        $changed = $true
    }

    if ($settings.PSObject.Properties.Name -notcontains 'http.proxySupport') {
        $settings | Add-Member -NotePropertyName 'http.proxySupport' -NotePropertyValue 'override'
        $changed = $true
    } elseif ([string]$settings.'http.proxySupport' -ne 'override') {
        $settings.'http.proxySupport' = 'override'
        $changed = $true
    }

    if ($changed) {
        New-Item -ItemType Directory -Path $SettingsBackupRoot -Force | Out-Null
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $backupPath = Join-Path $SettingsBackupRoot ('settings-before-supervisor-sync-' + $stamp + '.json')
        Copy-Item -LiteralPath $SettingsPath -Destination $backupPath
        $tempSettingsPath = $SettingsPath + '.antigravity-proxy.tmp'
        $settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $tempSettingsPath -Encoding UTF8
        Move-Item -LiteralPath $tempSettingsPath -Destination $SettingsPath -Force
        Write-SafeLog -Event 'settings_proxy_synced'
    } else {
        Write-SafeLog -Event 'settings_proxy_verified'
    }
}

function Restore-ProcessEnvironment {
    param([hashtable]$Previous)

    foreach ($name in @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY')) {
        $oldValue = $Previous[$name]
        if ($null -eq $oldValue) {
            Remove-Item -Path ('Env:' + $name) -ErrorAction SilentlyContinue
        } else {
            Set-Item -Path ('Env:' + $name) -Value $oldValue
        }
    }
}

function Repair-DesktopShortcut {
    # Cockpit Tools may replace the desktop entry while switching accounts.
    # Keep one stable user entry that always runs the self-healing launcher.
    try {
        if (-not (Test-Path -LiteralPath $LauncherPath)) {
            Write-SafeLog -Event 'desktop_shortcut_launcher_missing'
            return
        }

        $desktop = [Environment]::GetFolderPath('Desktop')
        $shortcutPath = Join-Path $desktop 'Antigravity.lnk'
        $shell = New-Object -ComObject WScript.Shell
        $needsRepair = $true

        if (Test-Path -LiteralPath $shortcutPath) {
            $current = $shell.CreateShortcut($shortcutPath)
            $needsRepair = -not (
                ([string]$current.TargetPath -ieq $LauncherPath) -and
                [string]::IsNullOrWhiteSpace([string]$current.Arguments)
            )
        }

        if (-not $needsRepair) {
            Write-SafeLog -Event 'desktop_shortcut_verified'
            return
        }

        if (Test-Path -LiteralPath $shortcutPath) {
            New-Item -ItemType Directory -Path $ShortcutBackupRoot -Force | Out-Null
            $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
            Copy-Item -LiteralPath $shortcutPath -Destination (Join-Path $ShortcutBackupRoot ('Antigravity-before-self-heal-' + $stamp + '.lnk'))
        }

        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $LauncherPath
        $shortcut.Arguments = ''
        $shortcut.WorkingDirectory = $ScriptRoot
        $shortcut.IconLocation = $AntigravityPath + ',0'
        $shortcut.Description = 'Antigravity self-healing launcher'
        $shortcut.Save()
        Write-SafeLog -Event 'desktop_shortcut_repaired'
    } catch {
        # A shortcut repair failure must not prevent an otherwise healthy app
        # startup. The event is enough for the next diagnostic pass.
        Write-SafeLog -Event 'desktop_shortcut_repair_failed'
    }
}

function Stop-ExistingAntigravity {
    # Cockpit Tools can relaunch Antigravity without this launcher's proxy
    # environment. Electron then keeps that broken single instance alive and
    # later shortcut clicks are routed to the black window. Always replace an
    # existing instance with one started by this launcher.
    $normalizedPath = [System.IO.Path]::GetFullPath($AntigravityPath)
    $existing = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -ieq 'Antigravity.exe' -and
        -not [string]::IsNullOrWhiteSpace([string]$_.ExecutablePath) -and
        [System.IO.Path]::GetFullPath([string]$_.ExecutablePath) -ieq $normalizedPath
    })
    if ($existing.Count -eq 0) {
        return
    }

    foreach ($processInfo in $existing) {
        $process = Get-Process -Id $processInfo.ProcessId -ErrorAction SilentlyContinue
        if ($null -ne $process -and $process.MainWindowHandle -ne 0) {
            try {
                if (-not $process.HasExited) {
                    $null = $process.CloseMainWindow()
                }
            } catch {
                # Exiting between discovery and CloseMainWindow is success.
            }
        }
    }

    for ($i = 0; $i -lt 12; $i++) {
        Start-Sleep -Milliseconds 250
        $remaining = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -ieq 'Antigravity.exe' -and
            -not [string]::IsNullOrWhiteSpace([string]$_.ExecutablePath) -and
            [System.IO.Path]::GetFullPath([string]$_.ExecutablePath) -ieq $normalizedPath
        })
        if ($remaining.Count -eq 0) {
            break
        }
    }

    $remaining = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -ieq 'Antigravity.exe' -and
        -not [string]::IsNullOrWhiteSpace([string]$_.ExecutablePath) -and
        [System.IO.Path]::GetFullPath([string]$_.ExecutablePath) -ieq $normalizedPath
    })
    foreach ($processInfo in $remaining) {
        Stop-Process -Id $processInfo.ProcessId -Force -ErrorAction SilentlyContinue
    }

    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 250
        $stillRunning = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -ieq 'Antigravity.exe' -and
            -not [string]::IsNullOrWhiteSpace([string]$_.ExecutablePath) -and
            [System.IO.Path]::GetFullPath([string]$_.ExecutablePath) -ieq $normalizedPath
        })
        if ($stillRunning.Count -eq 0) {
            Write-SafeLog -Event 'existing_antigravity_stopped' -Values @{ count = $existing.Count }
            return
        }
    }

    Stop-WithMessage -Event 'existing_antigravity_stop_failed'
}

function Test-PriorLocationError {
    $languageLog = Join-Path $env:APPDATA 'Antigravity\logs\language_server.log'
    if (-not (Test-Path -LiteralPath $languageLog)) {
        return $false
    }
    try {
        $tail = @(Get-Content -LiteralPath $languageLog -Tail 400 -ErrorAction Stop)
        return [bool]($tail -match 'User location is not supported')
    } catch {
        return $false
    }
}

function Wait-AntigravityReady {
    param(
        [Parameter(Mandatory = $true)][int]$MainPid,
        [Parameter(Mandatory = $true)][datetime]$LaunchTime
    )

    $languageLog = Join-Path $env:APPDATA 'Antigravity\logs\language_server.log'
    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 1
        $main = Get-Process -Id $MainPid -ErrorAction SilentlyContinue
        if ($null -eq $main) {
            Stop-WithMessage -Event 'antigravity_exited_during_startup'
        }

        $initialized = $false
        if (Test-Path -LiteralPath $languageLog) {
            $logItem = Get-Item -LiteralPath $languageLog -ErrorAction SilentlyContinue
            if ($null -ne $logItem -and $logItem.LastWriteTime -ge $LaunchTime.AddSeconds(-2)) {
                $tail = @(Get-Content -LiteralPath $languageLog -Tail 300 -ErrorAction SilentlyContinue)
                $initialized = [bool]($tail -match 'initialized server successfully')
            }
        }

        if ($initialized -and $main.MainWindowHandle -ne 0 -and $main.Responding) {
            $languageServer = @(Get-CimInstance Win32_Process -Filter ("ParentProcessId = " + $MainPid) -ErrorAction SilentlyContinue | Where-Object { $_.Name -ieq 'language_server.exe' } | Select-Object -First 1)
            if ($languageServer.Count -gt 0) {
                $proxyConnections = @(Get-NetTCPConnection -OwningProcess $languageServer[0].ProcessId -State Established -ErrorAction SilentlyContinue | Where-Object { $_.RemoteAddress -eq '127.0.0.1' -and $_.RemotePort -eq $Port })
                if ($proxyConnections.Count -gt 0) {
                    Write-SafeLog -Event 'antigravity_ready' -Values @{ pid = $MainPid; language_pid = $languageServer[0].ProcessId; proxy_connections = $proxyConnections.Count }
                    return @{
                        LanguageServerPid = [int]$languageServer[0].ProcessId
                        ProxyConnections = $proxyConnections.Count
                    }
                }
            }
        }
    }

    Stop-ExistingAntigravity
    Stop-WithMessage -Event 'antigravity_startup_health_timeout'
}

if (-not (Test-Path -LiteralPath $MihomoPath)) {
    Stop-WithMessage -Event 'mihomo_missing'
}
if (-not (Test-Path -LiteralPath $AntigravityPath)) {
    Stop-WithMessage -Event 'antigravity_missing'
}

New-Item -ItemType Directory -Path $ProxyRoot -Force | Out-Null
Repair-DesktopShortcut
$forceProxyRestart = Test-PriorLocationError
if (-not (Test-LocalPort -TestPort $UpstreamPort)) {
    Stop-WithMessage -Event 'global_upstream_not_ready'
}
$configState = Write-PrivateConfig -ProfileId 'global-7897'
Test-PrivateConfig
Start-OrReuseMihomo -ExpectedConfigHash $configState.ConfigHash -ForceRestart $forceProxyRestart
$connectivity = Test-GoogleConnectivity
Sync-AntigravityProxySetting
Stop-ExistingAntigravity

$previousEnvironment = @{}
foreach ($name in @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY')) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

try {
    $env:HTTP_PROXY = $ProxyUrl
    $env:HTTPS_PROXY = $ProxyUrl
    $env:ALL_PROXY = $ProxyUrl
    $env:NO_PROXY = 'localhost,127.0.0.1,::1'

    $arguments = @(
        '--proxy-server=' + $ProxyUrl,
        '--proxy-bypass-list=localhost;127.0.0.1;[::1]'
    )
    $launchTime = Get-Date
    $antigravity = Start-Process -FilePath $AntigravityPath -ArgumentList $arguments -WorkingDirectory (Split-Path -Parent $AntigravityPath) -PassThru
    Write-SafeLog -Event 'antigravity_started' -Values @{ pid = $antigravity.Id; port = $Port }
} finally {
    Restore-ProcessEnvironment -Previous $previousEnvironment
}

$readiness = Wait-AntigravityReady -MainPid $antigravity.Id -LaunchTime $launchTime

$state = [ordered]@{
    version = '1.6.0'
    status = 'ready'
    started_at = (Get-Date).ToString('o')
    profile_id = $configState.ProfileId
    config_hash = $configState.ConfigHash
    target_alias = $TargetAlias
    private_port = $Port
    mihomo_pid = [int](Get-Content -LiteralPath $PidPath -Raw).Trim()
    google_status = $connectivity.GoogleStatus
    generativelanguage_status = $connectivity.ApiStatus
    antigravity_pid = [int]$antigravity.Id
    language_server_pid = $readiness.LanguageServerPid
    language_proxy_connections = $readiness.ProxyConnections
}
$state | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding UTF8
