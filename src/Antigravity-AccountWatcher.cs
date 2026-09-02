using System;
using System.Diagnostics;
using System.IO;
using System.Management;
using System.Net;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Threading;

[assembly: AssemblyVersion("0.5.2.0")]
[assembly: AssemblyFileVersion("0.5.2.0")]
[assembly: AssemblyInformationalVersion("0.5.2")]

internal static class AntigravityAccountWatcher
{
    private static readonly string AppDirectory = AppDomain.CurrentDomain.BaseDirectory;
    private static readonly string AccountsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".antigravity_cockpit", "accounts.json");
    private static readonly string RuntimeDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Antigravity", "private-proxy");
    private static readonly string StatePath = Path.Combine(RuntimeDirectory, "supervisor-state.json");
    private static readonly string LauncherPath = Path.Combine(AppDirectory, "Antigravity-Recovery-Launcher.exe");
    private static readonly string WatcherLogPath = Path.Combine(RuntimeDirectory, "account-watcher.log");
    private static readonly string AccountIdStatePath = Path.Combine(RuntimeDirectory, "watcher-current-account.txt");
    private static readonly string LanguageServerLogPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "Antigravity", "logs", "language_server.log");
    private static readonly string LocalizationDisabledMarkerPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Antigravity", "localization-extension-disabled.flag");
    private static readonly string LocalizationPendingMarkerPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Antigravity", "localization-extension-pending.flag");
    private const string RequiredProxyArgument = "--proxy-server=http://127.0.0.1:17897";
    private const string WatcherVersion = "0.5.2";
    internal const int MaxRepairAttempts = 3;
    internal const int SuccessfulRepairCooldownSeconds = 30;
    internal const int HealthFailureThreshold = 3;
    internal const int HealthCheckIntervalSeconds = 20;
    internal const int HealthRepairCooldownSeconds = 60;
    internal const int ExhaustedHealthRetrySeconds = 300;

    internal static bool AccountIdChanged(string activeAccountId, string handledAccountId)
    {
        return !string.IsNullOrEmpty(activeAccountId) &&
            !string.Equals(activeAccountId, handledAccountId, StringComparison.OrdinalIgnoreCase);
    }

    internal static int RetryDelaySeconds(int failedAttempts)
    {
        if (failedAttempts <= 0) return 0;
        int shift = Math.Min(failedAttempts - 1, 3);
        return 10 * (1 << shift);
    }

    internal static bool CanStartRepair(
        bool repairDue,
        bool launcherRunning,
        bool repairInProgress,
        DateTime utcNow,
        DateTime nextAttemptUtc,
        DateTime cooldownUntilUtc)
    {
        return repairDue && !launcherRunning && !repairInProgress &&
            utcNow >= nextAttemptUtc && utcNow >= cooldownUntilUtc;
    }

    internal static bool HealthRepairDue(int consecutiveFailures, bool newLocationFailure)
    {
        return newLocationFailure || consecutiveFailures >= HealthFailureThreshold;
    }

    internal static string RecoveryModeForReason(string reason)
    {
        if (string.Equals(reason, "proxy_location_failure", StringComparison.OrdinalIgnoreCase))
            return "LocationFailure";
        if (string.Equals(reason, "proxy_network_failure", StringComparison.OrdinalIgnoreCase))
            return "NetworkFailure";
        return "Startup";
    }

    private static bool LocalizationIsDisabled()
    {
        try { return File.Exists(LocalizationDisabledMarkerPath); }
        catch { return false; }
    }

    private static bool LocalizationActivationIsPending()
    {
        try { return File.Exists(LocalizationPendingMarkerPath); }
        catch { return false; }
    }

    private static bool HasLocalizationHook(string commandLine)
    {
        bool hasCdpLoaderFlag = commandLine.IndexOf(
            "--antigravity-localization-loader", StringComparison.OrdinalIgnoreCase) >= 0;
        bool hasChromiumExtension = commandLine.IndexOf(
            "--load-extension=", StringComparison.OrdinalIgnoreCase) >= 0 &&
            commandLine.IndexOf("localization-extension", StringComparison.OrdinalIgnoreCase) >= 0;
        return hasCdpLoaderFlag || hasChromiumExtension;
    }

    private static string ReadCurrentAccountId()
    {
        try
        {
            if (!File.Exists(AccountsPath)) return "";
            string json = File.ReadAllText(AccountsPath);
            Match match = Regex.Match(json, "\\\"current_account_id\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"", RegexOptions.IgnoreCase);
            return match.Success ? match.Groups[1].Value : "";
        }
        catch { return ""; }
    }

    private static void Log(string message)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(WatcherLogPath));
            File.AppendAllText(WatcherLogPath, DateTime.Now.ToString("o") + " " + message + Environment.NewLine);
        }
        catch { }
    }

    private static bool RunLauncher(string reason)
    {
        if (!File.Exists(LauncherPath))
        {
            Log("launcher_missing");
            return false;
        }
        try
        {
            Log("repair_started reason=" + reason);
            using (var process = Process.Start(new ProcessStartInfo
            {
                FileName = LauncherPath,
                Arguments = "--background --recovery-reason=" + RecoveryModeForReason(reason),
                UseShellExecute = true,
                WorkingDirectory = Path.GetDirectoryName(LauncherPath)
            }))
            {
                if (process != null)
                {
                    process.WaitForExit();
                    Log("repair_finished code=" + process.ExitCode);
                    return process.ExitCode == 0;
                }
            }
        }
        catch (Exception ex)
        {
            Log("repair_failed type=" + ex.GetType().Name);
        }
        return false;
    }

    private static bool HasCompliantMainProcess()
    {
        try
        {
            using (var searcher = new ManagementObjectSearcher(
                "SELECT CommandLine FROM Win32_Process WHERE Name='Antigravity.exe'"))
            using (var results = searcher.Get())
            {
                foreach (ManagementObject process in results)
                {
                    string commandLine = Convert.ToString(process["CommandLine"]);
                    if (string.IsNullOrWhiteSpace(commandLine) ||
                        commandLine.IndexOf("--type=", StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        continue;
                    }
                    if (commandLine.IndexOf(RequiredProxyArgument, StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        return true;
                    }
                }
            }
        }
        catch { }
        return false;
    }

    private static bool ProbeThroughPrivateProxy(string uri)
    {
        HttpWebResponse response = null;
        try
        {
            var request = (HttpWebRequest)WebRequest.Create(uri);
            request.Proxy = new WebProxy("http://127.0.0.1:17897");
            request.Method = "GET";
            request.Timeout = 6000;
            request.ReadWriteTimeout = 6000;
            response = (HttpWebResponse)request.GetResponse();
            return true;
        }
        catch (WebException ex)
        {
            response = ex.Response as HttpWebResponse;
            return response != null;
        }
        catch { return false; }
        finally
        {
            if (response != null) response.Close();
        }
    }

    private static bool PrivateProxyHealthy()
    {
        return ProbeThroughPrivateProxy("https://www.google.com/generate_204") &&
            ProbeThroughPrivateProxy("https://oauth2.googleapis.com/");
    }

    private static long CurrentLanguageLogLength()
    {
        try { return File.Exists(LanguageServerLogPath) ? new FileInfo(LanguageServerLogPath).Length : 0; }
        catch { return 0; }
    }

    private static bool ReadNewLocationFailure(ref long position)
    {
        try
        {
            if (!File.Exists(LanguageServerLogPath))
            {
                position = 0;
                return false;
            }
            using (var stream = new FileStream(LanguageServerLogPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                if (position < 0 || position > stream.Length) position = 0;
                stream.Seek(position, SeekOrigin.Begin);
                using (var reader = new StreamReader(stream))
                {
                    string appended = reader.ReadToEnd();
                    position = stream.Position;
                    return appended.IndexOf("User location is not supported", StringComparison.OrdinalIgnoreCase) >= 0;
                }
            }
        }
        catch { return false; }
    }

    private static bool LauncherIsRunning()
    {
        try
        {
            foreach (Process process in Process.GetProcessesByName("Antigravity-Recovery-Launcher"))
            {
                try
                {
                    string path = process.MainModule == null ? "" : process.MainModule.FileName;
                    if (string.Equals(path, LauncherPath, StringComparison.OrdinalIgnoreCase)) return true;
                }
                catch { }
                finally { process.Dispose(); }
            }
        }
        catch { }
        return false;
    }

    private static bool RuntimeNeedsRepair()
    {
        try
        {
            bool foundNonCompliantMainProcess = false;
            bool localizationDisabled = LocalizationIsDisabled();
            bool localizationPending = LocalizationActivationIsPending();
            using (var searcher = new ManagementObjectSearcher(
                "SELECT CommandLine FROM Win32_Process WHERE Name='Antigravity.exe'"))
            using (var results = searcher.Get())
            {
                foreach (ManagementObject process in results)
                {
                    string commandLine = Convert.ToString(process["CommandLine"]);
                    if (string.IsNullOrWhiteSpace(commandLine) ||
                        commandLine.IndexOf("--type=", StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        continue;
                    }

                    if (commandLine.IndexOf(RequiredProxyArgument, StringComparison.OrdinalIgnoreCase) < 0)
                    {
                        foundNonCompliantMainProcess = true;
                    }
                    else if (!localizationDisabled && !localizationPending && !HasLocalizationHook(commandLine))
                    {
                        foundNonCompliantMainProcess = true;
                    }
                }
            }

            // Do not reopen Antigravity after the user intentionally closes it.
            // If Cockpit left both a compliant and a non-compliant instance,
            // the non-compliant one is still a real routing defect.
            return foundNonCompliantMainProcess;
        }
        catch
        {
            return false;
        }
    }

    private static int Main()
    {
        bool createdNew;
        using (var mutex = new Mutex(true, @"Local\AntigravityCockpitAccountWatcher", out createdNew))
        {
            if (!createdNew) return 0;
            Log("watcher_started version=" + WatcherVersion);

            DateTime observed = File.Exists(AccountsPath) ? File.GetLastWriteTimeUtc(AccountsPath) : DateTime.MinValue;
            string activeAccountId = ReadCurrentAccountId();
            string handledAccountId = File.Exists(AccountIdStatePath) ? File.ReadAllText(AccountIdStatePath).Trim() : "";
            int runtimeDriftChecks = 0;
            string pendingAccountId = "";
            string suppressedAccountId = "";
            int accountRepairAttempts = 0;
            int runtimeRepairAttempts = 0;
            int healthFailureChecks = 0;
            int healthRepairAttempts = 0;
            DateTime nextAccountRepairUtc = DateTime.MinValue;
            DateTime nextRuntimeRepairUtc = DateTime.MinValue;
            DateTime nextHealthCheckUtc = DateTime.UtcNow.AddSeconds(5);
            DateTime nextHealthRepairUtc = DateTime.MinValue;
            DateTime repairCooldownUntilUtc = DateTime.MinValue;
            bool repairInProgress = false;
            bool locationFailurePending = false;
            long languageLogPosition = CurrentLanguageLogLength();
            if (AccountIdChanged(activeAccountId, handledAccountId))
            {
                pendingAccountId = activeAccountId;
                nextAccountRepairUtc = DateTime.UtcNow.AddSeconds(5);
                Log("account_change_observed source=startup");
            }

            while (true)
            {
                Thread.Sleep(2000);
                if (File.Exists(AccountsPath))
                {
                    DateTime current = File.GetLastWriteTimeUtc(AccountsPath);
                    if (current > observed)
                    {
                        observed = current;
                        string observedAccountId = ReadCurrentAccountId();
                        if (AccountIdChanged(observedAccountId, handledAccountId))
                        {
                            if (!string.Equals(observedAccountId, suppressedAccountId, StringComparison.OrdinalIgnoreCase) &&
                                !string.Equals(observedAccountId, pendingAccountId, StringComparison.OrdinalIgnoreCase))
                            {
                                pendingAccountId = observedAccountId;
                                accountRepairAttempts = 0;
                                nextAccountRepairUtc = DateTime.UtcNow.AddSeconds(5);
                                Log("account_change_observed source=accounts_file");
                            }
                        }
                        else
                        {
                            Log("accounts_file_write_ignored reason=account_unchanged");
                        }
                    }
                }

                activeAccountId = ReadCurrentAccountId();
                bool accountIdChanged = AccountIdChanged(activeAccountId, handledAccountId);
                if (!accountIdChanged)
                {
                    if (!string.IsNullOrEmpty(pendingAccountId))
                    {
                        Log("account_change_cancelled reason=returned_to_handled_account");
                    }
                    pendingAccountId = "";
                    suppressedAccountId = "";
                    accountRepairAttempts = 0;
                    nextAccountRepairUtc = DateTime.MinValue;
                }
                else if (!string.Equals(activeAccountId, suppressedAccountId, StringComparison.OrdinalIgnoreCase) &&
                    !string.Equals(activeAccountId, pendingAccountId, StringComparison.OrdinalIgnoreCase))
                {
                    pendingAccountId = activeAccountId;
                    accountRepairAttempts = 0;
                    nextAccountRepairUtc = DateTime.UtcNow.AddSeconds(5);
                    Log("account_change_observed source=account_id_poll");
                }

                DateTime utcNow = DateTime.UtcNow;
                bool launcherRunning = LauncherIsRunning();
                bool accountRepairDue = !string.IsNullOrEmpty(pendingAccountId) &&
                    accountRepairAttempts < MaxRepairAttempts;
                if (CanStartRepair(accountRepairDue, launcherRunning, repairInProgress,
                    utcNow, nextAccountRepairUtc, repairCooldownUntilUtc))
                {
                    string stableAccountId = ReadCurrentAccountId();
                    if (!string.Equals(stableAccountId, pendingAccountId, StringComparison.OrdinalIgnoreCase) ||
                        !AccountIdChanged(stableAccountId, handledAccountId))
                    {
                        pendingAccountId = "";
                        accountRepairAttempts = 0;
                        Log("account_change_cancelled reason=unstable_account_id");
                        continue;
                    }

                    Log("account_change_detected");
                    repairInProgress = true;
                    bool repaired = RunLauncher("cockpit_account_changed");
                    repairInProgress = false;
                    if (repaired)
                    {
                        handledAccountId = stableAccountId;
                        File.WriteAllText(AccountIdStatePath, handledAccountId);
                        pendingAccountId = "";
                        suppressedAccountId = "";
                        accountRepairAttempts = 0;
                        nextAccountRepairUtc = DateTime.MinValue;
                        repairCooldownUntilUtc = DateTime.UtcNow.AddSeconds(SuccessfulRepairCooldownSeconds);
                        runtimeDriftChecks = 0;
                        runtimeRepairAttempts = 0;
                        healthFailureChecks = 0;
                        healthRepairAttempts = 0;
                        locationFailurePending = false;
                        languageLogPosition = CurrentLanguageLogLength();
                    }
                    else
                    {
                        accountRepairAttempts++;
                        if (accountRepairAttempts >= MaxRepairAttempts)
                        {
                            suppressedAccountId = stableAccountId;
                            pendingAccountId = "";
                            Log("repair_retry_exhausted reason=cockpit_account_changed attempts=" + accountRepairAttempts);
                        }
                        else
                        {
                            int delaySeconds = RetryDelaySeconds(accountRepairAttempts);
                            nextAccountRepairUtc = DateTime.UtcNow.AddSeconds(delaySeconds);
                            Log("repair_retry_scheduled reason=cockpit_account_changed attempt=" +
                                (accountRepairAttempts + 1) + " delay_seconds=" + delaySeconds);
                        }
                    }
                    continue;
                }

                if (ReadNewLocationFailure(ref languageLogPosition))
                {
                    locationFailurePending = true;
                    Log("proxy_location_failure_observed");
                }

                bool compliantMainRunning = HasCompliantMainProcess();
                if (!compliantMainRunning)
                {
                    healthFailureChecks = 0;
                    healthRepairAttempts = 0;
                    locationFailurePending = false;
                }
                else if (!launcherRunning && !repairInProgress && DateTime.UtcNow >= nextHealthCheckUtc)
                {
                    bool healthy = PrivateProxyHealthy();
                    nextHealthCheckUtc = DateTime.UtcNow.AddSeconds(HealthCheckIntervalSeconds);
                    if (healthy)
                    {
                        if (healthFailureChecks > 0) Log("private_proxy_health_recovered");
                        healthFailureChecks = 0;
                        if (!locationFailurePending) healthRepairAttempts = 0;
                    }
                    else
                    {
                        healthFailureChecks++;
                        Log("private_proxy_health_failed consecutive=" + healthFailureChecks);
                    }
                }

                bool healthRepairDue = compliantMainRunning &&
                    HealthRepairDue(healthFailureChecks, locationFailurePending) &&
                    healthRepairAttempts < MaxRepairAttempts;
                if (CanStartRepair(healthRepairDue, launcherRunning, repairInProgress,
                    DateTime.UtcNow, nextHealthRepairUtc, repairCooldownUntilUtc))
                {
                    string healthReason = locationFailurePending ?
                        "proxy_location_failure" : "proxy_network_failure";
                    Log("health_recovery_started reason=" + healthReason);
                    repairInProgress = true;
                    bool repaired = RunLauncher(healthReason);
                    repairInProgress = false;
                    healthFailureChecks = 0;
                    locationFailurePending = false;
                    languageLogPosition = CurrentLanguageLogLength();
                    if (repaired)
                    {
                        healthRepairAttempts = 0;
                        nextHealthRepairUtc = DateTime.MinValue;
                        repairCooldownUntilUtc = DateTime.UtcNow.AddSeconds(HealthRepairCooldownSeconds);
                        nextHealthCheckUtc = repairCooldownUntilUtc;
                        Log("health_recovery_succeeded reason=" + healthReason);
                    }
                    else
                    {
                        if (healthReason == "proxy_location_failure") locationFailurePending = true;
                        else healthFailureChecks = HealthFailureThreshold;
                        healthRepairAttempts++;
                        if (healthRepairAttempts >= MaxRepairAttempts)
                        {
                            nextHealthRepairUtc = DateTime.UtcNow.AddSeconds(ExhaustedHealthRetrySeconds);
                            healthRepairAttempts = 0;
                            Log("repair_retry_cycle_exhausted reason=" + healthReason +
                                " retry_after_seconds=" + ExhaustedHealthRetrySeconds);
                        }
                        else
                        {
                            int delaySeconds = RetryDelaySeconds(healthRepairAttempts);
                            nextHealthRepairUtc = DateTime.UtcNow.AddSeconds(delaySeconds);
                            Log("repair_retry_scheduled reason=" + healthReason + " attempt=" +
                                (healthRepairAttempts + 1) + " delay_seconds=" + delaySeconds);
                        }
                    }
                    continue;
                }

                if (launcherRunning || repairInProgress || DateTime.UtcNow < repairCooldownUntilUtc)
                {
                    runtimeDriftChecks = 0;
                    continue;
                }

                bool runtimeNeedsRepair = RuntimeNeedsRepair();
                if (!runtimeNeedsRepair)
                {
                    runtimeDriftChecks = 0;
                    runtimeRepairAttempts = 0;
                    nextRuntimeRepairUtc = DateTime.MinValue;
                    continue;
                }

                runtimeDriftChecks++;
                bool runtimeRepairDue = runtimeDriftChecks >= 3 && runtimeRepairAttempts < MaxRepairAttempts;
                if (CanStartRepair(runtimeRepairDue, false, repairInProgress,
                    DateTime.UtcNow, nextRuntimeRepairUtc, repairCooldownUntilUtc))
                {
                    Log("runtime_proxy_bypass_detected");
                    repairInProgress = true;
                    bool repaired = RunLauncher("runtime_proxy_bypass");
                    repairInProgress = false;
                    runtimeDriftChecks = 0;
                    if (repaired)
                    {
                        runtimeRepairAttempts = 0;
                        nextRuntimeRepairUtc = DateTime.MinValue;
                        repairCooldownUntilUtc = DateTime.UtcNow.AddSeconds(SuccessfulRepairCooldownSeconds);
                    }
                    else
                    {
                        runtimeRepairAttempts++;
                        if (runtimeRepairAttempts >= MaxRepairAttempts)
                        {
                            Log("repair_retry_exhausted reason=runtime_proxy_bypass attempts=" + runtimeRepairAttempts);
                        }
                        else
                        {
                            int delaySeconds = RetryDelaySeconds(runtimeRepairAttempts);
                            nextRuntimeRepairUtc = DateTime.UtcNow.AddSeconds(delaySeconds);
                            Log("repair_retry_scheduled reason=runtime_proxy_bypass attempt=" +
                                (runtimeRepairAttempts + 1) + " delay_seconds=" + delaySeconds);
                        }
                    }
                }
            }
        }
    }
}
