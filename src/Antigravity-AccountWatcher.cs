using System;
using System.Diagnostics;
using System.IO;
using System.Management;
using System.Text.RegularExpressions;
using System.Threading;

internal static class AntigravityAccountWatcher
{
    private static readonly string AppDirectory = AppDomain.CurrentDomain.BaseDirectory;
    private static readonly string AccountsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".antigravity_cockpit", "accounts.json");
    private static readonly string RuntimeDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Antigravity", "private-proxy");
    private static readonly string StatePath = Path.Combine(RuntimeDirectory, "supervisor-state.json");
    private static readonly string LauncherPath = Path.Combine(AppDirectory, "Antigravity-Recovery-Launcher.exe");
    private static readonly string WatcherLogPath = Path.Combine(RuntimeDirectory, "account-watcher.log");
    private static readonly string AccountIdStatePath = Path.Combine(RuntimeDirectory, "watcher-current-account.txt");
    private const string RequiredProxyArgument = "--proxy-server=http://127.0.0.1:17897";

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

    private static void RunLauncher(string reason)
    {
        if (!File.Exists(LauncherPath))
        {
            Log("launcher_missing");
            return;
        }
        try
        {
            Log("repair_started reason=" + reason);
            using (var process = Process.Start(new ProcessStartInfo
            {
                FileName = LauncherPath,
                UseShellExecute = true,
                WorkingDirectory = Path.GetDirectoryName(LauncherPath)
            }))
            {
                if (process != null)
                {
                    process.WaitForExit();
                    Log("repair_finished code=" + process.ExitCode);
                }
            }
        }
        catch (Exception ex)
        {
            Log("repair_failed type=" + ex.GetType().Name);
        }
    }

    private static bool LauncherIsRunning()
    {
        try { return Process.GetProcessesByName("Antigravity-Launcher").Length > 0; }
        catch { return false; }
    }

    private static bool RuntimeNeedsRepair()
    {
        try
        {
            bool foundMainProcess = false;
            bool foundCompliantMainProcess = false;
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

                    foundMainProcess = true;
                    if (commandLine.IndexOf(RequiredProxyArgument, StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        foundCompliantMainProcess = true;
                    }
                }
            }

            // Do not reopen Antigravity after the user intentionally closes it.
            return foundMainProcess && !foundCompliantMainProcess;
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
            Log("watcher_started");

            DateTime observed = File.Exists(AccountsPath) ? File.GetLastWriteTimeUtc(AccountsPath) : DateTime.MinValue;
            string activeAccountId = ReadCurrentAccountId();
            string handledAccountId = File.Exists(AccountIdStatePath) ? File.ReadAllText(AccountIdStatePath).Trim() : "";
            int runtimeDriftChecks = 0;
            if (!string.IsNullOrEmpty(activeAccountId) && !string.Equals(activeAccountId, handledAccountId, StringComparison.OrdinalIgnoreCase))
            {
                Thread.Sleep(5000);
                RunLauncher("unhandled_current_account");
                File.WriteAllText(AccountIdStatePath, activeAccountId);
                handledAccountId = activeAccountId;
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
                        string newAccountId = ReadCurrentAccountId();
                        if (!string.IsNullOrEmpty(newAccountId) && !string.Equals(newAccountId, handledAccountId, StringComparison.OrdinalIgnoreCase))
                        {
                            Log("account_change_detected");
                            Thread.Sleep(5000);
                            observed = File.GetLastWriteTimeUtc(AccountsPath);
                            RunLauncher("cockpit_account_changed");
                            handledAccountId = newAccountId;
                            File.WriteAllText(AccountIdStatePath, handledAccountId);
                            runtimeDriftChecks = 0;
                            continue;
                        }
                    }
                }

                if (LauncherIsRunning())
                {
                    runtimeDriftChecks = 0;
                    continue;
                }

                runtimeDriftChecks = RuntimeNeedsRepair() ? runtimeDriftChecks + 1 : 0;
                if (runtimeDriftChecks >= 3)
                {
                    Log("runtime_proxy_bypass_detected");
                    RunLauncher("runtime_proxy_bypass");
                    runtimeDriftChecks = 0;
                }
            }
        }
    }
}
