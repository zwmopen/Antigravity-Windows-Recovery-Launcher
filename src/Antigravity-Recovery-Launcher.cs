using System;
using System.Diagnostics;
using System.IO;
using System.Drawing;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyVersion("0.5.2.0")]
[assembly: AssemblyFileVersion("0.5.2.0")]
[assembly: AssemblyInformationalVersion("0.5.2")]

internal static class AntigravityLauncher
{
    private static readonly string AppDirectory = AppDomain.CurrentDomain.BaseDirectory;
    private static readonly string ScriptPath = Path.Combine(AppDirectory, "Antigravity-ProxySupervisor.ps1");
    private static readonly string WatcherPath = Path.Combine(AppDirectory, "Antigravity-AccountWatcher.exe");
    private static readonly string RuntimeDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Antigravity", "private-proxy");
    private static readonly string LauncherLogPath = Path.Combine(RuntimeDirectory, "launcher-error.log");
    private static readonly string SupervisorLogPath = Path.Combine(RuntimeDirectory, "supervisor.log");

    private static void EnsureWatcherRunning()
    {
        try
        {
            if (!File.Exists(WatcherPath) || Process.GetProcessesByName("Antigravity-AccountWatcher").Length > 0) return;
            Process.Start(new ProcessStartInfo
            {
                FileName = WatcherPath,
                WorkingDirectory = AppDirectory,
                UseShellExecute = true,
                WindowStyle = ProcessWindowStyle.Hidden
            });
        }
        catch { }
    }

    private static string GetStatusText()
    {
        try
        {
            if (!File.Exists(SupervisorLogPath)) return "Checking private proxy configuration...";
            string[] lines = File.ReadAllLines(SupervisorLogPath);
            string line = lines.Length == 0 ? "" : lines[lines.Length - 1];
            if (line.Contains("config_test")) return "Checking private proxy configuration...";
            if (line.Contains("proxy_restart") || line.Contains("proxy_stopped") || line.Contains("proxy_started") || line.Contains("proxy_reused")) return "Preparing the verified private proxy...";
            if (line.Contains("google_connectivity")) return "Checking Google connectivity...";
            if (line.Contains("settings_proxy")) return "Applying Antigravity proxy settings...";
            if (line.Contains("existing_antigravity")) return "Closing the previous Antigravity instance...";
            if (line.Contains("antigravity_started")) return "Starting Antigravity and its language service...";
            if (line.Contains("antigravity_ready")) return "Verifying that Antigravity is ready...";
        }
        catch { }
        return "Repairing and restarting Antigravity...";
    }

    private static bool HasArgument(string[] args, string expected)
    {
        foreach (string arg in args)
        {
            if (string.Equals(arg, expected, StringComparison.OrdinalIgnoreCase)) return true;
        }
        return false;
    }

    private static string GetRecoveryReason(string[] args)
    {
        foreach (string arg in args)
        {
            const string prefix = "--recovery-reason=";
            if (!arg.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) continue;
            string value = arg.Substring(prefix.Length);
            if (value == "NetworkFailure" || value == "LocationFailure") return value;
        }
        return "Startup";
    }

