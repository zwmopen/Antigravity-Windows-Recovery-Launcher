using System;
using System.Diagnostics;
using System.IO;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using System.Runtime.InteropServices;

[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]
[assembly: AssemblyInformationalVersion("1.0.0-preview")]

internal static class AntigravityLauncher
{
    private static readonly string AppDirectory = AppDomain.CurrentDomain.BaseDirectory;
    private static readonly string ScriptPath = Path.Combine(AppDirectory, "Antigravity-ProxySupervisor.ps1");
    private static readonly string WatcherPath = Path.Combine(AppDirectory, "Antigravity-AccountWatcher.exe");
    private static readonly string RuntimeDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Antigravity", "private-proxy");
    private static readonly string LauncherLogPath = Path.Combine(RuntimeDirectory, "launcher-error.log");
    private static readonly string SupervisorLogPath = Path.Combine(RuntimeDirectory, "supervisor.log");
    private static readonly string SupervisorStatePath = Path.Combine(RuntimeDirectory, "supervisor-state.json");
    private const string SupervisorMutexName = @"Local\AntigravitySupervisorRun";

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

    private static void ActivateExistingLauncher()
    {
        try
        {
            for (int attempt = 0; attempt < 20; attempt++)
            {
                foreach (Process process in Process.GetProcessesByName("Antigravity-Recovery-Launcher"))
                {
                    try
                    {
                        if (process.Id == Process.GetCurrentProcess().Id) continue;
                        IntPtr handle = process.MainWindowHandle;
                        if (handle == IntPtr.Zero) continue;
                        ShowWindowAsync(handle, 9); // SW_RESTORE
                        SetForegroundWindow(handle);
                        return;
                    }
                    finally { process.Dispose(); }
                }
                Thread.Sleep(100);
            }
        }
        catch { }
    }

    private sealed class StatusView
    {
        internal string Headline = "正在读取本机代理配置…";
        internal string Proxy = "● 正在建立 Antigravity 独立代理 127.0.0.1:17897";
        internal string Nodes = "○ 正在发现本机候选节点";
        internal string Verification = "○ 等待 Google、OAuth、日美出口和真实模型验证";
        internal string Localization = "○ 等待注入中文翻译";
        internal string Launch = "○ 等待启动 Antigravity";
        internal int Progress = 3;
        internal int Ceiling = 16;
    }

    private sealed class StatusProgress : Control
    {
        private int currentValue;

