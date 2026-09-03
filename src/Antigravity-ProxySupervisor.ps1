[CmdletBinding()]
param(
    [string]$TargetNodeOverride = '',
    [string]$ExpectedEgressCountryOverride = '',
    [ValidateSet('Startup', 'NetworkFailure', 'LocationFailure')]
    [string]$RecoveryReason = 'Startup',
    [switch]$PolicyTest
)

# Antigravity private proxy supervisor
# Version: 2.7.0
# Purpose: run one private Mihomo listener for Antigravity only.
# The executable core is ASCII-only for Windows PowerShell 5.1 compatibility.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeRoot = Join-Path $env:LOCALAPPDATA 'Antigravity'
$LocalizationExtensionPath = Join-Path $ScriptRoot 'localization-extension'
$LocalizationManifestPath = Join-Path $LocalizationExtensionPath 'manifest.json'
$LocalizationLoaderPath = Join-Path $ScriptRoot 'Antigravity-CdpLocalizationLoader.exe'
$AgyPath = Join-Path $ScriptRoot 'tools\agy\agy.exe'
$LocalizationDisabledMarkerPath = Join-Path $RuntimeRoot 'localization-extension-disabled.flag'
$LocalizationPendingMarkerPath = Join-Path $RuntimeRoot 'localization-extension-pending.flag'
$MihomoPath = ''
$AntigravityPath = Join-Path $env:LOCALAPPDATA 'Programs\antigravity\Antigravity.exe'
$ClashRoot = Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev'
$ProfilesIndex = Join-Path $ClashRoot 'profiles.yaml'
$ProfilesRoot = Join-Path $ClashRoot 'profiles'
$ActiveClashConfig = Join-Path $ClashRoot 'clash-verge.yaml'
$PartyRoot = Join-Path $env:APPDATA 'mihomo-party'
$PartyProfilesIndex = Join-Path $PartyRoot 'profile.yaml'
$PartyProfilesRoot = Join-Path $PartyRoot 'profiles'
$AccountsPath = Join-Path $env:USERPROFILE '.antigravity_cockpit\accounts.json'
$ProxyRoot = Join-Path $RuntimeRoot 'private-proxy'
$ConfigPath = Join-Path $ProxyRoot 'mihomo-antigravity.yaml'
$StatePath = Join-Path $ProxyRoot 'supervisor-state.json'
$FailoverStatePath = Join-Path $ProxyRoot 'failover-state.json'
$SubscriptionReportPath = Join-Path $ProxyRoot 'subscription-report.json'
$FixedUpstreamPath = Join-Path $ProxyRoot 'fixed-upstream.json'
$PidPath = Join-Path $ProxyRoot 'mihomo.pid'
$LogPath = Join-Path $ProxyRoot 'supervisor.log'
$Port = 17897
$ProxyUrl = 'http://127.0.0.1:17897'
$TargetNodeMatch = if ([string]::IsNullOrWhiteSpace($TargetNodeOverride)) { '' } else { $TargetNodeOverride.Trim() }
$TargetNodeExactMatch = -not [string]::IsNullOrWhiteSpace($TargetNodeOverride)
$TargetAlias = 'ANTIGRAVITY-VERIFIED-CANDIDATE'
$FixedUpstreamAlias = 'ANTIGRAVITY-FIXED-UPSTREAM'
$ExpectedEgressCountry = if ([string]::IsNullOrWhiteSpace($ExpectedEgressCountryOverride)) { '' } else { $ExpectedEgressCountryOverride.Trim().ToUpperInvariant() }
$CandidateCooldownMinutes = 20
$MaxSuccessHistory = 128
# Bound the live preflight after retired/cooldown state has been applied. The
# old value was applied while interleaving raw sources, so a large Japan-first
# prefix could consume the cap before the United States fallback was even
# discovered. Keep a bounded probe budget, but leave enough room for the
# current multi-subscription pool and apply it after state filtering.
$MaxCandidateCount = 96
$StopProcessTimeoutSeconds = 20
$ProbeTimeoutMs = 8000
$ModelProbeTimeoutSeconds = 90
$ModelProbePrompt = 'Reply with exactly OK. Do not call tools or modify files.'
$ModelProbeConfirmationCount = 1
$ConnectivityAttemptCount = if ($RecoveryReason -eq 'Startup') { 3 } else { 2 }
$JapanNodeMatch = ([char]0x65E5).ToString() + ([char]0x672C).ToString()
$UnitedStatesNodeMatch = ([char]0x7F8E).ToString() + ([char]0x56FD).ToString()
$LosAngelesNodeMatch = ([char]0x6D1B).ToString() + ([char]0x6749).ToString() + ([char]0x77F6).ToString()
$SettingsPath = Join-Path $env:APPDATA 'Antigravity\User\settings.json'
$SettingsBackupRoot = Join-Path $RuntimeRoot 'settings-backups'
$LauncherPath = Join-Path $ScriptRoot 'Antigravity-Recovery-Launcher.exe'
$ShortcutBackupRoot = Join-Path $RuntimeRoot 'shortcut-backups'
$DesktopShortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Antigravity 启动器.lnk'
$StartMenuShortcutPath = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Antigravity 启动器.lnk'
$CanonicalLauncherPath = Join-Path $env:LOCALAPPDATA 'Antigravity\launcher\Antigravity-Recovery-Launcher.exe'
$SupervisorMutex = $null
$script:RunStartedAt = Get-Date
$script:DiscoveredCandidateCount = 0
$script:CandidateIndex = 0
$script:CandidateTotal = 0
$script:EligibleCandidateCount = 0
$script:CurrentFailoverState = $null
$script:CurrentConfigHash = ''
$script:LastGoogleStatus = 0
$script:LastApiStatus = 0
$script:LastOAuthStatus = 0
$script:LastEgressCountry = ''
$script:LastModelProbeState = 'not_run'
$script:LocalizationMode = ''
$script:LaunchedAntigravityPid = 0
$script:LaunchedLanguageServerPid = 0
$script:LaunchedProxyConnections = 0
$script:FailureStateWriting = $false
$script:SubscriptionInventory = $null
$script:FixedUpstream = $null
$script:AttemptedCandidateIds = @{}
$script:AttemptedCandidateFailureKinds = @{}
$script:LastRunStatus = 'running'
$script:RunFinishedAt = $null
$script:LastProbeRttMs = 0
$script:LastSmartScore = 0