    private static ProcessStartInfo CreateSupervisorStartInfo(string recoveryReason)
    {
        return new ProcessStartInfo
        {
            FileName = @"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" +
                ScriptPath + "\" -RecoveryReason " + recoveryReason,
            WorkingDirectory = AppDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
    }

    private static int RunBackgroundRepair(string recoveryReason)
    {
        var output = new StringBuilder();
        var error = new StringBuilder();
        try
        {
            using (var process = Process.Start(CreateSupervisorStartInfo(recoveryReason)))
            {
                if (process == null) return 3;
                process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) output.AppendLine(e.Data); };
                process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) error.AppendLine(e.Data); };
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();
                process.WaitForExit();
                if (process.ExitCode != 0)
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(LauncherLogPath));
                    File.AppendAllText(LauncherLogPath, DateTime.Now.ToString("o") +
                        " background=true recovery=" + recoveryReason + " exit=" + process.ExitCode +
                        Environment.NewLine + output + Environment.NewLine + error + Environment.NewLine);
                }
                return process.ExitCode;
            }
        }
        catch (Exception ex)
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(LauncherLogPath));
                File.AppendAllText(LauncherLogPath, DateTime.Now.ToString("o") +
                    " background=true recovery=" + recoveryReason + " type=" + ex.GetType().Name + Environment.NewLine);
            }
            catch { }
            return 3;
        }
    }

    [STAThread]
    private static int Main(string[] args)
    {
        bool backgroundMode = HasArgument(args, "--background");
        bool createdNew;
        using (var mutex = new Mutex(true, @"Local\AntigravitySelfHealingLauncher", out createdNew))
        {
            if (!createdNew)
            {
                if (!backgroundMode)
                {
                    MessageBox.Show("Antigravity is already being checked. Please wait for it to open.", "Antigravity", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                return 0;
            }

            if (!File.Exists(ScriptPath))
            {
                MessageBox.Show("The Antigravity repair script is missing:\n" + ScriptPath, "Antigravity launcher error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 2;
            }

            EnsureWatcherRunning();

            string recoveryReason = GetRecoveryReason(args);
            if (backgroundMode)
            {
                return RunBackgroundRepair(recoveryReason);
            }

            try
            {
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);

                var form = new Form
                {
                    Text = "Antigravity self-healing launcher",
                    Width = 520,
                    Height = 155,
                    FormBorderStyle = FormBorderStyle.FixedDialog,
                    MaximizeBox = false,
                    MinimizeBox = false,
                    StartPosition = FormStartPosition.CenterScreen,
                    ShowInTaskbar = true
                };
                var label = new Label
                {
                    Text = "Checking private proxy configuration...",
                    AutoSize = false,
                    Left = 22,
                    Top = 22,
                    Width = 460,
                    Height = 26,
                    Font = new Font("Segoe UI", 10F)
                };
                var progress = new ProgressBar
                {
                    Left = 22,
                    Top = 62,
                    Width = 460,
                    Height = 20,
                    Style = ProgressBarStyle.Marquee,
                    MarqueeAnimationSpeed = 25
                };
                form.Controls.Add(label);
                form.Controls.Add(progress);
                form.Show();
                Application.DoEvents();

                var startInfo = CreateSupervisorStartInfo(recoveryReason);

                using (var process = Process.Start(startInfo))
                {
                    if (process == null)
                    {
                        throw new InvalidOperationException("Windows did not start the repair process.");
                    }
                    var output = new StringBuilder();
                    var error = new StringBuilder();
                    process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) output.AppendLine(e.Data); };
                    process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) error.AppendLine(e.Data); };
                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    while (!process.HasExited)
                    {
                        label.Text = GetStatusText();
                        Application.DoEvents();
                        Thread.Sleep(250);
                    }
                    process.WaitForExit();
                    if (process.ExitCode != 0)
                    {
                        Directory.CreateDirectory(Path.GetDirectoryName(LauncherLogPath));
                        File.AppendAllText(LauncherLogPath, DateTime.Now.ToString("o") + " exit=" + process.ExitCode + Environment.NewLine + output.ToString() + Environment.NewLine + error.ToString() + Environment.NewLine);
                        form.Close();
                        MessageBox.Show("Antigravity did not pass its startup checks. Please run this launcher again. If it still fails, check the supervisor log.", "Antigravity launch failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }
                    else
                    {
                        label.Text = "Antigravity is ready.";
                        progress.Style = ProgressBarStyle.Blocks;
                        progress.Value = 100;
                        Application.DoEvents();
                        Thread.Sleep(1000);
                        form.Close();
                    }
                    return process.ExitCode;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Unable to start Antigravity:\n" + ex.Message, "Antigravity launcher error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 3;
            }
        }
    }
}