        internal StatusProgress()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint, true);
            Height = 24;
        }

        internal int ProgressValue
        {
            get { return currentValue; }
            set { currentValue = Math.Max(0, Math.Min(100, value)); Invalidate(); }
        }

        private static GraphicsPath RoundedRectangle(Rectangle rectangle, int radius)
        {
            var path = new GraphicsPath();
            int diameter = radius * 2;
            path.AddArc(rectangle.Left, rectangle.Top, diameter, diameter, 180, 90);
            path.AddArc(rectangle.Right - diameter, rectangle.Top, diameter, diameter, 270, 90);
            path.AddArc(rectangle.Right - diameter, rectangle.Bottom - diameter, diameter, diameter, 0, 90);
            path.AddArc(rectangle.Left, rectangle.Bottom - diameter, diameter, diameter, 90, 90);
            path.CloseFigure();
            return path;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var track = new Rectangle(0, 2, Width - 1, Height - 5);
            using (var trackPath = RoundedRectangle(track, 9))
            using (var trackBrush = new SolidBrush(Color.FromArgb(214, 224, 237))) e.Graphics.FillPath(trackBrush, trackPath);
            int fillWidth = Math.Max(18, (int)Math.Round(track.Width * currentValue / 100.0));
            var fill = new Rectangle(track.Left, track.Top, Math.Min(track.Width, fillWidth), track.Height);
            using (var fillPath = RoundedRectangle(fill, 9))
            using (var fillBrush = new LinearGradientBrush(fill, Color.FromArgb(96, 165, 250), Color.FromArgb(37, 99, 235), 0F)) e.Graphics.FillPath(fillBrush, fillPath);
            string percent = currentValue.ToString() + "%";
            SizeF textSize = e.Graphics.MeasureString(percent, Font);
            using (var textBrush = new SolidBrush(currentValue > 88 ? Color.White : Color.FromArgb(30, 64, 175)))
                e.Graphics.DrawString(percent, Font, textBrush, Width - textSize.Width - 8, (Height - textSize.Height) / 2F);
        }
    }

    private static bool IsOwnWatcherRunning()
    {
        try
        {
            foreach (Process process in Process.GetProcessesByName("Antigravity-AccountWatcher"))
            {
                try
                {
                    string path = process.MainModule == null ? "" : process.MainModule.FileName;
                    if (string.Equals(path, WatcherPath, StringComparison.OrdinalIgnoreCase)) return true;
                }
                catch { }
                finally { process.Dispose(); }
            }
        }
        catch { }
        return false;
    }

    private sealed class GlassPanel : Panel
    {
        internal GlassPanel()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
        }

        private static GraphicsPath RoundedRectangle(Rectangle rectangle, int radius)
        {
            var path = new GraphicsPath();
            int diameter = radius * 2;
            path.AddArc(rectangle.Left, rectangle.Top, diameter, diameter, 180, 90);
            path.AddArc(rectangle.Right - diameter, rectangle.Top, diameter, diameter, 270, 90);
            path.AddArc(rectangle.Right - diameter, rectangle.Bottom - diameter, diameter, diameter, 0, 90);
            path.AddArc(rectangle.Left, rectangle.Bottom - diameter, diameter, diameter, 90, 90);
            path.CloseFigure();
            return path;
        }

        protected override void OnResize(EventArgs eventArgs)
        {
            base.OnResize(eventArgs);
            Invalidate();
        }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.Clear(Color.FromArgb(215, 229, 242));
            var bounds = new Rectangle(0, 0, Width - 1, Height - 1);
            using (var path = RoundedRectangle(bounds, 18))
            using (var fill = new LinearGradientBrush(bounds, Color.FromArgb(247, 251, 255), Color.FromArgb(232, 241, 250), 90F))
            using (var border = new Pen(Color.FromArgb(235, 255, 255, 255), 1.2F))
            {
                e.Graphics.FillPath(fill, path);
                e.Graphics.DrawPath(border, path);
            }
            using (var highlight = new Pen(Color.FromArgb(120, 255, 255, 255), 2F)) e.Graphics.DrawLine(highlight, 24, 3, Width - 24, 3);
        }
    }

    private static void EnsureWatcherRunning()
    {
        try
        {
            if (!File.Exists(WatcherPath) || IsOwnWatcherRunning()) return;
            Process.Start(new ProcessStartInfo { FileName = WatcherPath, WorkingDirectory = AppDirectory, UseShellExecute = true, WindowStyle = ProcessWindowStyle.Hidden });
        }
        catch { }
    }

    private static long GetLogLength()
    {
        try { return File.Exists(SupervisorLogPath) ? new FileInfo(SupervisorLogPath).Length : 0; }
        catch { return 0; }
    }

    private static string ReadLogSince(long startOffset)
    {
        try
        {
            if (!File.Exists(SupervisorLogPath)) return "";
            using (var stream = new FileStream(SupervisorLogPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                stream.Position = Math.Min(startOffset, stream.Length);
                using (var reader = new StreamReader(stream, Encoding.UTF8, true)) return reader.ReadToEnd();
            }
        }
        catch { return ""; }
    }

    private static bool IsSupervisorMutexAvailable()
    {
        bool createdNew;
        try
        {
            using (var mutex = new Mutex(false, SupervisorMutexName, out createdNew))
            {
                bool acquired = false;
                try { acquired = mutex.WaitOne(0); }
                catch (AbandonedMutexException) { acquired = true; }
                if (!acquired) return false;
                try { return true; }
                finally { mutex.ReleaseMutex(); }
            }
        }
        catch { return true; }
    }

    private static bool HasFreshReadyState(DateTime requestedUtc)
    {
        try
        {
            if (!File.Exists(SupervisorStatePath)) return false;
            if (File.GetLastWriteTimeUtc(SupervisorStatePath) < requestedUtc.AddSeconds(-2)) return false;
            string compact = File.ReadAllText(SupervisorStatePath, Encoding.UTF8)
                .Replace(" ", "")
                .Replace("\r", "")
                .Replace("\n", "")
                .Replace("\t", "");
            return compact.IndexOf("\"status\":\"ready\"", StringComparison.OrdinalIgnoreCase) >= 0 &&
                compact.IndexOf("\"real_model_probe\":\"passed\"", StringComparison.OrdinalIgnoreCase) >= 0 &&
                compact.IndexOf("\"private_port\":17897", StringComparison.OrdinalIgnoreCase) >= 0;
        }
        catch { return false; }
    }

    private static bool WaitForConcurrentRecovery(
        DateTime requestedUtc,
        long logStartOffset,
        Action<StatusView> updateStatus,
        out string concurrentLog)
    {
        DateTime deadline = DateTime.UtcNow.AddMinutes(20);
        concurrentLog = "";
        while (DateTime.UtcNow < deadline)
        {
            concurrentLog = ReadLogSince(logStartOffset);
            if (updateStatus != null) updateStatus(BuildStatus(concurrentLog));
            if (HasFreshReadyState(requestedUtc)) return true;

            // The other recovery has released the mutex. Give its final log
            // and state writes a short flush window before deciding whether
            // the foreground launch should report the real failure.
            if (IsSupervisorMutexAvailable())
            {
                Thread.Sleep(700);
                concurrentLog = ReadLogSince(logStartOffset);
                if (updateStatus != null) updateStatus(BuildStatus(concurrentLog));
                return HasFreshReadyState(requestedUtc);
            }

            Application.DoEvents();
            Thread.Sleep(250);
        }
        concurrentLog = ReadLogSince(logStartOffset) + Environment.NewLine + "supervisor_run_busy";
        return false;
    }

    private static string GetValue(string line, string key)
    {
        string marker = key + "=";
        int index = line.IndexOf(marker, StringComparison.OrdinalIgnoreCase);
        if (index < 0) return "";
        string value = line.Substring(index + marker.Length);
        int end = value.IndexOf(' ');
        return end < 0 ? value.Trim() : value.Substring(0, end).Trim();
    }

    private static StatusView BuildStatus(string logText)
    {
        var view = new StatusView();
        int candidateIndex = 0;
        int candidateTotal = 0;
        int discoveredTotal = 0;
        string egressCountry = "";
        foreach (string line in logText.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
        {
            if (line.Contains("candidate_discovery_completed"))
            {
                string count = GetValue(line, "candidate_count");
                view.Nodes = "✅ 已发现 " + (count.Length == 0 ? "多" : count) + " 条候选线路";
                int parsedDiscoveredTotal;
                if (Int32.TryParse(count, out parsedDiscoveredTotal))
                {
                    discoveredTotal = parsedDiscoveredTotal;
                    candidateTotal = parsedDiscoveredTotal;
                }
                view.Headline = "候选节点已发现，正在逐条验证…";
                view.Progress = Math.Max(view.Progress, 20);
                view.Ceiling = Math.Max(view.Ceiling, 28);
            }
            else if (line.Contains("candidate_preflight_started"))
            {
                int parsedIndex;
                int parsedTotal;
                string indexText = GetValue(line, "candidate_index");
                string totalText = GetValue(line, "candidate_total");
                if (Int32.TryParse(indexText, out parsedIndex) && parsedIndex > 0) candidateIndex = parsedIndex;
                else candidateIndex++;
                if (Int32.TryParse(totalText, out parsedTotal) && parsedTotal > 0) candidateTotal = parsedTotal;
                string totalLabel = candidateTotal > 0 ? candidateTotal.ToString() : "?";
                string discoveredLabel = discoveredTotal > 0 ? discoveredTotal.ToString() : totalLabel;
                view.Nodes = "✅ 已发现 " + discoveredLabel + " 条候选线路 · 正在验证 " + candidateIndex.ToString() + "/" + totalLabel;
                view.Headline = "正在逐条验证候选线路…";
            }
            else if (line.Contains("candidate_preflight_passed"))
            {
                int parsedIndex;
                int parsedTotal;
                if (Int32.TryParse(GetValue(line, "candidate_index"), out parsedIndex) && parsedIndex > 0) candidateIndex = parsedIndex;
                if (Int32.TryParse(GetValue(line, "candidate_total"), out parsedTotal) && parsedTotal > 0) candidateTotal = parsedTotal;
                string passedTotalLabel = candidateTotal > 0 ? candidateTotal.ToString() : "?";
                string passedDiscoveredLabel = discoveredTotal > 0 ? discoveredTotal.ToString() : passedTotalLabel;
                view.Nodes = "✅ 已发现 " + passedDiscoveredLabel + " 条候选线路 · 已验证 " + candidateIndex.ToString() + "/" + passedTotalLabel;
            }
            else if (line.Contains("proxy_started") || line.Contains("proxy_reused"))
            {
                view.Proxy = "✅ 已建立 Antigravity 独立代理 127.0.0.1:17897";
                view.Progress = Math.Max(view.Progress, 34);
                view.Ceiling = Math.Max(view.Ceiling, 42);
            }
            else if (line.Contains("google_connectivity_passed"))
            {
                string rttStr = GetValue(line, "rtt_ms");
                string rttSuffix = string.IsNullOrEmpty(rttStr) ? "" : (" · 延迟 " + rttStr + "ms");
                view.Verification = "● Google 与 OAuth 已连通" + rttSuffix + "，正在确认出口和模型";
                view.Progress = Math.Max(view.Progress, 48);
                view.Ceiling = Math.Max(view.Ceiling, 56);
            }
            else if (line.Contains("proxy_egress_country_passed"))
            {
                string country = GetValue(line, "country");
                egressCountry = country;
                view.Verification = "● Google / OAuth 连通，出口 " + (country == "US" ? "US（美国）" : country) + "；正在验证真实模型";
                view.Headline = "基础网络通过，正在验证真实模型…";
                view.Progress = Math.Max(view.Progress, 62);
                view.Ceiling = Math.Max(view.Ceiling, 75);
            }
            else if (line.Contains("model_generation_probe_failed") || line.Contains("candidate_preflight_failed"))
            {
                view.Verification = "● 当前节点未通过，正在自动切换下一条";
                if (line.Contains("candidate_preflight_failed"))
                {
                    int parsedIndex;
                    int parsedTotal;
                    if (Int32.TryParse(GetValue(line, "candidate_index"), out parsedIndex) && parsedIndex > 0) candidateIndex = parsedIndex;
                    if (Int32.TryParse(GetValue(line, "candidate_total"), out parsedTotal) && parsedTotal > 0) candidateTotal = parsedTotal;
                    string failedTotalLabel = candidateTotal > 0 ? candidateTotal.ToString() : "?";
                    string failedDiscoveredLabel = discoveredTotal > 0 ? discoveredTotal.ToString() : failedTotalLabel;
                    view.Nodes = "✅ 已发现 " + failedDiscoveredLabel + " 条候选线路 · 第 " + candidateIndex.ToString() + "/" + failedTotalLabel + " 条未通过，切换下一条";
                }
                view.Headline = "当前线路不可用，正在自动恢复…";
            }
            else if (line.Contains("model_generation_probe_passed"))
            {
                string countryLabel = egressCountry.Length == 0 ? "目标地区" : (egressCountry == "US" ? "US（美国）" : egressCountry);
                string rttStr = GetValue(line, "rtt_ms");
                string rttSuffix = string.IsNullOrEmpty(rttStr) ? "" : (" · 延迟 " + rttStr + "ms");
                view.Verification = "✅ Google / OAuth 连通，出口 " + countryLabel + rttSuffix + "；真实模型 OK 验证通过";
                view.Headline = "网络与真实模型均已通过";
                view.Progress = Math.Max(view.Progress, 76);
                view.Ceiling = Math.Max(view.Ceiling, 82);
            }
            else if (line.Contains("localization_cdp-loader_selected") || line.Contains("localization_chromium-extension_selected"))
            {
                view.Localization = "● 中文翻译模块已准备";
                view.Progress = Math.Max(view.Progress, 84);
                view.Ceiling = Math.Max(view.Ceiling, 89);
            }
            else if (line.Contains("localization_extension_disabled"))
            {
                view.Localization = "○ 当前使用英文原版";
                view.Progress = Math.Max(view.Progress, 84);
                view.Ceiling = Math.Max(view.Ceiling, 89);
            }
            else if (line.Contains("antigravity_started"))
            {
                view.Launch = "● 正在启动 Antigravity";
                view.Headline = "验证通过，正在启动…";
                view.Progress = Math.Max(view.Progress, 91);
                view.Ceiling = Math.Max(view.Ceiling, 95);
            }
            else if (line.Contains("antigravity_ready"))
            {
                view.Launch = "✅ Antigravity 已启动并连接语言服务";
                view.Progress = Math.Max(view.Progress, 97);
                view.Ceiling = Math.Max(view.Ceiling, 99);
            }
            else if (line.Contains("localization_loader_succeeded"))
            {
                view.Localization = "✅ 中文翻译注入成功";
                view.Headline = "中文翻译注入成功，Antigravity 已就绪";
                view.Progress = 100;
                view.Ceiling = 100;
            }
        }
        return view;
    }

    private static string TranslateFailure(string logText, string stderr)
    {
        string all = logText + "\n" + stderr;
        if (all.Contains("mihomo_missing")) return "未找到兼容的 Mihomo 核心，请先安装 Clash Verge 或 Mihomo Party。";
        if (all.Contains("antigravity_missing")) return "未找到官方 Antigravity，请先完成安装。";
        if (all.Contains("target_node_not_found")) return "没有发现日本或美国候选节点，请先在代理软件中更新自己的订阅。";
        if (all.Contains("all_candidates_in_cooldown")) return "候选线路正在冷却，请稍后再试。";
        if (all.Contains("supervisor_run_busy")) return "后台正在进行一次恢复检查，请稍后查看已经打开的启动器窗口。";
        if (all.Contains("no_healthy_candidate_available")) return "本轮候选均未通过真实模型验证，稍后会重新尝试。";
        if (all.Contains("google_connectivity_failed")) return "当前线路无法稳定连接 Google，已停止错误启动。";
        if (all.Contains("model_generation_probe_failed")) return "当前账号或线路未通过真实模型验证。";
        if (all.Contains("localization_loader_failed")) return "Antigravity 已启动，但中文翻译注入失败。";
        return "启动检查没有通过，请稍后再次双击启动器。";
    }

    private static bool HasArgument(string[] args, string expected)
    {
        foreach (string arg in args) if (string.Equals(arg, expected, StringComparison.OrdinalIgnoreCase)) return true;
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
            Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + ScriptPath + "\" -RecoveryReason " + recoveryReason,
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
                    File.AppendAllText(LauncherLogPath, DateTime.Now.ToString("o") + " background=true recovery=" + recoveryReason + " exit=" + process.ExitCode + Environment.NewLine + output + Environment.NewLine + error + Environment.NewLine);
                }
                return process.ExitCode;
            }
        }
        catch (Exception ex)
        {
            try { Directory.CreateDirectory(Path.GetDirectoryName(LauncherLogPath)); File.AppendAllText(LauncherLogPath, DateTime.Now.ToString("o") + " background=true recovery=" + recoveryReason + " type=" + ex.GetType().Name + Environment.NewLine); }
            catch { }
            return 3;
        }
    }

    private static Label MakeStepLabel(string text, int top)
    {
        return new Label { Text = text, AutoSize = false, Left = 34, Top = top, Width = 540, Height = 25, Font = new Font("Microsoft YaHei UI", 9F), ForeColor = Color.FromArgb(55, 65, 81) };
    }

    private static bool IsAntigravityRunning()
    {
        try
        {
            Process[] procs = Process.GetProcessesByName("Antigravity");
            return procs != null && procs.Length > 0;
        }
        catch { return false; }
    }

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll")]
    private static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
    [DllImport("user32.dll")]
    private static extern bool BringWindowToTop(IntPtr hWnd);
    [DllImport("user32.dll")]
    private static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")]
    private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("kernel32.dll")]
    private static extern uint GetCurrentThreadId();

    private static void ActivateExistingAntigravity()
    {
        try
        {
            IntPtr targetHwnd = IntPtr.Zero;
            Process[] procs = Process.GetProcessesByName("Antigravity");
            var pids = new System.Collections.Generic.List<uint>();
            foreach (var p in procs) pids.Add((uint)p.Id);

            EnumWindows(delegate(IntPtr hWnd, IntPtr lParam)
            {
                uint pid;
                GetWindowThreadProcessId(hWnd, out pid);
                if (pids.Contains(pid) && IsWindowVisible(hWnd))
                {
                    var sb = new StringBuilder(256);
                    GetWindowText(hWnd, sb, 256);
                    string title = sb.ToString();
                    if (!string.IsNullOrEmpty(title) && !title.Contains("Notification") && !title.Contains("Hidden"))
                    {
                        targetHwnd = hWnd;
                        return false;
                    }
                }
                return true;
            }, IntPtr.Zero);

            if (targetHwnd == IntPtr.Zero)
            {
                foreach (var p in procs)
                {
                    if (p.MainWindowHandle != IntPtr.Zero)
                    {
                        targetHwnd = p.MainWindowHandle;
                        break;
                    }
                }
            }

            if (targetHwnd != IntPtr.Zero)
            {
                IntPtr fgWnd = GetForegroundWindow();
                uint dummyPid;
                uint fgThread = GetWindowThreadProcessId(fgWnd, out dummyPid);
                uint currentThread = GetCurrentThreadId();

                if (fgThread != currentThread && fgThread != 0)
                {
                    AttachThreadInput(currentThread, fgThread, true);
                }

                if (IsIconic(targetHwnd))
                {
                    ShowWindowAsync(targetHwnd, 9); // SW_RESTORE
                }
                else
                {
                    ShowWindowAsync(targetHwnd, 5); // SW_SHOW
                }

                BringWindowToTop(targetHwnd);
                SetForegroundWindow(targetHwnd);

                if (fgThread != currentThread && fgThread != 0)
                {
                    AttachThreadInput(currentThread, fgThread, false);
                }
            }
        }
        catch { }
    }

    private static int ShowAlreadyRunningPrompt()
    {
        int userChoice = 0; // 0 = 激活反重力并退出, 1 = 强制重跑自愈, 2 = 打开中控台, 3 = 取消退出
        using (var dlg = new Form())
        {
            dlg.Text = "Antigravity 智能启动器";
            dlg.ClientSize = new Size(540, 340);
            dlg.FormBorderStyle = FormBorderStyle.FixedDialog;
            dlg.StartPosition = FormStartPosition.CenterScreen;
            dlg.MaximizeBox = false;
            dlg.MinimizeBox = false;
            dlg.BackColor = Color.FromArgb(215, 229, 242);
            dlg.Font = new Font("Microsoft YaHei UI", 9F);

            string icoPath = Path.Combine(AppDirectory, "Antigravity-Launcher.ico");
            if (File.Exists(icoPath)) { try { dlg.Icon = new Icon(icoPath); } catch { } }

            var card = new GlassPanel { Left = 16, Top = 14, Width = 508, Height = 312 };

            var badge = new Label
            {
                Text = "独立代理 127.0.0.1:17897 正常工作 · 守护中",
                Left = 24, Top = 16, Width = 460, Height = 28,
                TextAlign = ContentAlignment.MiddleCenter,
                BackColor = Color.FromArgb(220, 231, 245),
                ForeColor = Color.FromArgb(30, 82, 160),
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold)
            };

            var lblTitle = new Label
            {
                Text = "💡 Antigravity 已经在正常运行中",
                Left = 24, Top = 54, Width = 460, Height = 30,
                Font = new Font("Microsoft YaHei UI", 14F, FontStyle.Bold),
                ForeColor = Color.FromArgb(20, 35, 55)
            };

            var lblDesc = new Label
            {
                Text = "当前代理网络工作正常，正在编写的代码不会受到任何影响。\n您可以直接进入软件，也可以根据需要进行操作：",
                Left = 26, Top = 90, Width = 456, Height = 40,
                ForeColor = Color.FromArgb(92, 110, 132)
            };

            var btnSwitch = new Button
            {
                Text = "👉 直接进入反重力 (继续写代码)",
                Left = 24, Top = 140, Width = 460, Height = 44,
                BackColor = Color.FromArgb(37, 99, 235),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 10.5F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnSwitch.FlatAppearance.BorderSize = 0;
            btnSwitch.Click += delegate { userChoice = 0; dlg.Close(); };

            var btnPanel = new Button
            {
                Text = "⚡ 打开节点中控台",
                Left = 24, Top = 196, Width = 222, Height = 38,
                BackColor = Color.FromArgb(243, 247, 252),
                ForeColor = Color.FromArgb(30, 64, 175),
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnPanel.FlatAppearance.BorderColor = Color.FromArgb(191, 219, 254);
            btnPanel.Click += delegate { userChoice = 2; dlg.Close(); };

            var btnForce = new Button
            {
                Text = "🔄 强制重新自愈检测",
                Left = 262, Top = 196, Width = 222, Height = 38,
                BackColor = Color.FromArgb(254, 242, 242),
                ForeColor = Color.FromArgb(185, 28, 28),
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnForce.FlatAppearance.BorderColor = Color.FromArgb(254, 202, 202);
            btnForce.Click += delegate { userChoice = 1; dlg.Close(); };

            var btnCancel = new Label
            {
                Text = "误触请直接回车进入，或点击右上角 [X] / 按 Esc 取消",
                Left = 24, Top = 248, Width = 460, Height = 22,
                TextAlign = ContentAlignment.MiddleCenter,
                ForeColor = Color.FromArgb(120, 135, 155),
                Font = new Font("Microsoft YaHei UI", 8.5F)
            };

            card.Controls.AddRange(new Control[] { badge, lblTitle, lblDesc, btnSwitch, btnPanel, btnForce, btnCancel });
            dlg.Controls.Add(card);
            dlg.AcceptButton = btnSwitch;
            dlg.FormClosing += delegate(object s, FormClosingEventArgs e)
            {
                if (dlg.DialogResult == DialogResult.Cancel) userChoice = 3;
            };

            dlg.ShowDialog();
        }
        return userChoice;
    }

    private static void EnsureNodeTrayRunning(bool showPanel = false)
    {
        try
        {
            if (showPanel)
            {
                try
                {
                    EventWaitHandle evt;
                    if (EventWaitHandle.TryOpenExisting(@"Local\AntigravityNodeTrayShowPanel", out evt))
                    {
                        evt.Set();
                        evt.Dispose();
                    }
                }
                catch { }
            }

            string trayExe = Path.Combine(AppDirectory, "Antigravity-NodeTray.exe");
            if (!File.Exists(trayExe))
            {
                string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                string[] candidates = new string[]
                {
                    Path.Combine(localAppData, @"Antigravity\launcher\Antigravity-NodeTray.exe"),
                    Path.Combine(localAppData, @"Antigravity\launcher-v1.0\Antigravity-NodeTray.exe")
                };
                foreach (string c in candidates)
                {
                    if (File.Exists(c)) { trayExe = c; break; }
                }
            }
            if (!File.Exists(trayExe)) return;

            Process.Start(new ProcessStartInfo
            {
                FileName = trayExe,
                Arguments = showPanel ? "--show-panel" : "",
                WorkingDirectory = Path.GetDirectoryName(trayExe),
                UseShellExecute = true
            });
        }
        catch { }
    }

    [STAThread]
    private static int Main(string[] args)
    {
        bool backgroundMode = HasArgument(args, "--background");
        bool forceLaunch = HasArgument(args, "--force-launch");

        // 智能防误触分流：如果 Antigravity 已经在正常运行中，弹窗让用户选择，绝不打断代码！
        if (!backgroundMode && !forceLaunch && IsAntigravityRunning())
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            int choice = ShowAlreadyRunningPrompt();
            if (choice == 0) // 直接进入反重力
            {
                ActivateExistingAntigravity();
                EnsureNodeTrayRunning(false);
                return 0;
            }
            if (choice == 2) // 打开节点中控台
            {
                EnsureNodeTrayRunning(true);
                return 0;
            }
            if (choice == 3) // 取消退出
            {
                return 0;
            }
            // choice == 1: 强制重新自愈检测，继续向下执行！
        }

        // Background repairs must never occupy the foreground launcher's
        // single-instance slot. Otherwise a hidden watcher repair makes a
        // user's double-click show a misleading "already checking" dialog.
        if (backgroundMode)
        {
            bool backgroundCreated;
            using (var backgroundMutex = new Mutex(true, @"Local\AntigravitySelfHealingLauncherBackground", out backgroundCreated))
            {
                if (!backgroundCreated) return 0;
                if (!File.Exists(ScriptPath)) return 2;
                int backgroundResult = RunBackgroundRepair(GetRecoveryReason(args));
                if (backgroundResult == 0) EnsureWatcherRunning();
                return backgroundResult;
            }
        }

        bool createdNew;
        using (var mutex = new Mutex(true, @"Local\AntigravitySelfHealingLauncher", out createdNew))
        {
            if (!createdNew)
            {
                ActivateExistingLauncher();
                return 0;
            }
            if (!File.Exists(ScriptPath))
            {
                MessageBox.Show("缺少 Antigravity 恢复脚本：\n" + ScriptPath, "Antigravity 启动器错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 2;
            }

            string recoveryReason = GetRecoveryReason(args);

            try
            {
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);
                var form = new Form { Text = "Antigravity 智能启动器", ClientSize = new Size(640, 430), FormBorderStyle = FormBorderStyle.FixedDialog, MaximizeBox = false, MinimizeBox = true, StartPosition = FormStartPosition.CenterScreen, ShowInTaskbar = true, BackColor = Color.FromArgb(215, 229, 242), Font = new Font("Microsoft YaHei UI", 9F) };
                
                string icoPath = Path.Combine(AppDirectory, "Antigravity-Launcher.ico");
                if (File.Exists(icoPath)) { try { form.Icon = new Icon(icoPath); } catch { } }

                bool allowClose = false;
                bool userCancelled = false;
                Process supervisorProc = null;

                // 允许用户随时点击右上角叉叉退出，绝不强制锁定！
                form.FormClosing += delegate(object sender, FormClosingEventArgs e)
                {
                    if (!allowClose)
                    {
                        userCancelled = true;
                        try
                        {
                            if (supervisorProc != null && !supervisorProc.HasExited)
                            {
                                supervisorProc.Kill();
                            }
                        }
                        catch { }
                    }
                };

                var card = new GlassPanel { Left = 18, Top = 16, Width = 604, Height = 396 };
                var title = new Label { Text = "Antigravity 智能启动器", Left = 28, Top = 20, Width = 548, Height = 34, Font = new Font("Microsoft YaHei UI", 16F, FontStyle.Bold), ForeColor = Color.FromArgb(20, 35, 55) };
                var subtitle = new Label { Text = "自动检查独立代理、节点、真实模型与中文界面", Left = 30, Top = 56, Width = 544, Height = 22, ForeColor = Color.FromArgb(92, 110, 132) };
                var badge = new Label { Text = "独立代理 17897   ·   美国优先，日本兜底   ·   Clash 7897 保持不变", Left = 28, Top = 88, Width = 548, Height = 30, TextAlign = ContentAlignment.MiddleCenter, BackColor = Color.FromArgb(220, 231, 245), ForeColor = Color.FromArgb(30, 82, 160), Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold) };
                var headline = new Label { Text = "正在读取本机代理配置…", Left = 30, Top = 132, Width = 544, Height = 28, Font = new Font("Microsoft YaHei UI", 10F, FontStyle.Bold), ForeColor = Color.FromArgb(31, 50, 72) };
                var proxyStep = MakeStepLabel("● 正在建立 Antigravity 独立代理 127.0.0.1:17897", 168);
                var nodeStep = MakeStepLabel("○ 正在发现本机候选节点", 196);
                var verificationStep = MakeStepLabel("○ 等待 Google、OAuth、日美出口和真实模型验证", 224);
                var localizationStep = MakeStepLabel("○ 等待注入中文翻译", 252);
                var launchStep = MakeStepLabel("○ 等待启动 Antigravity", 280);
                var progress = new StatusProgress { Left = 30, Top = 320, Width = 544, Font = new Font("Segoe UI", 8.5F, FontStyle.Bold), ProgressValue = 1 };
                var footer = new Label { Text = "美国优先、日本兜底；地区误判先冷却，不修改 Clash 模式或日常节点。", Left = 30, Top = 357, Width = 544, Height = 24, ForeColor = Color.FromArgb(92, 110, 132), TextAlign = ContentAlignment.MiddleCenter };
                card.Controls.AddRange(new Control[] { title, subtitle, badge, headline, proxyStep, nodeStep, verificationStep, localizationStep, launchStep, progress, footer });
                form.Controls.Add(card);
                form.Show();
                Application.DoEvents();

                long logStartOffset = GetLogLength();
                int displayedProgress = 1;
                int animationTick = 0;
                DateTime supervisorRequestedUtc = DateTime.UtcNow;
                using (var process = Process.Start(CreateSupervisorStartInfo(recoveryReason)))
                {
                    supervisorProc = process;
                    if (process == null) throw new InvalidOperationException("Windows 未能启动检查进程。");
                    var output = new StringBuilder();
                    var error = new StringBuilder();
                    process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) output.AppendLine(e.Data); };
                    process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) error.AppendLine(e.Data); };
                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    while (!process.HasExited)
                    {
                        if (userCancelled) return 0;
                        StatusView status = BuildStatus(ReadLogSince(logStartOffset));
                        headline.Text = status.Headline;
                        proxyStep.Text = status.Proxy;
                        nodeStep.Text = status.Nodes;
                        verificationStep.Text = status.Verification;
                        localizationStep.Text = status.Localization;
                        launchStep.Text = status.Launch;
                        animationTick++;
                        if (displayedProgress < status.Progress)
                        {
                            displayedProgress += Math.Max(1, (status.Progress - displayedProgress + 3) / 4);
                        }
                        else if (displayedProgress < status.Ceiling && animationTick % 2 == 0)
                        {
                            displayedProgress++;
                        }
                        progress.ProgressValue = displayedProgress;
                        Application.DoEvents();
                        Thread.Sleep(250);
                    }
                    if (userCancelled) return 0;
                    process.WaitForExit();
                    int result = process.ExitCode;
                    string currentLog = ReadLogSince(logStartOffset);
                    if (result == 4)
                    {
                        headline.Text = "已有后台恢复正在进行，正在接收结果…";
                        verificationStep.Text = "● 后台检查已占用恢复通道，等待它完成";
                        launchStep.Text = "● 等待后台恢复完成后接管 Antigravity";
                        Application.DoEvents();
                        string concurrentLog;
                        bool joined = WaitForConcurrentRecovery(
                            supervisorRequestedUtc,
                            logStartOffset,
                            delegate(StatusView status)
                            {
                                headline.Text = status.Headline;
                                proxyStep.Text = status.Proxy;
                                nodeStep.Text = status.Nodes;
                                verificationStep.Text = status.Verification;
                                localizationStep.Text = status.Localization;
                                launchStep.Text = status.Launch;
                                Application.DoEvents();
                            },
                            out concurrentLog);
                        currentLog = concurrentLog;
                        if (joined) result = 0;
                    }
                    if (result != 0)
                    {
                        Directory.CreateDirectory(Path.GetDirectoryName(LauncherLogPath));
                        File.AppendAllText(LauncherLogPath, DateTime.Now.ToString("o") + " exit=" + result + Environment.NewLine + output + Environment.NewLine + error + Environment.NewLine);
                        allowClose = true;
                        form.Close();
                        MessageBox.Show(TranslateFailure(currentLog, error.ToString()), "Antigravity 启动未通过", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }
                    else
                    {
                        StatusView status = BuildStatus(currentLog);
                        headline.Text = "中文翻译注入成功，Antigravity 已就绪";
                        proxyStep.Text = status.Proxy;
                        nodeStep.Text = status.Nodes;
                        verificationStep.Text = status.Verification;
                        localizationStep.Text = status.Localization;
                        launchStep.Text = status.Launch;
                        progress.ProgressValue = 100;
                        Application.DoEvents();
                        Thread.Sleep(1400);
                        allowClose = true;
                        form.Close();
                    }
                    if (result == 0)
                    {
                        EnsureWatcherRunning();
                        EnsureNodeTrayRunning();
                    }
                    return result;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("无法启动 Antigravity：\n" + ex.Message, "Antigravity 启动器错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 3;
            }
        }
    }
}