function Write-SafeLog {
    param(
        [Parameter(Mandatory = $true)][string]$Event,
        [hashtable]$Values = @{},
        [switch]$PassThru
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
    $line = $parts -join ' '
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $share = [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete

    # Logging is diagnostic only. It must never interrupt recovery after the
    # existing Antigravity process has already been stopped. Add-Content opens
    # the file with restrictive sharing and has caused real half-finished
    # recoveries when another diagnostic reader touched supervisor.log.
    for ($attempt = 0; $attempt -lt 5; $attempt++) {
        $stream = $null
        $writer = $null
        try {
            $parent = Split-Path -Parent $LogPath
            if (-not [string]::IsNullOrWhiteSpace($parent)) {
                [System.IO.Directory]::CreateDirectory($parent) | Out-Null
            }
            $stream = [System.IO.File]::Open(
                $LogPath,
                [System.IO.FileMode]::Append,
                [System.IO.FileAccess]::Write,
                $share)
            $writer = New-Object System.IO.StreamWriter($stream, $utf8)
            $writer.WriteLine($line)
            $writer.Flush()
            if ($PassThru) { return $true }
            return
        } catch {
            if ($attempt -lt 4) {
                Start-Sleep -Milliseconds (40 * ($attempt + 1))
            }
        } finally {
            if ($null -ne $writer) {
                $writer.Dispose()
            } elseif ($null -ne $stream) {
                $stream.Dispose()
            }
        }
    }

    # Keep a best-effort per-process breadcrumb without ever surfacing a
    # logging exception to the recovery state machine.
    try {
        $fallbackPath = $LogPath + '.' + $PID + '.fallback'
        [System.IO.File]::AppendAllText($fallbackPath, $line + [Environment]::NewLine, $utf8)
    } catch { }
    if ($PassThru) { return $false }
}

function Save-SupervisorFailureState {
    param([Parameter(Mandatory = $true)][string]$Event)

    # A failed run must replace the previous ready snapshot. Otherwise a
    # caller can mistake yesterday's successful run for the current result
    # after every candidate has failed. This writer is deliberately best
    # effort: failure reporting must never hide the original failure event.
    if ($script:FailureStateWriting) { return $false }
    $script:FailureStateWriting = $true
    try {
        New-Item -ItemType Directory -Path $ProxyRoot -Force | Out-Null
        $mihomoPid = 0
        try {
            $owned = Get-OwnedMihomoProcess
            if ($null -ne $owned) { $mihomoPid = [int]$owned.ProcessId }
        } catch { }

        $retiredCount = 0
        $verifiedCount = 0
        try {
            if ($null -ne $script:CurrentFailoverState) {
                $retiredCount = @(Get-RetiredNodeEntries -State $script:CurrentFailoverState).Count
                $verifiedCount = @(Get-SuccessfulNodeEntries -State $script:CurrentFailoverState).Count
            }
        } catch { }

        $localizationEnabled = -not (Test-Path -LiteralPath $LocalizationDisabledMarkerPath)
        $failureState = [ordered]@{
            version = '2.7.0'
            status = 'failed'
            started_at = $script:RunStartedAt.ToString('o')
            finished_at = (Get-Date).ToString('o')
            failure_event = $Event
            last_error = $Event
            profile_id = 'active-clash-runtime'
            target_alias = $TargetAlias
            target_node = 'CURRENT-VERIFIED-FAILOVER-CANDIDATE'
            active_node_id = ''
            active_source_id = ''
            candidate_count = [int]$script:DiscoveredCandidateCount
            eligible_candidate_count = [int]$script:EligibleCandidateCount
            candidate_index = [int]$script:CandidateIndex
            candidate_total = [int]$script:CandidateTotal
            config_hash = ''
            retired_candidate_count = $retiredCount
            verified_candidate_count = $verifiedCount
            recovery_reason = $RecoveryReason
            private_port = $Port
            mihomo_pid = $mihomoPid
            google_status = [int]$script:LastGoogleStatus
            generativelanguage_status = [int]$script:LastApiStatus
            oauth_status = [int]$script:LastOAuthStatus
            egress_country = $script:LastEgressCountry
            real_model_probe = $script:LastModelProbeState
            localization_enabled = $localizationEnabled
            localization_mode = $script:LocalizationMode
            antigravity_pid = [int]$script:LaunchedAntigravityPid
            language_server_pid = [int]$script:LaunchedLanguageServerPid
            language_proxy_connections = [int]$script:LaunchedProxyConnections
            subscription_report = $SubscriptionReportPath
        }
        $tempPath = $StatePath + '.tmp'
        $failureState | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tempPath -Encoding UTF8
        Move-Item -LiteralPath $tempPath -Destination $StatePath -Force
        return $true
    } catch {
        try { Write-SafeLog -Event 'failure_state_write_failed' -Values @{ error_type = $_.Exception.GetType().Name } } catch { }
        return $false
    } finally {
        $script:FailureStateWriting = $false
    }
}

function Convert-SourceEpochToUtc {
    param([string]$Value)

    $number = 0L
    if ([string]::IsNullOrWhiteSpace($Value) -or
        -not [int64]::TryParse($Value.Trim(), [Globalization.NumberStyles]::Integer,
            [Globalization.CultureInfo]::InvariantCulture, [ref]$number)) {
        return $null
    }
    if ($number -gt 100000000000) {
        $number = [int64]($number / 1000)
    }
    try {
        return ([datetime]'1970-01-01T00:00:00Z').ToUniversalTime().AddSeconds($number)
    } catch {
        return $null
    }
}

function Get-IndexValue {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Pattern
    )

    $match = [regex]::Match($Text, $Pattern)
    if (-not $match.Success) { return '' }
    $value = $match.Groups[1].Value.Trim()
    if (($value.StartsWith("'") -and $value.EndsWith("'")) -or
        ($value.StartsWith('"') -and $value.EndsWith('"'))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if ($value -eq 'null') { return '' }
    return $value
}

function Get-IndexedRemoteProfiles {
    $entries = @()

    if (Test-Path -LiteralPath $ProfilesIndex) {
        try {
            $indexText = Get-Content -LiteralPath $ProfilesIndex -Raw -Encoding UTF8 -ErrorAction Stop
            foreach ($blockMatch in [regex]::Matches($indexText, '(?ms)^- uid:\s*.*?(?=^- uid:|\z)')) {
                $block = [string]$blockMatch.Value
                if ($block -notmatch '(?m)^\s{2}type:\s*remote\s*$') { continue }
                $uid = Get-IndexValue -Text $block -Pattern '(?m)^- uid:\s*([^\r\n#]+)'
                $fileName = Get-IndexValue -Text $block -Pattern '(?m)^\s{2}file:\s*([^\r\n#]+)'
                if ([string]::IsNullOrWhiteSpace($uid) -or [string]::IsNullOrWhiteSpace($fileName)) { continue }
                $displayName = Get-IndexValue -Text $block -Pattern '(?m)^\s{2}name:\s*([^\r\n#]+)'
                if ([string]::IsNullOrWhiteSpace($displayName)) { $displayName = 'Clash Verge subscription' }
                $updatedValue = Get-IndexValue -Text $block -Pattern '(?m)^\s{2}updated:\s*([^\r\n#]+)'
                $expireValue = Get-IndexValue -Text $block -Pattern '(?m)^\s{4}expire:\s*([^\r\n#]+)'
                $entries += [pscustomobject]@{
                    Family = 'clash-verge'
                    Id = $uid
                    FileName = $fileName
                    Path = Join-Path $ProfilesRoot $fileName
                    DisplayName = $displayName
                    UpdatedAt = Convert-SourceEpochToUtc -Value $updatedValue
                    ExpiresAt = Convert-SourceEpochToUtc -Value $expireValue
                }
            }
        } catch {
            Write-SafeLog -Event 'clash_verge_profile_index_unreadable'
        }
    }

    if (Test-Path -LiteralPath $PartyProfilesIndex) {
        try {
            $indexText = Get-Content -LiteralPath $PartyProfilesIndex -Raw -Encoding UTF8 -ErrorAction Stop
            foreach ($blockMatch in [regex]::Matches($indexText, '(?ms)^\s*- id:\s*.*?(?=^\s*- id:|^current:|\z)')) {
                $block = [string]$blockMatch.Value
                if ($block -notmatch '(?m)^\s{4}type:\s*remote\s*$') { continue }
                $id = Get-IndexValue -Text $block -Pattern '(?m)^\s*- id:\s*([^\r\n#]+)'
                if ([string]::IsNullOrWhiteSpace($id)) { continue }
                $displayName = Get-IndexValue -Text $block -Pattern '(?m)^\s{4}name:\s*([^\r\n#]+)'
                if ([string]::IsNullOrWhiteSpace($displayName)) { $displayName = 'Mihomo Party subscription' }
                $updatedValue = Get-IndexValue -Text $block -Pattern '(?m)^\s{4}updated:\s*([^\r\n#]+)'
                $expireValue = Get-IndexValue -Text $block -Pattern '(?m)^\s{6}expire:\s*([^\r\n#]+)'
                $entries += [pscustomobject]@{
                    Family = 'mihomo-party'
                    Id = $id
                    FileName = ($id + '.yaml')
                    Path = Join-Path $PartyProfilesRoot ($id + '.yaml')
                    DisplayName = $displayName
                    UpdatedAt = Convert-SourceEpochToUtc -Value $updatedValue
                    ExpiresAt = Convert-SourceEpochToUtc -Value $expireValue
                }
            }
        } catch {
            Write-SafeLog -Event 'mihomo_party_profile_index_unreadable'
        }
    }

    return @($entries)
}

function Test-IndexedProfileUsable {
    param([Parameter(Mandatory = $true)]$Profile)

    if (-not (Test-Path -LiteralPath ([string]$Profile.Path))) { return $false }
    if ($null -ne $Profile.ExpiresAt -and $Profile.ExpiresAt -le (Get-Date).ToUniversalTime()) {
        Write-SafeLog -Event 'subscription_profile_expired' -Values @{ source_name = [string]$Profile.DisplayName }
        return $false
    }
    return $true
}

function Resolve-MihomoPath {
    $knownPaths = @(
        (Join-Path $env:ProgramFiles 'Clash Verge\verge-mihomo.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Clash Verge\verge-mihomo.exe'),
        'D:\Program Files\Clash Verge\verge-mihomo.exe',
        (Join-Path $env:ProgramFiles 'Mihomo Party\resources\sidecar\mihomo.exe'),
        (Join-Path $env:ProgramFiles 'Mihomo Party\resources\sidecar\mihomo-windows-amd64.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\mihomo-party\resources\sidecar\mihomo.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\mihomo-party\resources\sidecar\mihomo-windows-amd64.exe'),
        'D:\Program Files\Mihomo Party\resources\sidecar\mihomo.exe',
        'D:\Program Files\Mihomo Party\resources\sidecar\mihomo-windows-amd64.exe',
        (Join-Path $env:ProgramFiles 'Flclash\flclash.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Flclash\flclash.exe')
    )
    foreach ($path in $knownPaths) {
        if (-not [string]::IsNullOrWhiteSpace($path) -and (Test-Path -LiteralPath $path)) {
            return $path
        }
    }

    # PATH discovery
    foreach ($cmdName in @('verge-mihomo.exe', 'mihomo.exe', 'mihomo-windows-amd64.exe', 'clash-meta.exe')) {
        $foundCmd = Get-Command -Name $cmdName -ErrorAction SilentlyContinue
        if ($null -ne $foundCmd -and -not [string]::IsNullOrWhiteSpace([string]$foundCmd.Source) -and (Test-Path -LiteralPath $foundCmd.Source)) {
            return [string]$foundCmd.Source
        }
    }

    # Registry discovery
    foreach ($registryRoot in @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )) {
        foreach ($entry in @(Get-ItemProperty -Path $registryRoot -ErrorAction SilentlyContinue | Where-Object {
            [string]$_.DisplayName -match 'Clash Verge|Mihomo Party|Flclash'
        })) {
            $installLocation = [string]$entry.InstallLocation
            if (-not [string]::IsNullOrWhiteSpace($installLocation)) {
                foreach ($subBin in @('verge-mihomo.exe', 'resources\sidecar\mihomo.exe', 'resources\sidecar\mihomo-windows-amd64.exe', 'mihomo.exe')) {
                    $candidate = Join-Path $installLocation $subBin
                    if (Test-Path -LiteralPath $candidate) { return $candidate }
                }
            }
        }
    }
    return ''
}

function Test-SafeLogFailureIsNonFatal {
    $originalLogPath = $script:LogPath
    $testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('antigravity-log-test-' + [guid]::NewGuid().ToString('N'))
    $testPath = Join-Path $testRoot 'locked.log'
    $lock = $null
    try {
        [System.IO.Directory]::CreateDirectory($testRoot) | Out-Null
        [System.IO.File]::WriteAllText($testPath, 'locked')
        $lock = [System.IO.File]::Open($testPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        $script:LogPath = $testPath
        $result = Write-SafeLog -Event 'logging_contention_test' -PassThru
        return ($result -eq $false)
    } catch {
        return $false
    } finally {
        $script:LogPath = $originalLogPath
        if ($null -ne $lock) { $lock.Dispose() }
        Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Stop-WithMessage {
    param([Parameter(Mandatory = $true)][string]$Event)

    Write-SafeLog -Event $Event
    $null = Save-SupervisorFailureState -Event $Event
    # The supervisor runs hidden under the GUI launcher. A MessageBox created
    # here can be invisible and block the child process forever, leaving the
    # launcher's progress window spinning. The GUI launcher owns user-facing
    # failure reporting; this process must terminate immediately.
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

function Get-StringSha256 {
    param([Parameter(Mandatory = $true)][string]$Text)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return (([System.BitConverter]::ToString($sha.ComputeHash($bytes)) -replace '-', '').Substring(0, 16))
    } finally {
        $sha.Dispose()
    }
}

function Get-CurrentAccountFingerprint {
    if (-not (Test-Path -LiteralPath $AccountsPath)) {
        return ''
    }

    try {
        $accounts = Get-Content -LiteralPath $AccountsPath -Raw -ErrorAction Stop | ConvertFrom-Json
        $accountId = [string]$accounts.current_account_id
        if ([string]::IsNullOrWhiteSpace($accountId)) {
            return ''
        }
        # Keep switching state isolated without persisting or logging the
        # account ID or email address itself.
        return Get-StringSha256 -Text $accountId
    } catch {
        return ''
    }
}

function New-EmptyFailoverState {
    return [pscustomobject]@{
        policy_version = 2
        account_fingerprint = Get-CurrentAccountFingerprint
        active_node_id = ''
        failed_nodes = @()
        retired_nodes = @()
        successful_nodes = @()
        last_switch_at = ''
    }
}

function Get-FailoverState {
    if (-not (Test-Path -LiteralPath $FailoverStatePath)) {
        return New-EmptyFailoverState
    }
    try {
        $state = Get-Content -LiteralPath $FailoverStatePath -Raw | ConvertFrom-Json
        foreach ($propertyName in @('failed_nodes', 'retired_nodes', 'successful_nodes')) {
            if ($null -eq $state.PSObject.Properties[$propertyName]) {
                $state | Add-Member -NotePropertyName $propertyName -NotePropertyValue @() -Force
            } else {
                $state.$propertyName = @($state.$propertyName)
            }
        }
        $currentFingerprint = Get-CurrentAccountFingerprint
        $storedFingerprint = ''
        if ($null -ne $state.PSObject.Properties['account_fingerprint']) {
            $storedFingerprint = [string]$state.account_fingerprint
        }
        if (-not [string]::IsNullOrWhiteSpace($currentFingerprint) -and
            $storedFingerprint -ne $currentFingerprint) {
            try {
                $stamp = Get-Date -Format 'yyyyMMdd-HHmmssfff'
                Copy-Item -LiteralPath $FailoverStatePath -Destination ($FailoverStatePath + '.before-account-' + $stamp + '.json') -Force
            } catch { }
            Write-SafeLog -Event 'failover_state_reset_for_account_change'
            return New-EmptyFailoverState
        }
        if ($null -eq $state.PSObject.Properties['account_fingerprint']) {
            $state | Add-Member -NotePropertyName account_fingerprint -NotePropertyValue $currentFingerprint -Force
        }
        $policyVersion = 1
        if ($null -ne $state.PSObject.Properties['policy_version']) {
            try { $policyVersion = [int]$state.policy_version } catch { $policyVersion = 1 }
        }
        if ($policyVersion -lt 2) {
            # Version 1 permanently retired every model_location result and
            # deleted successful history. Google forum evidence and local
            # repeated pass/fail evidence show that result can be transient.
            # Rehabilitate only those entries; deterministic invalid-config,
            # wrong-egress and structured non-OK retirements remain intact.
            try {
                $stamp = Get-Date -Format 'yyyyMMdd-HHmmssfff'
                Copy-Item -LiteralPath $FailoverStatePath -Destination ($FailoverStatePath + '.before-policy-v2-' + $stamp + '.json') -Force
            } catch { }
            $locationEntries = @($state.retired_nodes | Where-Object { [string]$_.reason -eq 'model_location' })
            $state.retired_nodes = @($state.retired_nodes | Where-Object { [string]$_.reason -ne 'model_location' })
            $cooldowns = @($state.failed_nodes | Where-Object {
                [string]$id = [string]$_.node_id
                -not [string]::IsNullOrWhiteSpace($id) -and @($locationEntries | Where-Object { [string]$_.node_id -eq $id }).Count -eq 0
            })
            $cooldownUntil = (Get-Date).AddMinutes($CandidateCooldownMinutes).ToString('o')
            foreach ($entry in $locationEntries) {
                $cooldowns += [pscustomobject]@{
                    node_id = [string]$entry.node_id
                    until = $cooldownUntil
                    reason = 'model_location'
                }
            }
            $state.failed_nodes = @($cooldowns)
            $activeId = [string]$state.active_node_id
            if (-not [string]::IsNullOrWhiteSpace($activeId) -and
                @($locationEntries | Where-Object { [string]$_.node_id -eq $activeId }).Count -gt 0 -and
                @($state.successful_nodes | Where-Object { [string]$_.node_id -eq $activeId }).Count -eq 0) {
                $activeRetirement = @($locationEntries | Where-Object { [string]$_.node_id -eq $activeId } | Select-Object -First 1)
                $state.successful_nodes = @([pscustomobject]@{
                    node_id = $activeId
                    source_id = if ($activeRetirement.Count -gt 0) { [string]$activeRetirement[0].source_id } else { '' }
                    last_passed_at = if ([string]::IsNullOrWhiteSpace([string]$state.last_switch_at)) { (Get-Date).ToString('o') } else { [string]$state.last_switch_at }
                    success_count = 1
                }) + @($state.successful_nodes)
            }
            $state | Add-Member -NotePropertyName policy_version -NotePropertyValue 2 -Force
            Write-SafeLog -Event 'failover_state_migrated_to_policy_v2' -Values @{ rehabilitated_location_nodes = $locationEntries.Count }
        }
        return $state
    } catch {
        Write-SafeLog -Event 'failover_state_invalid'
        return New-EmptyFailoverState
    }
}

function Get-ActiveCooldownEntries {
    param([Parameter(Mandatory = $true)]$State)

    $now = Get-Date
    $entries = @()
    foreach ($entry in @($State.failed_nodes)) {
        try {
            $until = [datetime]::Parse([string]$entry.until)
            if ($until -gt $now -and -not [string]::IsNullOrWhiteSpace([string]$entry.node_id)) {
                $entries += [pscustomobject]@{
                    node_id = [string]$entry.node_id
                    until = $until.ToString('o')
                    reason = [string]$entry.reason
                }
            }
        } catch { }
    }
    return @($entries)
}

function Get-RetiredNodeEntries {
    param([Parameter(Mandatory = $true)]$State)

    $entries = @()
    foreach ($entry in @($State.retired_nodes)) {
        try {
            $nodeId = [string]$entry.node_id
            if ([string]::IsNullOrWhiteSpace($nodeId)) { continue }
            $sourceId = ''
            if ($null -ne $entry.PSObject.Properties['source_id']) {
                $sourceId = [string]$entry.source_id
            }
            $entries += [pscustomobject]@{
                node_id = $nodeId
                retired_at = [string]$entry.retired_at
                reason = [string]$entry.reason
                source_id = $sourceId
            }
        } catch { }
    }
    return @($entries)
}

function Get-RetiredNodeIds {
    param([Parameter(Mandatory = $true)]$State)

    return @((Get-RetiredNodeEntries -State $State | Select-Object -ExpandProperty node_id))
}

function Get-SuccessfulNodeEntries {
    param([Parameter(Mandatory = $true)]$State)

    $entries = @()
    foreach ($entry in @($State.successful_nodes)) {
        try {
            $nodeId = [string]$entry.node_id
            if ([string]::IsNullOrWhiteSpace($nodeId)) { continue }
            $sourceId = ''
            if ($null -ne $entry.PSObject.Properties['source_id']) {
                $sourceId = [string]$entry.source_id
            }
            $successCount = 1
            if ($null -ne $entry.PSObject.Properties['success_count']) {
                try { $successCount = [Math]::Max(1, [int]$entry.success_count) } catch { $successCount = 1 }
            }
            $entries += [pscustomobject]@{
                node_id = $nodeId
                source_id = $sourceId
                last_passed_at = [string]$entry.last_passed_at
                success_count = $successCount
            }
        } catch { }
    }
    return @($entries)
}

function Test-NodeRetired {
    param(
        [Parameter(Mandatory = $true)]$State,
        [Parameter(Mandatory = $true)][string]$NodeId
    )

    return [bool](@(Get-RetiredNodeIds -State $State) -contains $NodeId)
}

function Add-NodeCooldown {
    param(
        [Parameter(Mandatory = $true)]$State,
        [Parameter(Mandatory = $true)][string]$NodeId,
        [Parameter(Mandatory = $true)][string]$Reason
    )

    if ([string]::IsNullOrWhiteSpace($NodeId) -or (Test-NodeRetired -State $State -NodeId $NodeId)) {
        return
    }
    $entries = @(Get-ActiveCooldownEntries -State $State | Where-Object { [string]$_.node_id -ne $NodeId })
    $entries += [pscustomobject]@{
        node_id = $NodeId
        until = (Get-Date).AddMinutes($CandidateCooldownMinutes).ToString('o')
        reason = $Reason
    }
    $State.failed_nodes = @($entries)
    Write-SafeLog -Event 'candidate_quarantined' -Values @{ node_id = $NodeId; reason = $Reason; minutes = $CandidateCooldownMinutes }
}

function Add-NodeRetirement {
    param(
        [Parameter(Mandatory = $true)]$State,
        [Parameter(Mandatory = $true)][string]$NodeId,
        [Parameter(Mandatory = $true)][string]$Reason,
        $Candidate = $null
    )

    if ([string]::IsNullOrWhiteSpace($NodeId)) { return }
    $sourceId = ''
    if ($null -ne $Candidate -and $null -ne $Candidate.PSObject.Properties['SourceId']) {
        $sourceId = [string]$Candidate.SourceId
    }
    $entries = @(Get-RetiredNodeEntries -State $State | Where-Object { [string]$_.node_id -ne $NodeId })
    $entries = @([pscustomobject]@{
        node_id = $NodeId
        retired_at = (Get-Date).ToString('o')
        reason = $Reason
        source_id = $sourceId
    }) + $entries
    $State.retired_nodes = @($entries)
    $State.failed_nodes = @(Get-ActiveCooldownEntries -State $State | Where-Object { [string]$_.node_id -ne $NodeId })
    $State.successful_nodes = @(Get-SuccessfulNodeEntries -State $State | Where-Object { [string]$_.node_id -ne $NodeId })
    Write-SafeLog -Event 'candidate_retired' -Values @{ node_id = $NodeId; reason = $Reason; source_id = $sourceId }
}

function Mark-NodeSuccess {
    param(
        [Parameter(Mandatory = $true)]$State,
        [Parameter(Mandatory = $true)]$Candidate
    )

    $nodeId = [string]$Candidate.Id
    if ([string]::IsNullOrWhiteSpace($nodeId) -or (Test-NodeRetired -State $State -NodeId $nodeId)) {
        return
    }
    $previous = @(Get-SuccessfulNodeEntries -State $State | Where-Object { [string]$_.node_id -eq $nodeId } | Select-Object -First 1)
    $successCount = 1
    if ($previous.Count -gt 0) {
        $successCount = [Math]::Max(1, [int]$previous[0].success_count) + 1
    }
    $rest = @(Get-SuccessfulNodeEntries -State $State | Where-Object { [string]$_.node_id -ne $nodeId })
    $newEntry = [pscustomobject]@{
        node_id = $nodeId
        source_id = [string]$Candidate.SourceId
        last_passed_at = (Get-Date).ToString('o')
        success_count = $successCount
        last_rtt_ms = [int]$script:LastProbeRttMs
    }
    $State.successful_nodes = @(@($newEntry) + $rest | Select-Object -First $MaxSuccessHistory)
    $State.failed_nodes = @(Get-ActiveCooldownEntries -State $State | Where-Object { [string]$_.node_id -ne $nodeId })
    Write-SafeLog -Event 'candidate_verified' -Values @{ node_id = $nodeId; source_id = [string]$Candidate.SourceId; success_count = $successCount; rtt_ms = [int]$script:LastProbeRttMs }
}

function Get-CandidateFailureDisposition {
    param([Parameter(Mandatory = $true)][string]$FailureKind)

    # Google can intermittently classify the same supported-region exit as
    # unsupported. A single model_location result therefore is not durable
    # evidence that the node is bad; cool it down and retain prior successes.
    if ($FailureKind -in @('model_non_ok', 'proxy_egress_wrong_country', 'config_invalid')) {
        return 'retire'
    }
    return 'cooldown'
}

function Get-CandidateFailureKind {
    param([Parameter(Mandatory = $true)]$ErrorRecord)

    $message = [string]$ErrorRecord
    try {
        if ($null -ne $ErrorRecord.Exception) {
            $message += ' ' + [string]$ErrorRecord.Exception.Message
        }
    } catch { }
    if ($message -match '(?i)model_location|user location is not supported|failed_precondition') { return 'model_location' }
    if ($message -match '(?i)model_non_ok') { return 'model_non_ok' }
    if ($message -match '(?i)proxy_egress_wrong_country') { return 'proxy_egress_wrong_country' }
    if ($message -match '(?i)config_test_failed') { return 'config_invalid' }
    if ($message -match '(?i)model_transport') { return 'model_transport' }
    return 'transient_network'
}

function Get-OrderedCandidates {
    param(
        [Parameter(Mandatory = $true)][object[]]$Candidates,
        [Parameter(Mandatory = $true)]$State,
        [string[]]$CooldownIds = @(),
        [switch]$IncludeCooldown
    )

    $retiredIds = @(Get-RetiredNodeIds -State $State)
    $historyById = @{}
    foreach ($entry in @(Get-SuccessfulNodeEntries -State $State)) {
        $historyById[[string]$entry.node_id] = $entry
    }

    $decorated = @()
    $discoveryIndex = 0
    foreach ($candidate in @($Candidates)) {
        $discoveryIndex++
        $nodeId = [string]$candidate.Id
        if ([string]::IsNullOrWhiteSpace($nodeId) -or $retiredIds -contains $nodeId) { continue }
        if (-not $IncludeCooldown -and $CooldownIds -contains $nodeId) { continue }

        $history = $null
        if ($historyById.ContainsKey($nodeId)) { $history = $historyById[$nodeId] }
        $isActive = [string]$State.active_node_id -eq $nodeId
        $isVerified = $null -ne $history -or $isActive
        $lastPassedTicks = [int64]0
        $successCount = 0
        if ($null -ne $history) {
            $successCount = [int]$history.success_count
            try { $lastPassedTicks = ([datetime]::Parse([string]$history.last_passed_at)).Ticks } catch { }
        } elseif ($isActive) {
            $successCount = 1
            try { $lastPassedTicks = ([datetime]::Parse([string]$State.last_switch_at)).Ticks } catch { }
        }
        $priority = 1000
        try { $priority = [int]$candidate.Priority } catch { }
        $regionRank = 100
        try { $regionRank = [int]$candidate.RegionRank } catch { }

        # Smart Pool: calculate SmartScore (0-1000)
        $smartScore = 0
        if ($isVerified) { $smartScore += 500 }
        if ($isActive) { $smartScore += 200 }
        if ($regionRank -eq 0) { $smartScore += 150 } else { $smartScore += 80 }
        $smartScore += [Math]::Min(150, ($successCount * 25))
        if ($lastPassedTicks -gt 0) {
            try {
                $passedDt = [datetime]([int64]$lastPassedTicks)
                $ageHours = ((Get-Date).ToUniversalTime() - $passedDt.ToUniversalTime()).TotalHours
                if ($ageHours -le 24) { $smartScore += 100 }
                elseif ($ageHours -le 168) { $smartScore += 50 }
            } catch { }
        }
        if ($null -ne $history -and $history.PSObject.Properties['last_rtt_ms']) {
            $histRtt = [int]$history.last_rtt_ms
            if ($histRtt -gt 0 -and $histRtt -le 350) { $smartScore += 50 }
            elseif ($histRtt -gt 1500) { $smartScore -= 50 }
        }
        $smartScore = [Math]::Max(0, [Math]::Min(1000, $smartScore))
        if ($null -eq $candidate.PSObject.Properties['SmartScore']) {
            $candidate | Add-Member -NotePropertyName SmartScore -NotePropertyValue $smartScore -Force
        } else {
            $candidate.SmartScore = $smartScore
        }

        $decorated += [pscustomobject]@{
            Candidate = $candidate
            RegionRank = $regionRank
            VerifiedRank = if ($isVerified) { 0 } else { 1 }
            ActiveRank = if ($isActive) { 0 } else { 1 }
            LastPassedTicks = $lastPassedTicks
            SuccessCount = $successCount
            SmartScore = $smartScore
            Priority = $priority
            DiscoveryIndex = $discoveryIndex
        }
    }

    # A node that already passed the real model gate is stronger evidence than
    # its country label. Keep verified/sticky history first; among equally
    # proven or unproven candidates, prefer United States and use Japan as the
    # fallback. SmartScore refines ordering with latency and recency.
    $ordered = @($decorated | Sort-Object @{ Expression = { $_.VerifiedRank } }, @{ Expression = { $_.ActiveRank } }, @{ Expression = { $_.RegionRank } }, @{ Expression = { $_.SmartScore }; Descending = $true }, @{ Expression = { $_.LastPassedTicks }; Descending = $true }, @{ Expression = { $_.SuccessCount }; Descending = $true }, @{ Expression = { $_.Priority } }, @{ Expression = { $_.DiscoveryIndex } })
    if ($ordered.Count -gt $MaxCandidateCount) {
        # United States remains the primary region. If the pool is larger than
        # the bounded probe budget, reserve up to 16 slots for the Japan
        # fallback so a cooling US prefix cannot starve it.
        $primaryOrdered = @($ordered | Where-Object { [int]$_.RegionRank -eq 0 })
        $fallbackOrdered = @($ordered | Where-Object { [int]$_.RegionRank -eq 1 })
        $fallbackReserve = if ($primaryOrdered.Count -gt 0) {
            [Math]::Min(16, $fallbackOrdered.Count)
        } else {
            0
        }
        $primaryLimit = [Math]::Max(0, $MaxCandidateCount - $fallbackReserve)
        $capped = @($primaryOrdered | Select-Object -First $primaryLimit)
        $remaining = $MaxCandidateCount - $capped.Count
        if ($remaining -gt 0) {
            $capped += @($fallbackOrdered | Select-Object -First $remaining)
        }
        $ordered = @($capped)
    }
    return @($ordered | ForEach-Object { $_.Candidate })
}

function Save-FailoverState {
    param(
        [Parameter(Mandatory = $true)]$State,
        [string]$ActiveNodeId = ''
    )

    $currentFingerprint = Get-CurrentAccountFingerprint
    if ($null -eq $State.PSObject.Properties['account_fingerprint']) {
        $State | Add-Member -NotePropertyName account_fingerprint -NotePropertyValue $currentFingerprint -Force
    } elseif (-not [string]::IsNullOrWhiteSpace($currentFingerprint)) {
        $State.account_fingerprint = $currentFingerprint
    }
    if (-not [string]::IsNullOrWhiteSpace($ActiveNodeId)) {
        $State.active_node_id = $ActiveNodeId
        $State.last_switch_at = (Get-Date).ToString('o')
    }
    $State.failed_nodes = @(Get-ActiveCooldownEntries -State $State)
    $temp = $FailoverStatePath + '.tmp'
    $State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $FailoverStatePath -Force
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
    if ($processInfo.Name -notmatch '^(verge-mihomo|mihomo|mihomo-windows-amd64|clash-meta)(\.exe)?$') {
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
    if ($null -eq $processInfo -or $processInfo.Name -notmatch '^(verge-mihomo|mihomo|mihomo-windows-amd64|clash-meta)(\.exe)?$') { return $null }
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

function Get-CandidateNodeDefinitions {
    $profileSources = @()
    $currentProfileId = ''
    $indexedProfiles = @(Get-IndexedRemoteProfiles)
    $indexedVergeProfiles = @($indexedProfiles | Where-Object { [string]$_.Family -eq 'clash-verge' })
    $indexedPartyProfiles = @($indexedProfiles | Where-Object { [string]$_.Family -eq 'mihomo-party' })

    # Clash Verge's generated runtime config is the authoritative active
    # composition after remote subscriptions, proxy providers and merge rules
    # have been refreshed. Raw profile YAML can omit provider-backed nodes.
    if (Test-Path -LiteralPath $ActiveClashConfig) {
        $profileSources += [pscustomobject]@{
            Path = $ActiveClashConfig
            SourceKey = 'clash-verge-runtime'
            SourceName = 'Clash Verge runtime'
            SourceType = 'runtime'
            UpdatedAt = $null
            ExpiresAt = $null
            Priority = 20
        }
    }
    if (Test-Path -LiteralPath $ProfilesIndex) {
        try {
            $indexText = Get-Content -LiteralPath $ProfilesIndex -Raw -ErrorAction Stop
            $currentMatch = [regex]::Match($indexText, '(?m)^current:\s*([^\s#]+)')
            if ($currentMatch.Success) {
                $currentProfileId = $currentMatch.Groups[1].Value.Trim()
            }
        } catch {
            $currentProfileId = ''
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($currentProfileId)) {
        $currentProfile = @($indexedVergeProfiles | Where-Object { [string]$_.Id -eq $currentProfileId } | Select-Object -First 1)
        $currentProfilePath = Join-Path $ProfilesRoot ($currentProfileId + '.yaml')
        if ($currentProfile.Count -gt 0 -and (Test-IndexedProfileUsable -Profile $currentProfile[0])) {
            $profileSources += [pscustomobject]@{
                Path = $currentProfilePath
                SourceKey = ('clash-verge-current-' + $currentProfileId)
                SourceName = [string]$currentProfile[0].DisplayName
                SourceType = 'subscription-cache'
                UpdatedAt = $currentProfile[0].UpdatedAt
                ExpiresAt = $currentProfile[0].ExpiresAt
                Priority = 20
            }
        }
    }

    # Only indexed, non-expired remote profiles are eligible. Scanning every
    # historical YAML in the cache made expired subscriptions look like live
    # fallbacks and consumed the real model probe budget.
    if ($indexedVergeProfiles.Count -gt 0) {
        foreach ($profile in $indexedVergeProfiles) {
            if (-not (Test-IndexedProfileUsable -Profile $profile)) { continue }
            $profileSources += [pscustomobject]@{
                Path = [string]$profile.Path
                SourceKey = ('clash-verge-cache-' + [string]$profile.Id)
                SourceName = [string]$profile.DisplayName
                SourceType = 'subscription-cache'
                UpdatedAt = $profile.UpdatedAt
                ExpiresAt = $profile.ExpiresAt
                Priority = 30
            }
        }
    } else {
        # Keep a bounded compatibility fallback for machines whose Clash
        # version has no readable profile index. It is still subject to the
        # live Google/OAuth/egress/model gates below.
        $profileSources += @(Get-ChildItem -LiteralPath $ProfilesRoot -Filter '*.yaml' -File -ErrorAction SilentlyContinue | ForEach-Object {
            [pscustomobject]@{
                Path = $_.FullName
                SourceKey = ('clash-verge-cache-' + $_.BaseName)
                SourceName = 'Clash Verge unindexed cache'
                SourceType = 'subscription-cache'
                UpdatedAt = $_.LastWriteTimeUtc
                ExpiresAt = $null
                Priority = 30
            }
        })
    }

    # Clash Party is used only as another maintained subscription cache. Its
    # own 7890/7891 listener, system proxy and TUN never become dependencies of
    # Antigravity: the candidate definition is copied into the private 17897
    # Mihomo configuration and works even after Clash Party is closed.
    foreach ($profile in $indexedPartyProfiles) {
        if (-not (Test-IndexedProfileUsable -Profile $profile)) { continue }
        $profileSources += [pscustomobject]@{
            Path = [string]$profile.Path
            SourceKey = ('clash-party-' + [string]$profile.Id)
            SourceName = [string]$profile.DisplayName
            SourceType = 'subscription-cache'
            UpdatedAt = $profile.UpdatedAt
            ExpiresAt = $profile.ExpiresAt
            Priority = 40
        }
    }

    $candidates = @()
    $seenDefinitions = @{}
    $seenPaths = @{}
    foreach ($source in ($profileSources | Sort-Object Priority)) {
        $profilePath = [string]$source.Path
        if ($seenPaths.ContainsKey($profilePath)) { continue }
        $seenPaths[$profilePath] = $true
        try {
            foreach ($line in @(Get-Content -LiteralPath $profilePath -Encoding UTF8 -ErrorAction Stop)) {
                $trimmed = ([string]$line).Trim()
                if (-not $trimmed.StartsWith('- {')) {
                    continue
                }
                $nameMatch = [regex]::Match($trimmed, '^\- \{\s*name:\s*(?:''([^'']+)''|"([^"]+)"|([^,]+))\s*,')
                $candidateName = ''
                if ($nameMatch.Success) {
                    foreach ($groupIndex in 1..3) {
                        if ($nameMatch.Groups[$groupIndex].Success) {
                            $candidateName = $nameMatch.Groups[$groupIndex].Value.Trim()
                            break
                        }
                    }
                }
                $matchesJapan = $candidateName.IndexOf($JapanNodeMatch, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                    [regex]::IsMatch($candidateName, '(?i)(^|\W)(Japan|Tokyo|JP)(\W|$)')
                $matchesUnitedStates = $candidateName.IndexOf($UnitedStatesNodeMatch, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
                    [regex]::IsMatch($candidateName, '(?i)(^|\W)(US|USA|United States|Los Angeles)(\W|$)')
                $matchesTarget = if ($TargetNodeExactMatch) {
                    $candidateName.Equals($TargetNodeMatch, [System.StringComparison]::OrdinalIgnoreCase)
                } else {
                    $matchesJapan -or $matchesUnitedStates
                }
                if ($nameMatch.Success -and $matchesTarget) {
                    $nodeDefinition = $trimmed.Substring(2).Trim()
                    $firstComma = $nodeDefinition.IndexOf(',')
                    if ($firstComma -lt 0) {
                        continue
                    }
                    $definitionTail = $nodeDefinition.Substring($firstComma)
                    $definitionId = Get-StringSha256 -Text $definitionTail
                    if ($seenDefinitions.ContainsKey($definitionId)) { continue }
                    $seenDefinitions[$definitionId] = $true
                    $sourceId = Get-StringSha256 -Text ([string]$source.SourceKey)
                    $candidateCountry = if ($matchesJapan) { 'JP' } elseif ($matchesUnitedStates) { 'US' } else { $ExpectedEgressCountry }
                    if ([string]::IsNullOrWhiteSpace($candidateCountry)) {
                        continue
                    }
                    $regionRank = if ($candidateCountry -eq 'US') { 0 } else { 1 }
                    $priority = ($regionRank * 1000) + [int]$source.Priority
                    $candidates += [pscustomobject]@{
                        Id = Get-StringSha256 -Text (([string]$source.SourceKey) + '|' + $candidateName + '|' + $definitionId)
                        SourceId = $sourceId
                        SourceKey = [string]$source.SourceKey
                        DefinitionId = $definitionId
                        Name = $candidateName
                        Definition = ('{ name: ' + $TargetAlias + $definitionTail)
                        SourceName = [string]$source.SourceName
                        SourceType = [string]$source.SourceType
                        SourceUpdatedAt = $source.UpdatedAt
                        SourceExpiresAt = $source.ExpiresAt
                        Region = $candidateCountry
                        RegionRank = $regionRank
                        ExpectedEgressCountry = $candidateCountry
                        Priority = $priority
                    }
                }
            }
        } catch {
            continue
        }
    }

    # Interleave providers. Three nodes from three subscriptions are more
    # useful than three labels from one provider during a provider-wide outage.
    $ordered = @()
    $groups = @($candidates | Group-Object SourceId | Sort-Object {
        ($_.Group | Measure-Object Priority -Minimum).Minimum
    })
    # Preserve the cross-subscription order for diagnostics, but do not cap
    # here. The cap belongs after failover state filtering in
    # Get-OrderedCandidates; otherwise retired Japan candidates can hide
    # healthy United States fallbacks.
    for ($round = 0; ; $round++) {
        $added = $false
        foreach ($group in $groups) {
            $items = @($group.Group | Sort-Object Priority, Name)
            if ($round -lt $items.Count) {
                $ordered += $items[$round]
                $added = $true
            }
        }
        if (-not $added) { break }
    }
    return @($ordered)
}

function Get-ReportDateString {
    param($Value)

    if ($null -eq $Value) { return '' }
    try { return ([datetime]$Value).ToUniversalTime().ToString('o') } catch { return [string]$Value }
}

function Save-SubscriptionReport {
    param(
        [Parameter(Mandatory = $true)][object[]]$Candidates,
        [Parameter(Mandatory = $true)]$State,
        [object[]]$EligibleCandidates = @()
    )

    try {
        $retiredIds = @{}
        foreach ($id in @(Get-RetiredNodeIds -State $State)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$id)) { $retiredIds[[string]$id] = $true }
        }
        $cooldownIds = @{}
        foreach ($entry in @(Get-ActiveCooldownEntries -State $State)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$entry.node_id)) { $cooldownIds[[string]$entry.node_id] = $true }
        }
        $verifiedIds = @{}
        foreach ($entry in @(Get-SuccessfulNodeEntries -State $State)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$entry.node_id)) { $verifiedIds[[string]$entry.node_id] = $true }
        }
        $eligibleIds = @{}
        foreach ($candidate in @($EligibleCandidates)) {
            if ($null -ne $candidate -and -not [string]::IsNullOrWhiteSpace([string]$candidate.Id)) {
                $eligibleIds[[string]$candidate.Id] = $true
            }
        }

        $currentCandidateIds = @{}
        foreach ($candidate in @($Candidates)) {
            if ($null -ne $candidate -and -not [string]::IsNullOrWhiteSpace([string]$candidate.Id)) {
                $currentCandidateIds[[string]$candidate.Id] = $true
            }
        }
        $currentRetiredIds = @{}
        foreach ($id in @($retiredIds.Keys)) {
            if ($currentCandidateIds.ContainsKey([string]$id)) { $currentRetiredIds[[string]$id] = $true }
        }
        $currentCoolingIds = @{}
        foreach ($id in @($cooldownIds.Keys)) {
            if ($currentCandidateIds.ContainsKey([string]$id)) { $currentCoolingIds[[string]$id] = $true }
        }
        $currentVerifiedIds = @{}
        foreach ($id in @($verifiedIds.Keys)) {
            if ($currentCandidateIds.ContainsKey([string]$id)) { $currentVerifiedIds[[string]$id] = $true }
        }

        $runAttemptedIds = @{}
        $runPassedIds = @{}
        $runRetiredIds = @{}
        $runCoolingIds = @{}
        $runFailureKindCounts = [ordered]@{}
        foreach ($candidate in @($Candidates)) {
            $candidateId = [string]$candidate.Id
            if ([string]::IsNullOrWhiteSpace($candidateId) -or -not $script:AttemptedCandidateIds.ContainsKey($candidateId)) {
                continue
            }
            $runAttemptedIds[$candidateId] = $true
            $kind = ''
            if ($script:AttemptedCandidateFailureKinds.ContainsKey($candidateId)) {
                $kind = [string]$script:AttemptedCandidateFailureKinds[$candidateId]
            }
            if ($kind -eq 'passed') {
                $runPassedIds[$candidateId] = $true
            } elseif ($kind -in @('model_location', 'model_non_ok', 'proxy_egress_wrong_country', 'config_invalid')) {
                $runRetiredIds[$candidateId] = $true
            } elseif (-not [string]::IsNullOrWhiteSpace($kind)) {
                $runCoolingIds[$candidateId] = $true
            }
            if (-not [string]::IsNullOrWhiteSpace($kind)) {
                if (-not $runFailureKindCounts.ContainsKey($kind)) { $runFailureKindCounts[$kind] = 0 }
                $runFailureKindCounts[$kind] = [int]$runFailureKindCounts[$kind] + 1
            }
        }

        $subscriptionCandidates = @($Candidates | Where-Object { [string]$_.SourceType -ne 'runtime' })
        $groups = @($subscriptionCandidates | Group-Object SourceName | Sort-Object Name)
        $rows = @()
        foreach ($group in $groups) {
            $items = @($group.Group)
            $sourceEligible = @($items | Where-Object { $eligibleIds.ContainsKey([string]$_.Id) })
            $sourceVerified = @($items | Where-Object { $verifiedIds.ContainsKey([string]$_.Id) })
            $sourceRetired = @($items | Where-Object { $retiredIds.ContainsKey([string]$_.Id) })
            $sourceCooling = @($items | Where-Object { $cooldownIds.ContainsKey([string]$_.Id) })
            $sourceRunAttempted = @($items | Where-Object { $runAttemptedIds.ContainsKey([string]$_.Id) })
            $sourceRunPassed = @($items | Where-Object { $runPassedIds.ContainsKey([string]$_.Id) })
            $sourceRunRetired = @($items | Where-Object { $runRetiredIds.ContainsKey([string]$_.Id) })
            $sourceRunCooling = @($items | Where-Object { $runCoolingIds.ContainsKey([string]$_.Id) })
            $sourceRunLocation = @($sourceRunRetired | Where-Object {
                $candidateId = [string]$_.Id
                $script:AttemptedCandidateFailureKinds.ContainsKey($candidateId) -and
                    [string]$script:AttemptedCandidateFailureKinds[$candidateId] -eq 'model_location'
            })
            $sourceRunTransport = @($sourceRunCooling | Where-Object {
                $candidateId = [string]$_.Id
                $script:AttemptedCandidateFailureKinds.ContainsKey($candidateId) -and
                    [string]$script:AttemptedCandidateFailureKinds[$candidateId] -in @('transient_network', 'model_transport')
            })
            $updated = @($items | Where-Object { $null -ne $_.SourceUpdatedAt } | Select-Object -First 1)
            $expires = @($items | Where-Object { $null -ne $_.SourceExpiresAt } | Select-Object -First 1)
            $rows += [ordered]@{
                source = [string]$group.Name
                candidate_count = $items.Count
                japan_count = @($items | Where-Object { [string]$_.Region -eq 'JP' }).Count
                united_states_count = @($items | Where-Object { [string]$_.Region -eq 'US' }).Count
                eligible_count = $sourceEligible.Count
                verified_count = $sourceVerified.Count
                retired_count = $sourceRetired.Count
                cooling_count = $sourceCooling.Count
                last_run_attempted_count = $sourceRunAttempted.Count
                last_run_verified_count = $sourceRunPassed.Count
                last_run_retired_count = $sourceRunRetired.Count
                last_run_cooling_count = $sourceRunCooling.Count
                last_run_model_location_count = $sourceRunLocation.Count
                last_run_transport_failure_count = $sourceRunTransport.Count
                updated_at = if ($updated.Count -gt 0) { Get-ReportDateString -Value $updated[0].SourceUpdatedAt } else { '' }
                expires_at = if ($expires.Count -gt 0) { Get-ReportDateString -Value $expires[0].SourceExpiresAt } else { '' }
            }
        }

        $indexedProfiles = @(Get-IndexedRemoteProfiles)
        $expiredProfiles = @($indexedProfiles | Where-Object {
            $null -ne $_.ExpiresAt -and $_.ExpiresAt -le (Get-Date).ToUniversalTime()
        })
        $japanCount = @($Candidates | Where-Object { [string]$_.Region -eq 'JP' }).Count
        $unitedStatesCount = @($Candidates | Where-Object { [string]$_.Region -eq 'US' }).Count
        $runtimeCount = @($Candidates | Where-Object { [string]$_.SourceType -eq 'runtime' }).Count
        $report = [ordered]@{
            version = '1.0'
            generated_at = (Get-Date).ToUniversalTime().ToString('o')
            candidate_count = @($Candidates).Count
            japan_candidate_count = $japanCount
            united_states_candidate_count = $unitedStatesCount
            eligible_candidate_count = @($EligibleCandidates).Count
            verified_candidate_count = $currentVerifiedIds.Count
            retired_candidate_count = $currentRetiredIds.Count
            cooling_candidate_count = $currentCoolingIds.Count
            last_run_status = $script:LastRunStatus
            last_run_started_at = $script:RunStartedAt.ToString('o')
            last_run_finished_at = if ($null -ne $script:RunFinishedAt) { $script:RunFinishedAt.ToString('o') } else { '' }
            last_run_candidate_attempted_count = $runAttemptedIds.Count
            last_run_verified_count = $runPassedIds.Count
            last_run_retired_count = $runRetiredIds.Count
            last_run_cooling_count = $runCoolingIds.Count
            last_run_failure_kinds = $runFailureKindCounts
            runtime_candidate_count = $runtimeCount
            indexed_subscription_count = $indexedProfiles.Count
            expired_subscription_count = $expiredProfiles.Count
            source_count = $rows.Count
            recommendation = if ($script:LastRunStatus -eq 'ready') {
                'Prefer the candidate that passed the real model gate; keep US first and use JP only as fallback.'
            } elseif ($script:LastRunStatus -eq 'failed') {
                'No candidate passed the real model gate in the last run. Basic reachability is not model eligibility; check the current account and egress combination or update subscriptions before retrying.'
            } else {
                'Prefer US; use JP only after US candidates fail the real model gate. Basic reachability is not model eligibility.'
            }
            sources = @($rows)
            privacy = 'Stores only source label, country counts, status counts and timestamps; never stores subscription URLs, servers, UUIDs, passwords, tokens or account identifiers.'
        }

        New-Item -ItemType Directory -Path $ProxyRoot -Force | Out-Null
        $tempPath = $SubscriptionReportPath + '.tmp'
        $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $tempPath -Encoding UTF8
        Move-Item -LiteralPath $tempPath -Destination $SubscriptionReportPath -Force
        $script:SubscriptionInventory = $report
        Write-SafeLog -Event 'subscription_inventory_completed' -Values @{
            source_count = $rows.Count
            candidate_count = @($Candidates).Count
            japan = $japanCount
            united_states = $unitedStatesCount
            expired_sources = $expiredProfiles.Count
        }
    } catch {
        Write-SafeLog -Event 'subscription_inventory_write_failed' -Values @{ error_type = $_.Exception.GetType().Name }
    }
}

function Write-PrivateConfig {
    param(
        [Parameter(Mandatory = $true)][string]$ProfileId,
        [Parameter(Mandatory = $true)]$Candidate
    )

    New-Item -ItemType Directory -Path $ProxyRoot -Force | Out-Null
    $nodeDefinition = [string]$Candidate.Definition
    if ([string]::IsNullOrWhiteSpace($nodeDefinition)) {
        Stop-WithMessage -Event 'target_node_not_found'
    }

    $configLines = @(
        '# Generated by Antigravity-ProxySupervisor.ps1',
        '# Do not edit manually. Target node is copied from the current local Clash profile.',
        'mixed-port: 17897',
        'allow-lan: false',
        'bind-address: 127.0.0.1',
        'mode: rule',
        'log-level: silent',
        # The current Japan candidate is an IPv6 endpoint. Disabling IPv6
        # lets Mihomo bind locally but prevents the upstream tunnel from
        # reaching Google, producing a misleading connectivity failure.
        'ipv6: true',
        'tun:',
        '  enable: false',
        'proxies:',
        ('  - ' + $nodeDefinition)
    )

    $routeTarget = $TargetAlias
    if ($null -ne $script:FixedUpstream) {
        $fixed = $script:FixedUpstream
        $configLines += @(
            ('  - name: ' + $FixedUpstreamAlias),
            ('    type: ' + [string]$fixed.Type),
            ('    server: ' + (ConvertTo-YamlSingleQuoted -Value ([string]$fixed.Server))),
            ('    port: ' + [string]$fixed.Port),
            ('    username: ' + (ConvertTo-YamlSingleQuoted -Value ([string]$fixed.Username))),
            ('    pass' + 'word: ' + (ConvertTo-YamlSingleQuoted -Value ([string]$fixed.Password))),
            ('    dialer-proxy: ' + $TargetAlias)
        )
        $routeTarget = $FixedUpstreamAlias
    }
    $configLines += @(
        'proxy-groups:',
        '  - name: ANTIGRAVITY-ROUTE',
        '    type: select',
        '    proxies:',
        ('      - ' + $routeTarget),
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
        CandidateId = [string]$Candidate.Id
    }
}

function ConvertTo-YamlSingleQuoted {
    param([Parameter(Mandatory = $true)][string]$Value)

    return "'" + $Value.Replace("'", "''") + "'"
}

function Get-FixedUpstreamConfig {
    if (-not (Test-Path -LiteralPath $FixedUpstreamPath)) { return $null }

    try {
        $raw = Get-Content -LiteralPath $FixedUpstreamPath -Raw -ErrorAction Stop | ConvertFrom-Json
        if ($raw.PSObject.Properties.Name -contains 'enabled' -and -not [bool]$raw.enabled) { return $null }
        $type = ([string]$raw.type).Trim().ToLowerInvariant()
        $server = ([string]$raw.server).Trim()
        $port = [int]$raw.port
        $username = [string]$raw.username
        $password = [string]$raw.password
        $expectedCountry = ([string]$raw.expected_country).Trim().ToUpperInvariant()
        $expectedIp = ([string]$raw.expected_ip).Trim()
        if ($type -notin @('http', 'socks5')) { throw 'fixed_upstream_type_invalid' }
        if ([string]::IsNullOrWhiteSpace($server) -or $port -lt 1 -or $port -gt 65535) { throw 'fixed_upstream_endpoint_invalid' }
        if ([string]::IsNullOrWhiteSpace($username) -or [string]::IsNullOrWhiteSpace($password)) { throw 'fixed_upstream_credentials_missing' }
        if ($expectedCountry -notmatch '^[A-Z]{2}$') { throw 'fixed_upstream_country_invalid' }
        if (-not [string]::IsNullOrWhiteSpace($expectedIp)) {
            $parsedIp = $null
            if (-not [System.Net.IPAddress]::TryParse($expectedIp, [ref]$parsedIp)) { throw 'fixed_upstream_ip_invalid' }
        }
        return [pscustomobject]@{
            Type = $type
            Server = $server
            Port = $port
            Username = $username
            Password = $password
            ExpectedCountry = $expectedCountry
            ExpectedIp = $expectedIp
        }
    } catch {
        Write-SafeLog -Event 'fixed_upstream_config_invalid' -Values @{ error_type = $_.Exception.GetType().Name }
        throw 'fixed_upstream_config_invalid'
    }
}

function Test-PrivateConfig {
    $output = @(& $MihomoPath -t -d $ProxyRoot -f $ConfigPath 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-SafeLog -Event 'config_test_failed' -Values @{ code = $exitCode }
        throw 'config_test_failed'
    }
    Write-SafeLog -Event 'config_test_passed'
}

function Start-OrReuseMihomo {
    param(
        [Parameter(Mandatory = $true)][string]$ExpectedConfigHash
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
    if ($null -ne $owned -and $loadedHash -ne $ExpectedConfigHash) {
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
        $request.Timeout = $ProbeTimeoutMs
        $request.ReadWriteTimeout = $ProbeTimeoutMs
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

function Get-TextThroughProxy {
    param([Parameter(Mandatory = $true)][string]$Uri)

    $request = $null
    $response = $null
    $reader = $null
    try {
        $request = [System.Net.HttpWebRequest]::Create($Uri)
        $request.Proxy = New-Object -TypeName System.Net.WebProxy -ArgumentList @($ProxyUrl)
        $request.Timeout = $ProbeTimeoutMs
        $request.ReadWriteTimeout = $ProbeTimeoutMs
        $request.Method = 'GET'
        $response = $request.GetResponse()
        $reader = New-Object -TypeName System.IO.StreamReader -ArgumentList @($response.GetResponseStream())
        return $reader.ReadToEnd()
    } catch {
        return ''
    } finally {
        if ($null -ne $reader) {
            $reader.Dispose()
        }
        if ($null -ne $response) {
            $response.Close()
        }
    }
}

function Test-GoogleConnectivity {
    $googleStatus = 0
    $apiStatus = 0
    $oauthStatus = 0
    $probeRttMs = 0
    for ($attempt = 1; $attempt -le $ConnectivityAttemptCount; $attempt++) {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $googleStatus = Get-HttpStatusThroughProxy -Uri 'https://www.google.com/generate_204'
        $sw.Stop()
        $probeRttMs = [int]$sw.ElapsedMilliseconds
        $apiStatus = Get-HttpStatusThroughProxy -Uri 'https://generativelanguage.googleapis.com/'
        $oauthStatus = Get-HttpStatusThroughProxy -Uri 'https://oauth2.googleapis.com/'
        if ($googleStatus -gt 0 -and $apiStatus -gt 0 -and $oauthStatus -gt 0) {
            break
        }
        if ($attempt -lt $ConnectivityAttemptCount) {
            Start-Sleep -Seconds 2
        }
    }
    $script:LastGoogleStatus = $googleStatus
    $script:LastApiStatus = $apiStatus
    $script:LastOAuthStatus = $oauthStatus
    $script:LastProbeRttMs = $probeRttMs
    if ($googleStatus -le 0 -or $apiStatus -le 0 -or $oauthStatus -le 0) {
        Write-SafeLog -Event 'google_connectivity_failed' -Values @{ google = $googleStatus; api = $apiStatus; oauth = $oauthStatus; attempts = $ConnectivityAttemptCount; rtt_ms = $probeRttMs }
        Stop-WithMessage -Event 'google_connectivity_failed'
    }
    Write-SafeLog -Event 'google_connectivity_passed' -Values @{ google = $googleStatus; api = $apiStatus; oauth = $oauthStatus; attempts = $attempt; rtt_ms = $probeRttMs }
    return @{
        GoogleStatus = $googleStatus
        ApiStatus = $apiStatus
        OAuthStatus = $oauthStatus
        RttMs = $probeRttMs
    }
}

function Test-ProxyEgress {
    param(
        [Parameter(Mandatory = $true)][string]$ExpectedCountry,
        [string]$ExpectedIp = ''
    )

    $country = ''
    $wrongCountry = $false
    for ($attempt = 1; $attempt -le $ConnectivityAttemptCount; $attempt++) {
        $trace = Get-TextThroughProxy -Uri 'https://www.cloudflare.com/cdn-cgi/trace'
        $match = [regex]::Match($trace, '(?m)^loc=([A-Za-z]{2})\s*$')
        if ($match.Success) {
            $country = $match.Groups[1].Value.ToUpperInvariant()
            if ($country -eq $ExpectedCountry) {
                if (-not [string]::IsNullOrWhiteSpace($ExpectedIp)) {
                    $ipMatch = [regex]::Match($trace, '(?m)^ip=([^\s]+)\s*$')
                    if (-not $ipMatch.Success -or $ipMatch.Groups[1].Value.Trim() -ne $ExpectedIp) {
                        Write-SafeLog -Event 'fixed_upstream_exit_ip_failed' -Values @{ expected_ip_match = $false; attempts = $attempt }
                        throw 'fixed_upstream_exit_ip_failed'
                    }
                    Write-SafeLog -Event 'fixed_upstream_exit_ip_passed' -Values @{ expected_ip_match = $true; attempts = $attempt }
                }
                Write-SafeLog -Event 'proxy_egress_country_passed' -Values @{ country = $country; attempts = $attempt }
                return $country
            }
            $wrongCountry = $true
            break
        }
        if ($attempt -lt $ConnectivityAttemptCount) {
            Start-Sleep -Seconds 2
        }
    }

    $script:LastEgressCountry = $country
    Write-SafeLog -Event 'proxy_egress_country_failed' -Values @{ country = $country; expected = $ExpectedCountry; attempts = $ConnectivityAttemptCount }
    if ($wrongCountry) {
        throw 'proxy_egress_wrong_country'
    }
    throw 'proxy_egress_network_failure'
}

function Test-RealModelGeneration {
    $script:LastModelProbeState = 'running'
    if (-not (Test-Path -LiteralPath $AgyPath)) {
        $script:LastModelProbeState = 'failed'
        Write-SafeLog -Event 'model_probe_cli_missing'
        throw 'model_probe_cli_missing'
    }

    $probeId = [guid]::NewGuid().ToString('N')
    $probeLog = Join-Path $ProxyRoot ('agy-probe-' + $probeId + '.log')
    $previousEnvironment = @{}
    foreach ($name in @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY')) {
        $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
    }

    $startedAt = Get-Date
    $exitCode = -1
    $probeOutput = @()
    $probeDiagnosticText = ''
    try {
        $env:HTTP_PROXY = $ProxyUrl
        $env:HTTPS_PROXY = $ProxyUrl
        $env:ALL_PROXY = $ProxyUrl
        $env:NO_PROXY = 'localhost,127.0.0.1,::1'
        $probeOutput = @(& $AgyPath -p $ModelProbePrompt --output-format json --print-timeout ($ModelProbeTimeoutSeconds.ToString() + 's') --sandbox --log-file $probeLog 2>&1)
        $exitCode = $LASTEXITCODE
    } finally {
        Restore-ProcessEnvironment -Previous $previousEnvironment
    }

    $status = ''
    $responseText = ''
    try {
        $probeResult = (($probeOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine) | ConvertFrom-Json
        $status = [string]$probeResult.status
        $responseText = ([string]$probeResult.response).Trim()
    } catch {
        $status = 'INVALID_OUTPUT'
    }

    $locationFailure = $false
    if (Test-Path -LiteralPath $probeLog) {
        try {
            $probeDiagnosticText = Get-Content -LiteralPath $probeLog -Raw -ErrorAction SilentlyContinue
            $locationFailure = [bool](Select-String -LiteralPath $probeLog -Pattern 'User location is not supported|FAILED_PRECONDITION.*400' -CaseSensitive:$false -Quiet)
        } catch { }
    }
    Remove-Item -LiteralPath $probeLog -Force -ErrorAction SilentlyContinue

    $durationMs = [int][math]::Round(((Get-Date) - $startedAt).TotalMilliseconds)
    if ($exitCode -eq 0 -and $status -eq 'SUCCESS' -and $responseText -ceq 'OK') {
        $script:LastModelProbeState = 'passed'
        Write-SafeLog -Event 'model_generation_probe_passed' -Values @{ duration_ms = $durationMs }
        return $true
    }

    $transportFailure = [regex]::IsMatch(($probeDiagnosticText + ' ' + (($probeOutput | ForEach-Object { [string]$_ }) -join ' ')), '(?i)timed?\s*out|timeout|connection\s+(?:reset|closed|refused)|network|temporarily\s+unavailable|unreachable|eof|deadline')
    $failureKind = 'model_transport'
    if ($locationFailure) {
        $failureKind = 'model_location'
    } elseif ($status -eq 'SUCCESS' -or $status -eq 'ERROR' -or -not [string]::IsNullOrWhiteSpace($responseText)) {
        # A structured model result that is not exactly OK is a candidate
        # eligibility/quality failure. Retire it instead of trying it again.
        # Only an explicitly transport-shaped failure remains temporary.
        $failureKind = if ($transportFailure -and $status -ne 'SUCCESS') { 'model_transport' } else { 'model_non_ok' }
    }

    Write-SafeLog -Event 'model_generation_probe_failed' -Values @{
        exit_code = $exitCode
        status = $status
        location_failure = $locationFailure
        failure_kind = $failureKind
        duration_ms = $durationMs
    }
    $script:LastModelProbeState = 'failed'
    throw $failureKind
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
    # Cockpit Tools may replace either shortcut while switching accounts.
    # Keep both user entries pointed at the stable self-healing launcher. A
    # stale Codex cache copy must not become the canonical desktop entry just
    # because that copy happened to be the one invoked.
    try {
        $canonicalLauncher = $CanonicalLauncherPath
        if (-not (Test-Path -LiteralPath $canonicalLauncher)) {
            $canonicalLauncher = $LauncherPath
        }
        if (-not (Test-Path -LiteralPath $canonicalLauncher)) {
            Write-SafeLog -Event 'desktop_shortcut_launcher_missing'
            return
        }

        $shell = New-Object -ComObject WScript.Shell
        $shortcutTargets = @(
            @{ Path = $DesktopShortcutPath; Key = 'desktop' },
            @{ Path = $StartMenuShortcutPath; Key = 'start_menu' }
        )

        foreach ($target in $shortcutTargets) {
            $shortcutPath = [string]$target.Path
            $key = [string]$target.Key
            $shortcutHandled = $false
            $backupCreated = $false
            for ($attempt = 1; $attempt -le 3 -and -not $shortcutHandled; $attempt++) {
                try {
                    $needsRepair = $true

                    if (Test-Path -LiteralPath $shortcutPath) {
                        $current = $shell.CreateShortcut($shortcutPath)
                        $needsRepair = -not (
                            ([string]$current.TargetPath -ieq $canonicalLauncher) -and
                            [string]::IsNullOrWhiteSpace([string]$current.Arguments) -and
                            ([string]$current.WorkingDirectory -ieq (Split-Path -Parent $canonicalLauncher))
                        )
                    }

                    if (-not $needsRepair) {
                        Write-SafeLog -Event ($key + '_shortcut_verified')
                        $shortcutHandled = $true
                        break
                    }

                    if (Test-Path -LiteralPath $shortcutPath) {
                        if (-not $backupCreated) {
                            New-Item -ItemType Directory -Path $ShortcutBackupRoot -Force | Out-Null
                            $stamp = Get-Date -Format 'yyyyMMdd-HHmmssfff'
                            Copy-Item -LiteralPath $shortcutPath -Destination (Join-Path $ShortcutBackupRoot ('Antigravity-' + $key + '-before-self-heal-' + $stamp + '.lnk'))
                            $backupCreated = $true
                        }
                    } else {
                        $parent = Split-Path -Parent $shortcutPath
                        New-Item -ItemType Directory -Path $parent -Force | Out-Null
                    }

                    $shortcut = $shell.CreateShortcut($shortcutPath)
                    $shortcut.TargetPath = $canonicalLauncher
                    $shortcut.Arguments = ''
                    $shortcut.WorkingDirectory = Split-Path -Parent $canonicalLauncher
                    $shortcut.IconLocation = $AntigravityPath + ',0'
                    $shortcut.Description = 'Antigravity self-healing launcher'
                    $shortcut.Save()
                    Write-SafeLog -Event ($key + '_shortcut_repaired')
                    $shortcutHandled = $true
                } catch {
                    # Explorer, antivirus, or Cockpit can briefly hold a .lnk
                    # during account switching. Retry the same shortcut before
                    # reporting failure; never let one entry block proxy repair.
                    if ($attempt -ge 3) {
                        Write-SafeLog -Event 'shortcut_repair_failed' -Values @{ key = $key; error_type = $_.Exception.GetType().Name }
                    } else {
                        Start-Sleep -Milliseconds (150 * $attempt)
                    }
                }
            }
        }
    } catch {
        # COM setup failure must not prevent an otherwise healthy app startup.
        Write-SafeLog -Event 'desktop_shortcut_shell_failed' -Values @{ error_type = $_.Exception.GetType().Name }
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

    $forceWaitIterations = [Math]::Max(1, [int]($StopProcessTimeoutSeconds * 4))
    for ($i = 0; $i -lt $forceWaitIterations; $i++) {
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

if ($PolicyTest) {
    $policyCandidates = @(Get-CandidateNodeDefinitions)
    $policyDiscoveryAvailable = $policyCandidates.Count -gt 0
    if (-not $policyDiscoveryAvailable) {
        # CI and a first-run machine may not have local Clash caches yet. The
        # policy contract must still be testable without pretending that a
        # real candidate was discovered; live startup continues to fail safe
        # when the actual candidate list is empty.
        $policyCandidates = @(
            [pscustomobject]@{ Id = 'policy-united-states'; SourceId = 'policy-us-source'; Priority = 0; Region = 'US'; RegionRank = 0; Name = 'policy-united-states' },
            [pscustomobject]@{ Id = 'policy-japan'; SourceId = 'policy-japan-source'; Priority = 0; Region = 'JP'; RegionRank = 1; Name = 'policy-japan' }
        )
    }
    $policyState = New-EmptyFailoverState
    $policyState.active_node_id = 'verified-active'
    $policyState.last_switch_at = '2026-09-02T00:00:00Z'
    $policyState.successful_nodes = @([pscustomobject]@{
        node_id = 'verified-history'
        source_id = 'source-a'
        last_passed_at = '2026-09-02T01:00:00Z'
        success_count = 3
    })
    $policyCandidatesForOrder = @(
        [pscustomobject]@{ Id = 'unverified'; SourceId = 'source-b'; Priority = 0; Region = 'JP'; RegionRank = 0; Name = 'unverified' },
        [pscustomobject]@{ Id = 'verified-history'; SourceId = 'source-a'; Priority = 30; Region = 'JP'; RegionRank = 0; Name = 'verified-history' },
        [pscustomobject]@{ Id = 'retired'; SourceId = 'source-c'; Priority = 0; Region = 'JP'; RegionRank = 0; Name = 'retired' }
    )
    $policyState.retired_nodes = @([pscustomobject]@{
        node_id = 'retired'
        retired_at = '2026-09-02T00:00:00Z'
        reason = 'model_location'
        source_id = 'source-c'
    })
    $policyOrder = @(Get-OrderedCandidates -Candidates $policyCandidatesForOrder -State $policyState -IncludeCooldown)
    $regionOrder = @(Get-OrderedCandidates -Candidates @(
        [pscustomobject]@{ Id = 'japan-unverified'; SourceId = 'source-jp'; Priority = 0; Region = 'JP'; RegionRank = 1; Name = 'japan-unverified' },
        [pscustomobject]@{ Id = 'us-verified'; SourceId = 'source-us'; Priority = 0; Region = 'US'; RegionRank = 0; Name = 'us-verified' }
    ) -State (New-EmptyFailoverState) -IncludeCooldown)
    $verifiedCrossRegionState = New-EmptyFailoverState
    $verifiedCrossRegionState.successful_nodes = @([pscustomobject]@{
        node_id = 'jp-verified'
        source_id = 'source-jp'
        last_passed_at = '2026-09-02T02:00:00Z'
        success_count = 3
    })
    $verifiedCrossRegionOrder = @(Get-OrderedCandidates -Candidates @(
        [pscustomobject]@{ Id = 'us-unverified'; SourceId = 'source-us'; Priority = 0; Region = 'US'; RegionRank = 0; Name = 'us-unverified' },
        [pscustomobject]@{ Id = 'jp-verified'; SourceId = 'source-jp'; Priority = 0; Region = 'JP'; RegionRank = 1; Name = 'jp-verified' }
    ) -State $verifiedCrossRegionState -IncludeCooldown)
    $historyPreservationState = New-EmptyFailoverState
    $historyPreservationState.successful_nodes = @([pscustomobject]@{
        node_id = 'historically-good'
        source_id = 'source-history'
        last_passed_at = '2026-09-02T01:00:00Z'
        success_count = 4
    })
    Add-NodeCooldown -State $historyPreservationState -NodeId 'historically-good' -Reason 'model_location'
    [pscustomobject]@{
        candidate_count = $policyCandidates.Count
        discovery_available = $policyDiscoveryAvailable
        unique_count = @($policyCandidates | Select-Object -ExpandProperty Id -Unique).Count
        preferred_first = [bool]($policyCandidates.Count -gt 0 -and [int]$policyCandidates[0].RegionRank -eq 0)
        japan_candidate_count = @($policyCandidates | Where-Object { [string]$_.Region -eq 'JP' }).Count
        united_states_candidate_count = @($policyCandidates | Where-Object { [string]$_.Region -eq 'US' }).Count
        united_states_preferred_first = [bool]($regionOrder.Count -gt 0 -and [string]$regionOrder[0].Id -eq 'us-verified')
        account_scoped_state = [bool]((New-EmptyFailoverState).PSObject.Properties.Name -contains 'account_fingerprint')
        max_candidate_count = $MaxCandidateCount
        cooldown_minutes = $CandidateCooldownMinutes
        real_model_gate = $true
        agy_present = Test-Path -LiteralPath $AgyPath
        model_probe_timeout_seconds = $ModelProbeTimeoutSeconds
        stop_process_timeout_seconds = $StopProcessTimeoutSeconds
        log_failure_nonfatal = Test-SafeLogFailureIsNonFatal
        model_non_ok_disposition = Get-CandidateFailureDisposition -FailureKind 'model_non_ok'
        location_failure_disposition = Get-CandidateFailureDisposition -FailureKind 'model_location'
        location_failure_preserves_history = [bool](@(Get-SuccessfulNodeEntries -State $historyPreservationState | Where-Object { [string]$_.node_id -eq 'historically-good' }).Count -eq 1)
        failed_failover_restores_active_candidate = $true
        wrong_egress_disposition = Get-CandidateFailureDisposition -FailureKind 'proxy_egress_wrong_country'
        transient_network_disposition = Get-CandidateFailureDisposition -FailureKind 'transient_network'
        model_transport_disposition = Get-CandidateFailureDisposition -FailureKind 'model_transport'
        retired_node_excluded = [bool](@($policyOrder | Select-Object -ExpandProperty Id) -notcontains 'retired')
        verified_history_first = [bool]($policyOrder.Count -gt 0 -and [string]$policyOrder[0].Id -eq 'verified-history')
        verified_history_beats_unverified_region = [bool]($verifiedCrossRegionOrder.Count -gt 0 -and [string]$verifiedCrossRegionOrder[0].Id -eq 'jp-verified')
        success_history_limit = $MaxSuccessHistory
        fixed_upstream_supported = $true
        fixed_upstream_path_is_private = [bool]($FixedUpstreamPath -like (Join-Path $ProxyRoot '*'))
        fixed_upstream_uses_candidate_dialer = $true
        fixed_upstream_exact_ip_gate = $true
    } | ConvertTo-Json -Compress
    return
}

# The watcher and a foreground double-click can arrive at the same time. The
# launcher mutex alone does not protect this PowerShell worker, so serialize
# the actual proxy/config/model run as well. A process exit releases the OS
# mutex even when Stop-WithMessage terminates this script with an error.
$supervisorMutexCreated = $false
try {
    $SupervisorMutex = New-Object System.Threading.Mutex -ArgumentList @($true, 'Local\AntigravitySupervisorRun', [ref]$supervisorMutexCreated)
} catch {
    $SupervisorMutex = $null
}
if ($null -ne $SupervisorMutex -and -not $supervisorMutexCreated) {
    Write-SafeLog -Event 'supervisor_run_busy'
    exit 4
}

$MihomoPath = Resolve-MihomoPath
if ([string]::IsNullOrWhiteSpace($MihomoPath) -or -not (Test-Path -LiteralPath $MihomoPath)) {
    Stop-WithMessage -Event 'mihomo_missing'
}
if (-not (Test-Path -LiteralPath $AntigravityPath)) {
    Stop-WithMessage -Event 'antigravity_missing'
}

New-Item -ItemType Directory -Path $ProxyRoot -Force | Out-Null
$script:FixedUpstream = Get-FixedUpstreamConfig
if ($null -ne $script:FixedUpstream) {
    Write-SafeLog -Event 'fixed_upstream_enabled' -Values @{ expected_country = [string]$script:FixedUpstream.ExpectedCountry; expected_ip_check = -not [string]::IsNullOrWhiteSpace([string]$script:FixedUpstream.ExpectedIp) }
}
Repair-DesktopShortcut
$candidates = @(Get-CandidateNodeDefinitions)
$script:DiscoveredCandidateCount = $candidates.Count
if ($candidates.Count -eq 0) {
    Stop-WithMessage -Event 'target_node_not_found'
}
Write-SafeLog -Event 'candidate_discovery_completed' -Values @{ candidate_count = $candidates.Count }

$failoverState = Get-FailoverState
$script:CurrentFailoverState = $failoverState
$originalActiveCandidate = @($candidates | Where-Object {
    -not [string]::IsNullOrWhiteSpace([string]$failoverState.active_node_id) -and
    [string]$_.Id -eq [string]$failoverState.active_node_id
} | Select-Object -First 1)
if ($RecoveryReason -eq 'NetworkFailure' -and -not [string]::IsNullOrWhiteSpace([string]$failoverState.active_node_id)) {
    Add-NodeCooldown -State $failoverState -NodeId ([string]$failoverState.active_node_id) -Reason $RecoveryReason
}
$cooldownIds = @(Get-ActiveCooldownEntries -State $failoverState | Select-Object -ExpandProperty node_id)
$includeCooldown = $RecoveryReason -eq 'Startup'
$orderedCandidates = @(Get-OrderedCandidates -Candidates $candidates -State $failoverState -CooldownIds $cooldownIds -IncludeCooldown:$includeCooldown)
$script:EligibleCandidateCount = $orderedCandidates.Count
Save-SubscriptionReport -Candidates $candidates -State $failoverState -EligibleCandidates $orderedCandidates
if ($includeCooldown -and $cooldownIds.Count -gt 0) {
    Write-SafeLog -Event 'manual_startup_cooldown_bypass' -Values @{ candidate_count = $orderedCandidates.Count }
}
if ($orderedCandidates.Count -eq 0) {
    Save-FailoverState -State $failoverState
    Stop-WithMessage -Event 'all_candidates_in_cooldown'
}

$selectedCandidate = $null
$configState = $null
$connectivity = $null
$egressCountry = ''
$candidateIndex = 0
$candidateTotal = $orderedCandidates.Count
$script:CandidateTotal = $candidateTotal
foreach ($candidate in $orderedCandidates) {
    $candidateIndex++
    $script:CandidateIndex = $candidateIndex
    $script:AttemptedCandidateIds[[string]$candidate.Id] = $true
    try {
        Write-SafeLog -Event 'candidate_preflight_started' -Values @{ node_id = [string]$candidate.Id; candidate_index = $candidateIndex; candidate_total = $candidateTotal; recovery = $RecoveryReason }
        $candidateConfig = Write-PrivateConfig -ProfileId 'active-clash-runtime' -Candidate $candidate
        $script:CurrentConfigHash = [string]$candidateConfig.ConfigHash
        Test-PrivateConfig
        Start-OrReuseMihomo -ExpectedConfigHash $candidateConfig.ConfigHash
        $candidateConnectivity = Test-GoogleConnectivity
        $script:LastGoogleStatus = [int]$candidateConnectivity.GoogleStatus
        $script:LastApiStatus = [int]$candidateConnectivity.ApiStatus
        $script:LastOAuthStatus = [int]$candidateConnectivity.OAuthStatus
        $expectedCountry = if ($null -ne $script:FixedUpstream) { [string]$script:FixedUpstream.ExpectedCountry } else { [string]$candidate.ExpectedEgressCountry }
        $expectedIp = if ($null -ne $script:FixedUpstream) { [string]$script:FixedUpstream.ExpectedIp } else { '' }
        $candidateCountry = Test-ProxyEgress -ExpectedCountry $expectedCountry -ExpectedIp $expectedIp
        $script:LastEgressCountry = [string]$candidateCountry
        Test-RealModelGeneration | Out-Null
        for ($confirmationIndex = 2; $confirmationIndex -le $ModelProbeConfirmationCount; $confirmationIndex++) {
            Test-RealModelGeneration | Out-Null
            Write-SafeLog -Event 'model_generation_probe_confirmation_passed' -Values @{ attempt = $confirmationIndex; total = $ModelProbeConfirmationCount }
        }
        $selectedCandidate = $candidate
        $configState = $candidateConfig
        $connectivity = $candidateConnectivity
        $egressCountry = $candidateCountry
        $script:AttemptedCandidateFailureKinds[[string]$candidate.Id] = 'passed'
        Mark-NodeSuccess -State $failoverState -Candidate $candidate
        Write-SafeLog -Event 'candidate_preflight_passed' -Values @{ node_id = [string]$candidate.Id; source_id = [string]$candidate.SourceId; candidate_index = $candidateIndex; candidate_total = $candidateTotal; recovery = $RecoveryReason }
        break
    } catch {
        $failureKind = Get-CandidateFailureKind -ErrorRecord $_
        $script:AttemptedCandidateFailureKinds[[string]$candidate.Id] = $failureKind
        $failureDisposition = Get-CandidateFailureDisposition -FailureKind $failureKind
        if ($failureDisposition -eq 'retire') {
            Add-NodeRetirement -State $failoverState -NodeId ([string]$candidate.Id) -Reason $failureKind -Candidate $candidate
        } else {
            Add-NodeCooldown -State $failoverState -NodeId ([string]$candidate.Id) -Reason $failureKind
        }
        Write-SafeLog -Event 'candidate_preflight_failed' -Values @{ node_id = [string]$candidate.Id; source_id = [string]$candidate.SourceId; failure_kind = $failureKind; disposition = $failureDisposition; candidate_index = $candidateIndex; candidate_total = $candidateTotal }
    }
}
if ($null -eq $selectedCandidate) {
    if ($RecoveryReason -ne 'Startup' -and $originalActiveCandidate.Count -gt 0) {
        try {
            # Failover is make-before-break from the user's perspective. The
            # probe listener necessarily changes candidates on the same local
            # port, but if no replacement passes, restore the last active
            # definition instead of leaving Antigravity pointed at a dead
            # 17897. This is especially important for intermittent Google
            # location classification failures.
            $fallbackCandidate = $originalActiveCandidate[0]
            $fallbackConfig = Write-PrivateConfig -ProfileId 'active-clash-runtime' -Candidate $fallbackCandidate
            Test-PrivateConfig
            Start-OrReuseMihomo -ExpectedConfigHash $fallbackConfig.ConfigHash
            $fallbackConnectivity = Test-GoogleConnectivity
            $fallbackExpectedCountry = if ($null -ne $script:FixedUpstream) { [string]$script:FixedUpstream.ExpectedCountry } else { [string]$fallbackCandidate.ExpectedEgressCountry }
            $fallbackExpectedIp = if ($null -ne $script:FixedUpstream) { [string]$script:FixedUpstream.ExpectedIp } else { '' }
            $fallbackCountry = Test-ProxyEgress -ExpectedCountry $fallbackExpectedCountry -ExpectedIp $fallbackExpectedIp
            Save-FailoverState -State $failoverState -ActiveNodeId ([string]$fallbackCandidate.Id)
            $fallbackPid = 0
            try { $fallbackPid = [int](Get-Content -LiteralPath $PidPath -Raw).Trim() } catch { }
            $degradedState = [ordered]@{
                version = '2.7.0'
                status = 'degraded'
                started_at = $script:RunStartedAt.ToString('o')
                finished_at = (Get-Date).ToString('o')
                failure_event = 'no_verified_replacement_active_candidate_restored'
                last_error = 'no_verified_replacement_active_candidate_restored'
                profile_id = 'active-clash-runtime'
                target_alias = $TargetAlias
                target_node = 'CURRENT-VERIFIED-FAILOVER-CANDIDATE'
                active_node_id = [string]$fallbackCandidate.Id
                active_source_id = [string]$fallbackCandidate.SourceId
                candidate_count = $candidates.Count
                eligible_candidate_count = $orderedCandidates.Count
                candidate_index = $candidateIndex
                candidate_total = $candidateTotal
                config_hash = [string]$fallbackConfig.ConfigHash
                retired_candidate_count = @(Get-RetiredNodeIds -State $failoverState).Count
                verified_candidate_count = @(Get-SuccessfulNodeEntries -State $failoverState).Count
                recovery_reason = $RecoveryReason
                private_port = $Port
                mihomo_pid = $fallbackPid
                google_status = [int]$fallbackConnectivity.GoogleStatus
                generativelanguage_status = [int]$fallbackConnectivity.ApiStatus
                oauth_status = [int]$fallbackConnectivity.OAuthStatus
                egress_country = [string]$fallbackCountry
                real_model_probe = 'intermittent_failure_active_candidate_restored'
                localization_enabled = -not (Test-Path -LiteralPath $LocalizationDisabledMarkerPath)
                localization_mode = ''
                antigravity_pid = 0
                language_server_pid = 0
                language_proxy_connections = 0
                subscription_report = $SubscriptionReportPath
            }
            $degradedState | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding UTF8
            Write-SafeLog -Event 'active_candidate_restored_after_failed_failover' -Values @{ node_id = [string]$fallbackCandidate.Id; recovery = $RecoveryReason; port = $Port }
            exit 0
        } catch {
            Write-SafeLog -Event 'active_candidate_restore_failed' -Values @{ error_type = $_.Exception.GetType().Name; recovery = $RecoveryReason }
        }
    }
    Save-FailoverState -State $failoverState
    $script:LastRunStatus = 'failed'
    $script:RunFinishedAt = Get-Date
    Save-SubscriptionReport -Candidates $candidates -State $failoverState -EligibleCandidates $orderedCandidates
    Stop-OwnedMihomo
    Stop-WithMessage -Event 'no_healthy_candidate_available'
}
Save-FailoverState -State $failoverState -ActiveNodeId ([string]$selectedCandidate.Id)
$script:LastRunStatus = 'ready'
$script:RunFinishedAt = Get-Date
Save-SubscriptionReport -Candidates $candidates -State $failoverState -EligibleCandidates $orderedCandidates
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
    $localizationEnabled = -not (Test-Path -LiteralPath $LocalizationDisabledMarkerPath)
    $localizationMode = 'disabled'
    if ($localizationEnabled) {
        if (Test-Path -LiteralPath $LocalizationLoaderPath) {
            # Electron currently exposes DevToolsActivePort but ignores the
            # Chromium --load-extension switch. The loader is the primary
            # path for this client; the switch remains a future/fallback hook.
            $arguments += '--antigravity-localization-loader'
            $localizationMode = 'cdp-loader'
        } elseif (Test-Path -LiteralPath $LocalizationManifestPath) {
            $arguments += '--load-extension="' + $LocalizationExtensionPath + '"'
            $localizationMode = 'chromium-extension'
        } else {
            Stop-WithMessage -Event 'localization_extension_missing'
        }
        Write-SafeLog -Event ('localization_' + $localizationMode + '_selected')
    } else {
        Write-SafeLog -Event 'localization_extension_disabled'
    }
    # Installation deliberately leaves the currently open app alone. Once a
    # launcher invocation has applied the selected language, the watcher may
    # enforce that choice on later runtime drift checks.
    Remove-Item -LiteralPath $LocalizationPendingMarkerPath -Force -ErrorAction SilentlyContinue
    $launchTime = Get-Date
    $antigravity = Start-Process -FilePath $AntigravityPath -ArgumentList $arguments -WorkingDirectory (Split-Path -Parent $AntigravityPath) -PassThru
    Write-SafeLog -Event 'antigravity_started' -Values @{ pid = $antigravity.Id; port = $Port }
} finally {
    Restore-ProcessEnvironment -Previous $previousEnvironment
}

$readiness = Wait-AntigravityReady -MainPid $antigravity.Id -LaunchTime $launchTime

if ($localizationEnabled -and $localizationMode -eq 'cdp-loader') {
    $loader = Start-Process -FilePath $LocalizationLoaderPath -WorkingDirectory $ScriptRoot -WindowStyle Hidden -Wait -PassThru
    if ($loader.ExitCode -ne 0) {
        Write-SafeLog -Event 'localization_loader_failed'
        Stop-ExistingAntigravity
        Stop-WithMessage -Event 'localization_loader_failed'
    }
    Write-SafeLog -Event 'localization_loader_succeeded'
}

$state = [ordered]@{
    version = '2.7.0'
    status = 'ready'
    started_at = (Get-Date).ToString('o')
    profile_id = $configState.ProfileId
    config_hash = $configState.ConfigHash
    target_alias = $TargetAlias
    target_node = 'CURRENT-VERIFIED-FAILOVER-CANDIDATE'
    active_node_id = [string]$selectedCandidate.Id
    active_source_id = [string]$selectedCandidate.SourceId
    active_node_score = if ($null -ne $selectedCandidate.PSObject.Properties['SmartScore']) { [int]$selectedCandidate.SmartScore } else { 0 }
    active_node_rtt_ms = [int]$script:LastProbeRttMs
    candidate_count = $candidates.Count
    eligible_candidate_count = $orderedCandidates.Count
    retired_candidate_count = @(Get-RetiredNodeEntries -State $failoverState).Count
    verified_candidate_count = @(Get-SuccessfulNodeEntries -State $failoverState).Count
    recovery_reason = $RecoveryReason
    private_port = $Port
    mihomo_pid = [int](Get-Content -LiteralPath $PidPath -Raw).Trim()
    google_status = $connectivity.GoogleStatus
    generativelanguage_status = $connectivity.ApiStatus
    oauth_status = $connectivity.OAuthStatus
    egress_country = $egressCountry
    real_model_probe = 'passed'
    localization_enabled = $localizationEnabled
    localization_mode = $localizationMode
    antigravity_pid = [int]$antigravity.Id
    language_server_pid = $readiness.LanguageServerPid
    language_proxy_connections = $readiness.ProxyConnections
    subscription_report = $SubscriptionReportPath
}
$script:CurrentConfigHash = [string]$configState.ConfigHash
$script:LastGoogleStatus = [int]$connectivity.GoogleStatus
$script:LastApiStatus = [int]$connectivity.ApiStatus
$script:LastOAuthStatus = [int]$connectivity.OAuthStatus
$script:LastEgressCountry = [string]$egressCountry
$script:LastModelProbeState = 'passed'
$script:LocalizationMode = [string]$localizationMode
$script:LaunchedAntigravityPid = [int]$antigravity.Id
$script:LaunchedLanguageServerPid = [int]$readiness.LanguageServerPid
$script:LaunchedProxyConnections = [int]$readiness.ProxyConnections
$state | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding UTF8
