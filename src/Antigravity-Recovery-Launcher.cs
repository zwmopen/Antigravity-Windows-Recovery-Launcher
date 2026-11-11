using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

[assembly: AssemblyTitle("Antigravity 启动器")]
[assembly: AssemblyProduct("Antigravity 启动器")]
[assembly: AssemblyCopyright("Copyright © 2026 zwmopen")]
[assembly: AssemblyVersion("2.9.29.0")]
[assembly: AssemblyFileVersion("2.9.29.0")]
[assembly: AssemblyInformationalVersion("2.9.29")]

namespace AntigravityLauncher
{
    internal static class Program
    {
        internal static readonly string AppDirectory = AppDomain.CurrentDomain.BaseDirectory;
        internal static readonly string ScriptPath = Path.Combine(AppDirectory, "Antigravity-ProxySupervisor.ps1");
        internal static readonly string WatcherPath = Path.Combine(AppDirectory, "Antigravity-AccountWatcher.exe");
        internal static readonly string RuntimeDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Antigravity", "private-proxy");
        internal static readonly string LauncherLogPath = Path.Combine(RuntimeDirectory, "launcher-error.log");
        internal static readonly string SupervisorLogPath = Path.Combine(RuntimeDirectory, "supervisor.log");
        internal static readonly string SupervisorStatePath = Path.Combine(RuntimeDirectory, "supervisor-state.json");
        internal static readonly string LauncherSettingsPath = Path.Combine(RuntimeDirectory, "launcher-settings.json");
        internal static readonly string IconPath = Path.Combine(AppDirectory, "Antigravity-Launcher.ico");

        private const string SingleInstanceMutexName = @"Local\AntigravityLauncherSingleInstance";
        private const string BackgroundMutexName = @"Local\AntigravitySelfHealingLauncherBackground";
        internal const string SupervisorMutexName = @"Local\AntigravitySupervisorRun";

        private static Mutex singleInstanceMutex;
        [DllImport("user32.dll")]
        private static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
        private static IntPtr EnterSharpCardDpiContext() {
            try { return SetThreadDpiAwarenessContext(new IntPtr(-2)); } catch { return IntPtr.Zero; }
        }


        internal static void TraceLog(string msg)
        {
            try
            {
                string dir = Path.GetDirectoryName(LauncherLogPath);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                if (File.Exists(LauncherLogPath) && new FileInfo(LauncherLogPath).Length > 1024 * 1024)
                {
                    string backup = LauncherLogPath + ".1";
                    try
                    {
                        if (File.Exists(backup)) File.Delete(backup);
                        File.Move(LauncherLogPath, backup);
                    }
                    catch { }
                }
                File.AppendAllText(LauncherLogPath, DateTime.Now.ToString("o") + " [TRACE] " + msg + Environment.NewLine);
            }
            catch { }
        }

        [STAThread]
        private static int Main(string[] args)
        {
            EnsureInteractiveDesktop();
            TraceLog("Main invoked: " + (args != null ? string.Join(" ", args) : "null"));
            bool backgroundMode = HasArgument(args, "--background");
            bool forceLaunch = HasArgument(args, "--force-launch");
            bool betaMode = HasArgument(args, "--beta");

            // Beta 模式：写入 beta.flag 文件，供 Python 守护进程读取以启用测试版行为
            string betaFlagPath = Path.Combine(RuntimeDirectory, "beta.flag");
            if (betaMode)
            {
                try
                {
                    Directory.CreateDirectory(RuntimeDirectory);
                    File.WriteAllText(betaFlagPath, "1");
                    TraceLog("Beta mode enabled. beta.flag written.");
                }
                catch { }
            }

            // 1. 后台静默自愈模式 (由 AccountWatcher 调度，无任何 UI)
            if (backgroundMode)
            {
                TraceLog("Running in backgroundMode");
                bool backgroundCreated;
                using (var backgroundMutex = new Mutex(true, BackgroundMutexName, out backgroundCreated))
                {
                    if (!backgroundCreated) return 0;
                    if (!File.Exists(ScriptPath)) return 2;
                    int backgroundResult = RunBackgroundRepair(GetRecoveryReason(args));
                    if (backgroundResult == 0) EnsureWatcherRunning();
                    return backgroundResult;
                }
            }

            // 2. 检查是否已有启动器实例在运行 (互斥锁防重入)
            bool createdNew;
            try
            {
                singleInstanceMutex = new Mutex(true, SingleInstanceMutexName, out createdNew);
            }
            catch (AbandonedMutexException)
            {
                createdNew = true;
            }

            if (!createdNew && !forceLaunch)
            {
                TraceLog("Another launcher instance is already active.");
                return 0;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);

            // 3. 检查 Antigravity 是否已经在运行中 (热启动场景：带 5 秒自动进入的双选卡片)
            bool antigravityRunning = IsAntigravityRunning();
            TraceLog("antigravityRunning=" + antigravityRunning + ", forceLaunch=" + forceLaunch);

            if (antigravityRunning && !forceLaunch)
            {
                TraceLog("Displaying AntigravityHotLaunchChoiceForm...");
                IntPtr previousDpiContext = EnterSharpCardDpiContext();
                var choiceForm = new AntigravityHotLaunchChoiceForm();
                if (HasArgument(args, "--inspect-card")) choiceForm.PauseCountdown();
                try { Application.Run(choiceForm); }
                finally { if (previousDpiContext != IntPtr.Zero) { try { SetThreadDpiAwarenessContext(previousDpiContext); } catch { } } }

                if (choiceForm.Action == HotLaunchAction.Activate)
                {
                    TraceLog("Hot launch: activating existing main window...");
                    string targetToSwitch = !string.IsNullOrEmpty(choiceForm.BestTargetEmail) ? choiceForm.BestTargetEmail : choiceForm.SelectedEmail;
                    if ((choiceForm.AccountMismatch || choiceForm.NeedSwitch) && !string.IsNullOrEmpty(targetToSwitch))
                    {
                        TraceLog("Hot launch: account switch required (mismatch=" + choiceForm.AccountMismatch + ", needSwitch=" + choiceForm.NeedSwitch + "); triggering smart switch to " + targetToSwitch);
                        TriggerSmartSwitch(targetToSwitch);
                    }
                    bool activated = ActivateExistingAntigravity();
                    TraceLog("Activate result: " + activated);
                    if (activated) return 0;
                    TraceLog("Hot launch: no activatable window; falling back to visible launch recovery.");
                    forceLaunch = true;
                }
                else if (choiceForm.Action == HotLaunchAction.Repair)
                {
                    TraceLog("Hot launch: user selected Repair. Launching recovery capsule...");
                    forceLaunch = true;
                }
                else
                {
                    TraceLog("Hot launch: user dismissed choice form.");
                    return 0;
                }
            }

            // 4. 冷启动 / 重启修复：展示具备清晰通路与链路核验反馈的极简状态卡片
            TraceLog("Displaying AntigravityLaunchCapsuleForm...");
            string resolvedReason = forceLaunch ? "UserRequestedRepair" : GetRecoveryReason(args);
            var capsule = new AntigravityLaunchCapsuleForm(resolvedReason);
            Application.Run(capsule);

            if (capsule.ExitCode == 0)
            {
                bool activated = ActivateExistingAntigravity();
                EnsureWatcherRunning();
                if (!activated)
                {
                    TraceLog("Launch completed but no foreground window was verified.");
                    MessageBox.Show("未能打开反重力主窗口，启动日志已记录失败原因。请重新点击启动器重试。", "反重力启动失败", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return 1;
                }
            }

            return capsule.ExitCode;
        }

        internal static bool HasArgument(string[] args, string expected)
        {
            if (args == null) return false;
            foreach (string arg in args)
            {
                if (string.Equals(arg, expected, StringComparison.OrdinalIgnoreCase)) return true;
            }
            return false;
        }

        internal static string GetRecoveryReason(string[] args)
        {
            if (args == null) return "Startup";
            foreach (string arg in args)
            {
                const string prefix = "--recovery-reason=";
                if (!arg.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) continue;
                string value = arg.Substring(prefix.Length);
                if (value == "NetworkFailure" || value == "LocationFailure" || value == "AccountChange" || value == "cockpit_account_changed") return value;
            }
            return "Startup";
        }

        internal static bool IsOwnWatcherRunning()
        {
            try
            {
                foreach (Process p in Process.GetProcessesByName("Antigravity-AccountWatcher"))
                {
                    try
                    {
                        string path = p.MainModule == null ? "" : p.MainModule.FileName;
                        if (string.Equals(path, WatcherPath, StringComparison.OrdinalIgnoreCase)) return true;
                    }
                    catch { }
                    finally { p.Dispose(); }
                }
            }
            catch { }
            return false;
        }

        internal static void EnsureWatcherRunning()
        {
            try
            {
                if (File.Exists(WatcherPath) && !IsOwnWatcherRunning())
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = WatcherPath,
                        WorkingDirectory = AppDirectory,
                        UseShellExecute = true,
                        WindowStyle = ProcessWindowStyle.Hidden
                    });
                }
            }
            catch { }

            EnsureQuotaWatcherRunning();
        }

        internal static string ResolvePythonw()
        {
            string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string[] candidates = new[]
            {
                Path.Combine(localApp, @"Programs\Python\Python311\pythonw.exe"),
                Path.Combine(localApp, @"Programs\Python\Python312\pythonw.exe"),
                Path.Combine(localApp, @"Programs\Python\Python310\pythonw.exe"),
                Path.Combine(localApp, @"Programs\Python\Python313\pythonw.exe")
            };
            foreach (var c in candidates)
            {
                if (File.Exists(c)) return c;
            }
            return "pythonw.exe";
        }

        internal static void TriggerSmartSwitch(string targetEmail)
        {
            try
            {
                string pyScript = Path.Combine(AppDirectory, "antigravity_smart_switch.py");
                if (!File.Exists(pyScript)) return;
                string pyw = ResolvePythonw();
                Process.Start(new ProcessStartInfo
                {
                    FileName = pyw,
                    Arguments = "\"" + pyScript + "\" --target \"" + targetEmail + "\" --force",
                    WorkingDirectory = AppDirectory,
                    UseShellExecute = false,
                    CreateNoWindow = true
                });
            }
            catch (Exception ex)
            {
                TraceLog("TriggerSmartSwitch error: " + ex.Message);
            }
        }

        internal static void EnsureQuotaWatcherRunning()
        {
            try
            {
                string pyScript = Path.Combine(AppDirectory, "antigravity_smart_switch.py");
                if (!File.Exists(pyScript)) return;

                bool mutexExists = false;
                try
                {
                    using (var m = Mutex.OpenExisting(@"Local\AntigravitySmartQuotaWatcher"))
                    {
                        mutexExists = true;
                    }
                }
                catch
                {
                    mutexExists = false;
                }

                if (mutexExists) return;

                string pyw = ResolvePythonw();
                Process.Start(new ProcessStartInfo
                {
                    FileName = pyw,
                    Arguments = "\"" + pyScript + "\" --watch",
                    WorkingDirectory = AppDirectory,
                    UseShellExecute = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                });
            }
            catch { }
        }

        internal static bool IsAntigravityRunning()
        {
            // Plugins also run under Antigravity.exe in ELECTRON_RUN_AS_NODE mode.
            // A process name alone does not mean there is an editor to enter.
            return FindAntigravityMainWindow() != IntPtr.Zero;
        }

        internal static bool IsSupervisorRunning()
        {
            try
            {
                using (var m = Mutex.OpenExisting(SupervisorMutexName))
                {
                    return true;
                }
            }
            catch
            {
                return false;
            }
        }

        // ==========================================
        // Win32 穿透唤醒与置顶逻辑 (突破 Windows 11 焦点限制)
        // ==========================================
        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool CloseDesktop(IntPtr hDesktop);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool EnumDesktopWindows(IntPtr hDesktop, EnumWindowsProc lpfn, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        [DllImport("user32.dll")]
        private static extern int GetClassName(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll")]
        private static extern bool IsIconic(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool SetThreadDesktop(IntPtr hDesktop);

        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

        [DllImport("user32.dll")]
        private static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        private static extern bool BringWindowToTop(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll")]
        private static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

        [DllImport("user32.dll")]
        private static extern void SwitchToThisWindow(IntPtr hWnd, bool fUnknown);

        [DllImport("user32.dll")]
        private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);

        [DllImport("user32.dll")]
        internal static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
        internal static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
        internal static readonly IntPtr HWND_NOTOPMOST = new IntPtr(-2);
        internal const uint SWP_NOMOVE = 0x0002;
        internal const uint SWP_NOSIZE = 0x0001;
        internal const uint SWP_NOACTIVATE = 0x0010;
        internal const uint SWP_SHOWWINDOW = 0x0040;

        [DllImport("user32.dll")]
        internal static extern bool ReleaseCapture();

        [DllImport("user32.dll")]
        internal static extern int SendMessage(IntPtr hWnd, int Msg, int wParam, int lParam);

        [DllImport("dwmapi.dll")]
        internal static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);

        internal const int DWMWA_WINDOW_CORNER_PREFERENCE = 33;
        internal const int DWMWCP_ROUND = 2;

        [DllImport("kernel32.dll")]
        private static extern uint GetCurrentThreadId();

        [StructLayout(LayoutKind.Sequential)]
        private struct RECT { public int Left, Top, Right, Bottom; }

        internal static void EnsureInteractiveDesktop()
        {
            try
            {
                IntPtr hDesk = OpenDesktop("default", 0, false, 0x01FF);
                if (hDesk != IntPtr.Zero)
                {
                    SetThreadDesktop(hDesk);
                }
            }
            catch { }
        }

        internal static IntPtr FindAntigravityMainWindow()
        {
            var pids = new HashSet<uint>();
            try
            {
                foreach (var p in Process.GetProcessesByName("Antigravity"))
                {
                    pids.Add((uint)p.Id);
                    p.Dispose();
                }
            }
            catch { }

            if (pids.Count == 0) return IntPtr.Zero;

            EnsureInteractiveDesktop();

            IntPtr foundHwnd = IntPtr.Zero;
            IntPtr fallbackHwnd = IntPtr.Zero;

            EnumWindowsProc checkWindow = delegate(IntPtr hWnd, IntPtr lParam)
            {
                uint pid;
                GetWindowThreadProcessId(hWnd, out pid);
                if (!pids.Contains(pid)) return true;
                if (!IsWindowVisible(hWnd)) return true;

                var sbClass = new StringBuilder(256);
                GetClassName(hWnd, sbClass, 256);
                string className = sbClass.ToString();
                if (className.Contains("Host") || className.Contains("Dde") || className.Contains("IME") || className.Contains("PowerMessage"))
                    return true;

                RECT r;
                GetWindowRect(hWnd, out r);
                bool isMin = IsIconic(hWnd) || r.Left < -5000;
                if (!isMin)
                {
                    int width = r.Right - r.Left;
                    int height = r.Bottom - r.Top;
                    if (width < 300 || height < 200) return true;
                }

                if (className == "Chrome_WidgetWin_1")
                {
                    foundHwnd = hWnd;
                    return false;
                }

                if (fallbackHwnd == IntPtr.Zero)
                {
                    fallbackHwnd = hWnd;
                }
                return true;
            };

            EnumWindows(checkWindow, IntPtr.Zero);
            if (foundHwnd == IntPtr.Zero)
            {
                IntPtr hDesk = OpenDesktop("default", 0, false, 0x01FF);
                if (hDesk != IntPtr.Zero)
                {
                    try { EnumDesktopWindows(hDesk, checkWindow, IntPtr.Zero); }
                    catch { }
                }
            }

            IntPtr result = foundHwnd != IntPtr.Zero ? foundHwnd : fallbackHwnd;
            TraceLog("FindAntigravityMainWindow found HWND=" + result);
            return result;
        }

        internal static bool ActivateExistingAntigravity()
        {
            EnsureInteractiveDesktop();
            IntPtr hWnd = FindAntigravityMainWindow();
            if (hWnd == IntPtr.Zero)
            {
                TraceLog("ActivateExistingAntigravity: no window handle found.");
                return false;
            }

            try
            {
                RECT r;
                GetWindowRect(hWnd, out r);
                bool isMin = IsIconic(hWnd) || r.Left < -5000;
                TraceLog("ActivateExistingAntigravity: target HWND=" + hWnd + ", isMin=" + isMin + ", Rect=(" + r.Left + "," + r.Top + "," + r.Right + "," + r.Bottom + ")");

                if (isMin)
                {
                    ShowWindow(hWnd, 9); // SW_RESTORE (synchronous restoration)
                }
                else
                {
                    ShowWindow(hWnd, 5); // SW_SHOW
                }

                IntPtr fgWnd = GetForegroundWindow();
                uint fgPid;
                uint fgThread = GetWindowThreadProcessId(fgWnd, out fgPid);
                uint curThread = GetCurrentThreadId();
                bool attached = false;
                if (fgThread != 0 && fgThread != curThread)
                {
                    attached = AttachThreadInput(curThread, fgThread, true);
                }

                keybd_event(0x12, 0, 0, 0); // Alt down
                keybd_event(0x12, 0, 2, 0); // Alt up

                BringWindowToTop(hWnd);
                SetForegroundWindow(hWnd);
                SwitchToThisWindow(hWnd, true);

                if (attached)
                {
                    AttachThreadInput(curThread, fgThread, false);
                }

                for (int attempt = 0; attempt < 10; attempt++)
                {
                    if (GetForegroundWindow() == hWnd)
                    {
                        TraceLog("ActivateExistingAntigravity: verified foreground HWND=" + hWnd);
                        return true;
                    }
                    Thread.Sleep(50);
                }
                TraceLog("ActivateExistingAntigravity: foreground verification failed HWND=" + hWnd);
                return false;
            }
            catch (Exception ex)
            {
                TraceLog("ActivateExistingAntigravity error: " + ex.Message);
                return false;
            }
        }

        private static int RunBackgroundRepair(string recoveryReason)
        {
            var output = new StringBuilder();
            var error = new StringBuilder();
            try
            {
                var psi = new ProcessStartInfo
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
                using (var process = Process.Start(psi))
                {
                    if (process == null) return 3;
                    process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) output.AppendLine(e.Data); };
                    process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) error.AppendLine(e.Data); };
                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    process.WaitForExit();
                    if (process.ExitCode != 0)
                    {
                        TraceLog("background=true recovery=" + recoveryReason + " exit=" + process.ExitCode + Environment.NewLine + output + Environment.NewLine + error);
                    }
                    return process.ExitCode;
                }
            }
            catch (Exception ex)
            {
                TraceLog("background=true recovery=" + recoveryReason + " type=" + ex.GetType().Name);
                return 3;
            }
        }

        internal static Image LoadIconOrPng(string filePath)
        {
            try
            {
                if (!File.Exists(filePath)) return null;
                byte[] bytes = File.ReadAllBytes(filePath);
                // 检索 ICO 文件内部嵌入的 256x256 高清 PNG 头部
                for (int i = 0; i <= bytes.Length - 8; i++)
                {
                    if (bytes[i] == 0x89 && bytes[i + 1] == 0x50 && bytes[i + 2] == 0x4E && bytes[i + 3] == 0x47)
                    {
                        var ms = new MemoryStream(bytes, i, bytes.Length - i);
                        return Image.FromStream(ms);
                    }
                }
                using (var ico = new Icon(filePath))
                {
                    return ico.ToBitmap();
                }
            }
            catch { return null; }
        }
    }

    // ==========================================
    // 视觉核心：精巧拟态圆角进度条 (CapsuleProgress)
    // ==========================================
    internal sealed class CapsuleProgress : Control
    {
        private int currentValue = 0;

        internal CapsuleProgress()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
            Height = 7;
        }

        internal int ProgressValue
        {
            get { return currentValue; }
            set { currentValue = Math.Max(0, Math.Min(100, value)); Invalidate(); }
        }

        private static GraphicsPath RoundedPill(Rectangle r)
        {
            var p = new GraphicsPath();
            int d = Math.Max(1, r.Height);
            p.AddArc(r.Left, r.Top, d, d, 90, 180);
            p.AddArc(r.Right - d, r.Top, d, d, 270, 180);
            p.CloseFigure();
            return p;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var track = new Rectangle(0, 0, Width - 1, Height - 1);
            if (track.Width <= 0 || track.Height <= 0) return;

            using (var trackPath = RoundedPill(track))
            using (var trackBrush = new SolidBrush(Color.FromArgb(220, 230, 242)))
            {
                e.Graphics.FillPath(trackBrush, trackPath);
            }

            if (currentValue > 0)
            {
                int fillWidth = Math.Max(Height, (int)Math.Round(track.Width * currentValue / 100.0));
                var fill = new Rectangle(track.Left, track.Top, Math.Min(track.Width, fillWidth), track.Height);
                using (var fillPath = RoundedPill(fill))
                using (var fillBrush = new LinearGradientBrush(fill, Color.FromArgb(96, 165, 250), Color.FromArgb(37, 99, 235), 0F))
                {
                    e.Graphics.FillPath(fillBrush, fillPath);
                }
            }
        }
    }

    // ==========================================
    // 视觉核心：轻巧关闭按钮 (CapsuleCloseButton)
    // ==========================================
    internal sealed class CapsuleCloseButton : Control
    {
        private bool isHovered = false;

        public CapsuleCloseButton()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
            Size = new Size(24, 24);
            Cursor = Cursors.Hand;
        }

        protected override void OnMouseEnter(EventArgs e) { isHovered = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { isHovered = false; Invalidate(); base.OnMouseLeave(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var rect = new Rectangle(0, 0, Width - 1, Height - 1);
            if (isHovered)
            {
                using (var path = new GraphicsPath())
                {
                    path.AddEllipse(rect);
                    using (var b = new SolidBrush(Color.FromArgb(254, 226, 226)))
                    {
                        e.Graphics.FillPath(b, path);
                    }
                }
            }
            Color tc = isHovered ? Color.FromArgb(220, 38, 38) : Color.FromArgb(148, 163, 184);
            using (var fontX = new Font("Segoe UI", 9F, FontStyle.Bold))
            using (var brushX = new SolidBrush(tc))
            using (var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center })
            {
                e.Graphics.DrawString("✕", fontX, brushX, rect, sf);
            }
        }

        protected override void WndProc(ref Message m)
        {
            const int WM_PRINTCLIENT = 0x0318;
            const int WM_PRINT = 0x0317;
            if (m.Msg == WM_PRINTCLIENT || m.Msg == WM_PRINT)
            {
                using (Graphics g = Graphics.FromHdc(m.WParam))
                {
                    OnPaint(new PaintEventArgs(g, ClientRectangle));
                }
                return;
            }
            base.WndProc(ref m);
        }
    }

    // ==========================================
    // 视觉核心：轻巧最小化按钮 (CapsuleMinimizeButton)
    // ==========================================
    internal sealed class CapsuleMinimizeButton : Control
    {
        private bool isHovered = false;

        public CapsuleMinimizeButton()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
            Size = new Size(24, 24);
            Cursor = Cursors.Hand;
        }

        protected override void OnMouseEnter(EventArgs e) { isHovered = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { isHovered = false; Invalidate(); base.OnMouseLeave(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var rect = new Rectangle(0, 0, Width - 1, Height - 1);
            if (isHovered)
            {
                using (var path = new GraphicsPath())
                {
                    path.AddEllipse(rect);
                    using (var b = new SolidBrush(Color.FromArgb(219, 234, 254)))
                    {
                        e.Graphics.FillPath(b, path);
                    }
                }
            }
            Color tc = isHovered ? Color.FromArgb(37, 99, 235) : Color.FromArgb(148, 163, 184);
            using (var pen = new Pen(tc, 2f))
            {
                pen.StartCap = LineCap.Round;
                pen.EndCap = LineCap.Round;
                int y = Height / 2;
                int pad = 6;
                e.Graphics.DrawLine(pen, pad, y, Width - pad - 1, y);
            }
        }

        protected override void WndProc(ref Message m)
        {
            const int WM_PRINTCLIENT = 0x0318;
            const int WM_PRINT = 0x0317;
            if (m.Msg == WM_PRINTCLIENT || m.Msg == WM_PRINT)
            {
                using (Graphics g = Graphics.FromHdc(m.WParam))
                {
                    OnPaint(new PaintEventArgs(g, ClientRectangle));
                }
                return;
            }
            base.WndProc(ref m);
        }
    }

    // ==========================================
    // 热启动选择动作枚举
    // ==========================================
        // ==========================================
    // 视觉核心：轻巧设置齿轮按钮 (CapsuleSettingsButton)
    // ==========================================
    internal sealed class CapsuleSettingsButton : Control
    {
        private bool isHovered = false;

        public CapsuleSettingsButton()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
            Size = new Size(22, 22);
            Cursor = Cursors.Hand;
        }

        protected override void OnMouseEnter(EventArgs e) { isHovered = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { isHovered = false; Invalidate(); base.OnMouseLeave(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var rect = new Rectangle(0, 0, Width - 1, Height - 1);
            if (isHovered)
            {
                using (var path = new GraphicsPath())
                {
                    path.AddEllipse(rect);
                    using (var b = new SolidBrush(Color.FromArgb(219, 234, 254)))
                    {
                        e.Graphics.FillPath(b, path);
                    }
                }
            }
            Color tc = isHovered ? Color.FromArgb(37, 99, 235) : Color.FromArgb(148, 163, 184);
            using (var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center })
            using (var font = new Font("Segoe UI Symbol", 10.5f))
            using (var b = new SolidBrush(tc))
            {
                e.Graphics.DrawString("⚙", font, b, new RectangleF(0, 0, Width, Height), sf);
            }
        }
    }

    internal enum HotLaunchAction { Activate, Repair, Cancel }

    // ==========================================
    // 启动器设置（持久化到 launcher-settings.json）
    // ==========================================
    internal class LauncherSettings
    {
        private bool autoResumeEnabled;
        internal bool AutoResumeEnabled { get { return autoResumeEnabled; } set { autoResumeEnabled = value; } }

        internal LauncherSettings() { autoResumeEnabled = false; }

        internal static LauncherSettings Load()
        {
            try
            {
                if (File.Exists(Program.LauncherSettingsPath))
                {
                    string json = File.ReadAllText(Program.LauncherSettingsPath, Encoding.UTF8);
                    var s = new LauncherSettings();
                    var m = System.Text.RegularExpressions.Regex.Match(json, "\"auto_resume_enabled\"\\s*:\\s*(true|false)");
                    if (m.Success) s.AutoResumeEnabled = m.Groups[1].Value == "true";
                    return s;
                }
            }
            catch { }
            return new LauncherSettings();
        }

        internal void Save()
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(Program.LauncherSettingsPath));
                string json = "{\n  \"auto_resume_enabled\": " + (AutoResumeEnabled ? "true" : "false") + "\n}\n";
                File.WriteAllText(Program.LauncherSettingsPath, json, Encoding.UTF8);
            }
            catch { }
        }
    }


    // ==========================================
    // 视觉核心：热启动拟态胶囊按钮 (HotLaunchButton)
    // ==========================================
    internal sealed class HotLaunchButton : Control
    {
        private bool isHovered = false;
        private bool isPressed = false;
        private string buttonText;
        internal bool IsPrimary { get; set; }
        internal bool IsWarning { get; set; }

        internal HotLaunchButton(string text)
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
            buttonText = text;
            AccessibleName = text;
            AccessibleRole = AccessibleRole.PushButton;
            Cursor = Cursors.Hand;
        }

        internal string ButtonText
        {
            get { return buttonText; }
            set { buttonText = value; AccessibleName = value; Invalidate(); }
        }

        protected override void OnMouseEnter(EventArgs e) { isHovered = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { isHovered = false; isPressed = false; Invalidate(); base.OnMouseLeave(e); }
        protected override void OnMouseDown(MouseEventArgs e) { if (e.Button == MouseButtons.Left) { isPressed = true; Invalidate(); } base.OnMouseDown(e); }
        protected override void OnMouseUp(MouseEventArgs e) { isPressed = false; Invalidate(); base.OnMouseUp(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;
            var r = new Rectangle(0, 0, Width - 1, Height - 1);
            using (var path = RoundedRectangle(r, 12))
            {
                Color c1 = isHovered ? Color.FromArgb(255, 255, 255) : Color.FromArgb(246, 250, 255);
                Color c2 = isHovered ? Color.FromArgb(240, 248, 255) : Color.FromArgb(232, 242, 254);
                Color border = isHovered ? Color.FromArgb(96, 165, 250) : Color.FromArgb(186, 215, 248);
                Color textColor = isHovered ? Color.FromArgb(30, 64, 175) : Color.FromArgb(29, 78, 216);

                if (isPressed)
                {
                    c1 = Color.FromArgb(219, 234, 254);
                    c2 = Color.FromArgb(191, 219, 254);
                    border = Color.FromArgb(59, 130, 246);
                    textColor = Color.FromArgb(30, 58, 138);
                }

                if (IsPrimary) {
                    if (IsWarning) {
                        c1 = isHovered ? Color.FromArgb(249, 115, 22) : Color.FromArgb(234, 88, 12);
                        c2 = Color.FromArgb(194, 65, 12);
                        border = Color.FromArgb(194, 65, 12);
                        textColor = Color.White;
                    } else {
                        c1 = isHovered ? Color.FromArgb(37, 99, 235) : Color.FromArgb(45, 108, 223);
                        c2 = Color.FromArgb(29, 78, 190);
                        border = Color.FromArgb(29, 78, 190);
                        textColor = Color.White;
                    }
                } else {
                    c1 = Color.White; c2 = Color.FromArgb(248, 250, 252);
                    border = Color.FromArgb(210, 218, 229); textColor = Color.FromArgb(51, 65, 85);
                }
                using (var fill = new LinearGradientBrush(r, c1, c2, 90F))
                using (var pen = new Pen(border, 1.2F))
                {
                    e.Graphics.FillPath(fill, path);
                    e.Graphics.DrawPath(pen, path);
                }

                using (var font = new Font("微软雅黑", 10F, FontStyle.Bold, GraphicsUnit.Point, 134))
                using (var brush = new SolidBrush(textColor))
                using (var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center })
                {
                    TextRenderer.DrawText(e.Graphics, buttonText, font, r, textColor, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.SingleLine | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPadding);
                }
            }
        }

        protected override void WndProc(ref Message m)
        {
            const int WM_PRINTCLIENT = 0x0318;
            const int WM_PRINT = 0x0317;
            if (m.Msg == WM_PRINTCLIENT || m.Msg == WM_PRINT)
            {
                using (Graphics g = Graphics.FromHdc(m.WParam))
                {
                    OnPaint(new PaintEventArgs(g, ClientRectangle));
                }
                return;
            }
            base.WndProc(ref m);
        }

        private static GraphicsPath RoundedRectangle(Rectangle r, int radius)
        {
            var path = new GraphicsPath();
            int d = radius * 2;
            path.AddArc(r.Left, r.Top, d, d, 180, 90);
            path.AddArc(r.Right - d, r.Top, d, d, 270, 90);
            path.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            path.AddArc(r.Left, r.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }
    }

    // ==========================================
    // 热启动拟态选项卡片：带 5 秒自动进入倒计时 (AntigravityHotLaunchChoiceForm)
    // ==========================================
    internal class AntigravityHotLaunchChoiceForm : Form
    {
        internal HotLaunchAction Action { get; private set; }
        internal bool AccountMismatch { get { return accountMismatch; } }
        internal bool NeedSwitch { get { return needSwitch; } }
        internal string SelectedEmail { get { return selectedEmail; } }
        internal string BestTargetEmail { get { return bestTargetEmail; } }
        private int remainingSeconds = 5;
        private float uiScale = 1F;
        private Rectangle Px(int x, int y, int width, int height) {
            return new Rectangle((int)Math.Round(x * uiScale), (int)Math.Round(y * uiScale), (int)Math.Round(width * uiScale), (int)Math.Round(height * uiScale));
        }

        private System.Windows.Forms.Timer countdownTimer;
        private System.Windows.Forms.Timer spinnerTimer;
        private int spinnerAngle = 0;
        private bool isLoadingIdentity = true;
        private bool countdownPaused = false;
        private bool countdownStarted = false;
        private HotLaunchButton btnActivate;
        private HotLaunchButton btnRepair;
        private CapsuleCloseButton closeButton;
        private Image appIcon = null;
        private string subtitleText = "网络与算力大盘监控 · 点击空白处可暂停 5 秒倒计时";
        private string networkText = "线路  正在同步当前节点…";
        private string accountText = "当前在用  正在读取软件内账号…";
        private string selectedText = "⏳ 状态评估  正在核验账号额度与运行状态…";
        private bool networkVerified;
        private bool accountMismatch;
        private bool needSwitch;
        private bool isExhausted;
        private bool isPro = true;
        private string verifiedEmail = "";
        private string selectedEmail = "";
        private string bestTargetEmail = "";
        private string bestTargetPlan = "";
        private string resolvedRegionLabel = "";
        private string resolvedNodeLabel = "";
        private ToolTip detailTip;

        private static string FormatRegionLabel(string regionOrText)
        {
            string val = (regionOrText ?? "").Trim();
            if (string.Equals(val, "JP", StringComparison.OrdinalIgnoreCase) || val.Contains("日本") || val.Contains("Tokyo") || val.Contains("Osaka") || val.Contains("🇯🇵")) return "日本";
            if (string.Equals(val, "US", StringComparison.OrdinalIgnoreCase) || val.Contains("美国") || val.Contains("San Jose") || val.Contains("Los Angeles") || val.Contains("Phoenix") || val.Contains("凤凰城") || val.Contains("🇺🇸")) return "美国";
            return val;
        }

        private static string MatchClashNodeByServerPort(string server, string port)
        {
            if (string.IsNullOrEmpty(server) || string.IsNullOrEmpty(port)) return "";
            try
            {
                string appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                string[] dirs = new[] {
                    Path.Combine(appData, @"io.github.clash-verge-rev.clash-verge-rev\profiles"),
                    Path.Combine(appData, @"mihomo-party\profiles")
                };
                string serverPat = "(?<![-\\w])server:\\s*['\"]?" + System.Text.RegularExpressions.Regex.Escape(server) + "['\"]?(?=[\\s,}])";
                string portPat = "(?<![-\\w])port:\\s*['\"]?" + System.Text.RegularExpressions.Regex.Escape(port) + "['\"]?(?=[\\s,}])";
                foreach (string dir in dirs)
                {
                    if (!Directory.Exists(dir)) continue;
                    string[] files = Directory.GetFiles(dir, "*.y*ml");
                    Array.Sort(files, delegate(string a, string b) { return File.GetLastWriteTimeUtc(b).CompareTo(File.GetLastWriteTimeUtc(a)); });
                    foreach (string file in files)
                    {
                        foreach (string line in File.ReadLines(file, Encoding.UTF8))
                        {
                            if (line.IndexOf(server, StringComparison.OrdinalIgnoreCase) < 0) continue;
                            if (!System.Text.RegularExpressions.Regex.IsMatch(line, serverPat) || !System.Text.RegularExpressions.Regex.IsMatch(line, portPat)) continue;
                            var m = System.Text.RegularExpressions.Regex.Match(line, "(?<![-\\w])name:\\s*(?:'([^']+)'|\"([^\"]+)\"|([^,}]+))");
                            if (m.Success)
                            {
                                string raw = !string.IsNullOrEmpty(m.Groups[1].Value) ? m.Groups[1].Value
                                    : !string.IsNullOrEmpty(m.Groups[2].Value) ? m.Groups[2].Value
                                    : m.Groups[3].Value;
                                string trimmed = (raw ?? "").Trim();
                                if (!string.IsNullOrEmpty(trimmed) && !trimmed.StartsWith("ANTIGRAVITY-", StringComparison.OrdinalIgnoreCase))
                                    return trimmed;
                            }
                        }
                    }
                }
            }
            catch { }
            return "";
        }

        private static void TryResolveActiveNodeFromConfig(out string nodeName, out string regionLabel)
        {
            nodeName = "";
            regionLabel = "";
            try
            {
                string mihomoYaml = Path.Combine(Program.RuntimeDirectory, "mihomo-antigravity.yaml");
                if (!File.Exists(mihomoYaml)) return;
                string content = File.ReadAllText(mihomoYaml, Encoding.UTF8);
                var mNode = System.Text.RegularExpressions.Regex.Match(content, @"(?m)^#\s*Antigravity-Target-Node:\s*(.+?)\s*$");
                if (mNode.Success) nodeName = mNode.Groups[1].Value.Trim();
                var mReg = System.Text.RegularExpressions.Regex.Match(content, @"(?m)^#\s*Antigravity-Target-Region:\s*(.+?)\s*$");
                if (mReg.Success) regionLabel = FormatRegionLabel(mReg.Groups[1].Value);

                if (string.IsNullOrEmpty(nodeName))
                {
                    var mServer = System.Text.RegularExpressions.Regex.Match(content, @"(?<![-\w])server:\s*['""]?([^,\s}'""]+)['""]?");
                    var mPort = System.Text.RegularExpressions.Regex.Match(content, @"(?<![-\w])port:\s*['""]?(\d+)['""]?");
                    if (mServer.Success && mPort.Success)
                    {
                        string srv = mServer.Groups[1].Value.Trim();
                        string prt = mPort.Groups[1].Value.Trim();
                        string matched = MatchClashNodeByServerPort(srv, prt);
                        if (!string.IsNullOrEmpty(matched)) nodeName = matched;
                        if (string.IsNullOrEmpty(regionLabel))
                        {
                            regionLabel = FormatRegionLabel(nodeName);
                            if (string.IsNullOrEmpty(regionLabel))
                            {
                                if (srv.StartsWith("us", StringComparison.OrdinalIgnoreCase)) regionLabel = "美国";
                                else if (srv.StartsWith("jp", StringComparison.OrdinalIgnoreCase)) regionLabel = "日本";
                            }
                        }
                    }
                }
                else if (string.IsNullOrEmpty(regionLabel))
                {
                    regionLabel = FormatRegionLabel(nodeName);
                }
            }
            catch { }
        }

        private static string FormatNetworkLine(string regionLabel, string nodeName, string liveTail)
        {
            if (string.IsNullOrEmpty(nodeName))
            {
                string regPart = string.IsNullOrEmpty(regionLabel) ? "" : (regionLabel + " · ");
                return string.IsNullOrEmpty(liveTail)
                    ? ("线路  " + regPart + "尚未同步专线节点（可点击“检查并切换线路”）")
                    : ("线路  " + regPart + "本地专线运行中" + liveTail);
            }
            string prefix = string.IsNullOrEmpty(regionLabel) ? "" : (regionLabel + " · ");
            return "线路  " + prefix + nodeName + (liveTail ?? "");
        }


        private static string JsonValue(string json, string key)
        {
            try
            {
                var data = new System.Web.Script.Serialization.JavaScriptSerializer().DeserializeObject(json) as Dictionary<string, object>;
                return data != null && data.ContainsKey(key) && data[key] != null ? Convert.ToString(data[key]) : "";
            }
            catch { return ""; }
        }

        internal AntigravityHotLaunchChoiceForm()
        {
            Action = HotLaunchAction.Cancel;
            Text = "Antigravity 启动助手";
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            AutoScaleMode = AutoScaleMode.None;
            DoubleBuffered = true;
            using (Graphics dpiGraphics = CreateGraphics()) { uiScale = Math.Max(1F, dpiGraphics.DpiX / 96F); }
            ClientSize = new Size(560, 256);
            BackColor = Color.FromArgb(248, 250, 252);
            ShowInTaskbar = true;
            TopMost = false;
            KeyPreview = true;

            appIcon = Program.LoadIconOrPng(Program.IconPath);

            try
            {
                string json = File.Exists(Program.SupervisorStatePath) ? File.ReadAllText(Program.SupervisorStatePath) : "{}";
                string country = JsonValue(json, "egress_country");
                string node = JsonValue(json, "target_node");
                bool passed = JsonValue(json, "real_model_probe") == "passed" && JsonValue(json, "status") == "ready";
                networkVerified = passed;
                if (node == "CURRENT-VERIFIED-FAILOVER-CANDIDATE") node = "";
                string regionLabel = FormatRegionLabel(country);
                if (string.IsNullOrEmpty(node) || string.IsNullOrEmpty(regionLabel))
                {
                    string cfgNode, cfgRegion;
                    TryResolveActiveNodeFromConfig(out cfgNode, out cfgRegion);
                    if (string.IsNullOrEmpty(node) && !string.IsNullOrEmpty(cfgNode)) node = cfgNode;
                    if (string.IsNullOrEmpty(regionLabel) && !string.IsNullOrEmpty(cfgRegion)) regionLabel = cfgRegion;
                }
                if (string.IsNullOrEmpty(regionLabel) && !string.IsNullOrEmpty(node)) regionLabel = FormatRegionLabel(node);
                resolvedRegionLabel = regionLabel;
                resolvedNodeLabel = node;
                networkText = FormatNetworkLine(resolvedRegionLabel, resolvedNodeLabel, "（正在检测连通性…）");
                subtitleText = "网络与算力大盘监控 · 点击空白处可暂停 5 秒倒计时";
                string receipt = Path.Combine(Program.RuntimeDirectory, "launch-account-status.json");
                if (File.Exists(receipt))
                {
                    string rJson = File.ReadAllText(receipt);
                    verifiedEmail = JsonValue(rJson, "email");
                    string h5Str = JsonValue(rJson, "gemini_5h");
                    string wStr = JsonValue(rJson, "gemini_weekly");
                    isPro = JsonValue(rJson, "is_pro") != "False";
                    isExhausted = JsonValue(rJson, "is_exhausted") == "True";
                    needSwitch = isExhausted || JsonValue(rJson, "need_switch") == "True";
                    bestTargetEmail = JsonValue(rJson, "best_target_email");
                    bestTargetPlan = JsonValue(rJson, "best_target_plan");
                    double h5 = 0; double.TryParse(h5Str, out h5);
                    double w = 0; double.TryParse(wStr, out w);
                    if (isExhausted || (h5 <= 5.0 && w <= 5.0))
                    {
                        isExhausted = true;
                        needSwitch = true;
                        subtitleText = "当前账号算力已耗尽 · 倒计时或点击将自动切号接力";
                    }
                    else if (h5 <= 15.0)
                    {
                        subtitleText = "当前账号配额较低 · 点击空白处可暂停 5 秒倒计时";
                    }
                    else
                    {
                        subtitleText = "网络与算力大盘监控 · 点击空白处可暂停 5 秒倒计时";
                    }
                }
                string selected = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".antigravity_cockpit", "current_account.json");
                if (File.Exists(selected))
                {
                    string email = JsonValue(File.ReadAllText(selected), "email");
                    selectedEmail = email;
                }
            }
            catch { }

            accountMismatch = !string.IsNullOrEmpty(verifiedEmail) && !string.IsNullOrEmpty(selectedEmail) && !string.Equals(verifiedEmail, selectedEmail, StringComparison.OrdinalIgnoreCase);
            if (accountMismatch) needSwitch = true;
            accountText = "当前在用  正在读取软件内账号…";
            selectedText = (needSwitch || accountMismatch)
                ? ("⚡ 状态评估  建议切号接力：" + (!string.IsNullOrEmpty(bestTargetEmail) ? bestTargetEmail : selectedEmail))
                : "⏳ 状态评估  正在核验账号额度与运行状态…";
            AccessibleDescription = accountText + "; " + selectedText + "; " + networkText + "; " + subtitleText;
            Shown += delegate {
                if (spinnerTimer != null) spinnerTimer.Start();
                ReadRuntimeIdentity();
            };
            detailTip = new ToolTip { AutoPopDelay = 15000, InitialDelay = 300, ReshowDelay = 100 };
            detailTip.SetToolTip(this, accountText + "\n" + selectedText + "\n" + networkText + "\n" + subtitleText + "\n账号来源 Cockpit；独立代理端口 17897。");
            FormClosed += delegate { StopTimer(); detailTip.Dispose(); };

            closeButton = new CapsuleCloseButton
            {
                Location = new Point(ClientSize.Width - 34, 11),
                Size = new Size(22, 22)
            };
            closeButton.Click += delegate
            {
                StopTimer();
                Action = HotLaunchAction.Cancel;
                Close();
            };

            var minimizeButton = new CapsuleMinimizeButton
            {
                Location = new Point(ClientSize.Width - 64, 11),
                Size = new Size(22, 22)
            };
            minimizeButton.Click += delegate
            {
                WindowState = FormWindowState.Minimized;
            };

            var settingsButton = new CapsuleSettingsButton
            {
                Location = new Point(ClientSize.Width - 94, 11),
                Size = new Size(22, 22)
            };
            settingsButton.Click += delegate
            {
                StopTimer();
                btnActivate.ButtonText = accountMismatch ? "同步切号并进入" : "进入反重力";
                using (var sf = new LauncherSettingsForm())
                {
                    sf.ShowDialog(this);
                }
            };

            btnActivate = new HotLaunchButton((needSwitch || accountMismatch) ? "优选切号并进入 (5s)" : "进入反重力 (5s)")
            {
                IsPrimary = true,
                IsWarning = (needSwitch || accountMismatch),
                Location = new Point(20, 194),
                Size = new Size(252, 46)
            };
            btnActivate.Click += delegate
            {
                StopTimer();
                Action = HotLaunchAction.Activate;
                Close();
            };

            btnRepair = new HotLaunchButton("检查并切换线路")
            {
                Location = new Point(288, 194),
                Size = new Size(252, 46)
            };
            btnRepair.Click += delegate
            {
                StopTimer();
                Action = HotLaunchAction.Repair;
                Close();
            };

            Controls.Add(closeButton);
            Controls.Add(minimizeButton);
            Controls.Add(settingsButton);
            Controls.Add(btnActivate);
            Controls.Add(btnRepair);

            MouseDown += delegate(object s, MouseEventArgs me)
            {
                StopTimer();
                btnActivate.ButtonText = (needSwitch || accountMismatch) ? "优选切号并进入" : "进入反重力";
                if (me.Button == MouseButtons.Left)
                {
                    Program.ReleaseCapture();
                    Program.SendMessage(Handle, 0xA1, 0x2, 0);
                }
            };

            Shown += delegate
            {
                try
                {
                    // 启动瞬间短暂置顶提醒（0.8秒），让用户立刻感知到启动器已就绪
                    Program.SetWindowPos(Handle, Program.HWND_TOPMOST, 0, 0, 0, 0, Program.SWP_NOMOVE | Program.SWP_NOSIZE | Program.SWP_SHOWWINDOW);
                    var unpinTimer = new System.Windows.Forms.Timer { Interval = 800 };
                    unpinTimer.Tick += delegate
                    {
                        unpinTimer.Stop();
                        unpinTimer.Dispose();
                        try { Program.SetWindowPos(Handle, Program.HWND_NOTOPMOST, 0, 0, 0, 0, Program.SWP_NOMOVE | Program.SWP_NOSIZE | Program.SWP_NOACTIVATE); } catch { }
                    };
                    unpinTimer.Start();
                }
                catch { }
            };

            Deactivate += delegate
            {
                // 一旦失焦或点击其他应用，立即彻底解除置顶，允许任何其他窗口自由覆盖
                try { Program.SetWindowPos(Handle, Program.HWND_NOTOPMOST, 0, 0, 0, 0, Program.SWP_NOMOVE | Program.SWP_NOSIZE | Program.SWP_NOACTIVATE); } catch { }
            };

            spinnerTimer = new System.Windows.Forms.Timer { Interval = 75 };
            spinnerTimer.Tick += delegate
            {
                if (!isLoadingIdentity)
                {
                    if (spinnerTimer != null) spinnerTimer.Stop();
                    return;
                }
                spinnerAngle = (spinnerAngle + 28) % 360;
                Invalidate(Px(16, 90, 32, 32));
            };

            countdownTimer = new System.Windows.Forms.Timer { Interval = 1000 };
            countdownTimer.Tick += delegate
            {
                if (countdownPaused) return;
                remainingSeconds--;
                if (remainingSeconds <= 0)
                {
                    StopTimer();
                    Action = HotLaunchAction.Activate;
                    Close();
                }
                else
                {
                    btnActivate.ButtonText = ((needSwitch || accountMismatch) ? "优选切号并进入 (" : "进入反重力 (") + remainingSeconds + "s)";
                }
            };
            if (uiScale != 1F) Scale(new SizeF(uiScale, uiScale));
        }

        private static int ProbeLiveProxyFast()
        {
            try
            {
                var sw = System.Diagnostics.Stopwatch.StartNew();
                var req = (System.Net.HttpWebRequest)System.Net.WebRequest.Create("http://www.gstatic.com/generate_204");
                req.Method = "GET";
                req.Proxy = new System.Net.WebProxy("http://127.0.0.1:17897");
                req.Timeout = 1300;
                req.ReadWriteTimeout = 1300;
                req.KeepAlive = false;
                using (var resp = (System.Net.HttpWebResponse)req.GetResponse())
                {
                    sw.Stop();
                    if ((int)resp.StatusCode == 204 || (int)resp.StatusCode == 200)
                        return Math.Max(1, (int)sw.ElapsedMilliseconds);
                }
            }
            catch { }
            return -1;
        }

        private void ReadRuntimeIdentity() {
            Task.Run(delegate {
                string liveEmail = "";
                string liveJson = "";
                var proxyTask = Task.Run(delegate { return ProbeLiveProxyFast(); });
                try {
                    string helper = Path.Combine(Program.AppDirectory, "antigravity_runtime_identity.py");
                    string pythonw = Program.ResolvePythonw();
                    string python = Path.Combine(Path.GetDirectoryName(pythonw) ?? "", "python.exe");
                    var info = new ProcessStartInfo(python, "\"" + helper + "\"") { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
                    using (var process = Process.Start(info)) {
                        var output = process.StandardOutput.ReadToEndAsync();
                        var error = process.StandardError.ReadToEndAsync();
                        if (!process.WaitForExit(3500)) { try { process.Kill(); } catch { } }
                        else if (process.ExitCode == 0 && output.Wait(300)) {
                            liveJson = output.Result;
                            if (JsonValue(liveJson, "status") == "live") liveEmail = JsonValue(liveJson, "email");
                        }
                    }
                } catch { }
                int liveRttMs = -1;
                try { if (proxyTask.Wait(1500)) liveRttMs = proxyTask.Result; } catch { }

                if (IsDisposed || Disposing || !IsHandleCreated) return;
                try { BeginInvoke(new Action(delegate {
                    if (IsDisposed) return;
                    isLoadingIdentity = false;
                    if (spinnerTimer != null) spinnerTimer.Stop();
                    if (liveRttMs > 0) networkVerified = true;
                    string liveTail = liveRttMs > 0
                        ? ("（在线 · " + liveRttMs + "ms）")
                        : "（待恢复 · 可点右侧重连）";
                    networkText = FormatNetworkLine(resolvedRegionLabel, resolvedNodeLabel, liveTail);

                    if (!string.IsNullOrEmpty(liveJson)) {
                        string liveEm = JsonValue(liveJson, "email");
                        if (!string.IsNullOrEmpty(liveEm)) liveEmail = liveEm;
                        string h5Str = JsonValue(liveJson, "gemini_5h");
                        string wStr = JsonValue(liveJson, "gemini_weekly");
                        double h5 = 0; double.TryParse(h5Str, out h5);
                        double w = 0; double.TryParse(wStr, out w);
                        isPro = JsonValue(liveJson, "is_pro") != "False";
                        isExhausted = JsonValue(liveJson, "is_exhausted") == "True";
                        if (JsonValue(liveJson, "need_switch") == "True") needSwitch = true;
                        string bTarget = JsonValue(liveJson, "best_target_email");
                        if (!string.IsNullOrEmpty(bTarget)) bestTargetEmail = bTarget;

                        string planTag = isPro ? "Pro" : "Free";
                        if (isExhausted || (h5 <= 5.0 && w <= 5.0)) {
                            isExhausted = true;
                            needSwitch = true;
                            subtitleText = "当前账号算力已耗尽 · 倒计时或点击将自动切号接力";
                        } else if (h5 <= 15.0) {
                            subtitleText = "当前账号配额较低 · 点击空白处可暂停 5 秒倒计时";
                        } else {
                            subtitleText = "网络与算力大盘监控 · 点击空白处可暂停 5 秒倒计时";
                        }

                        accountText = "当前在用  " + liveEmail + " (" + planTag + " · 5 小时 " + Math.Round(h5) + "% | 周 " + Math.Round(w) + "%)";
                        accountMismatch = !string.IsNullOrEmpty(selectedEmail) && !string.Equals(liveEmail, selectedEmail, StringComparison.OrdinalIgnoreCase);
                        if (accountMismatch) needSwitch = true;

                        string targetShow = !string.IsNullOrEmpty(bestTargetEmail) ? bestTargetEmail : selectedEmail;
                        if (needSwitch || accountMismatch) {
                            selectedText = "✅ 状态评估  建议切号接力至 " + targetShow;
                            btnActivate.IsWarning = true;
                        } else {
                            selectedText = "✅ 状态评估  当前在用账号配额充足健康，保持在用";
                            btnActivate.IsWarning = false;
                        }
                    } else if (!string.IsNullOrEmpty(liveEmail)) {
                        accountText = "当前在用  " + liveEmail;
                        selectedText = "✅ 状态评估  已连接当前正在运行的编辑器账号";
                    } else {
                        selectedText = "✅ 状态评估  当前编辑窗口运行中，可直接进入";
                    }

                    if (!countdownPaused && countdownTimer != null) {
                        if (!countdownStarted) {
                            remainingSeconds = 5;
                            countdownStarted = true;
                            countdownTimer.Start();
                        }
                        btnActivate.ButtonText = ((needSwitch || accountMismatch) ? "优选切号并进入 (" : "进入反重力 (") + remainingSeconds + "s)";
                    } else {
                        btnActivate.ButtonText = (needSwitch || accountMismatch) ? "优选切号并进入" : "进入反重力";
                    }
                    AccessibleDescription = accountText + "; " + selectedText + "; " + networkText;
                    detailTip.SetToolTip(this, accountText + "\n" + selectedText + "\n" + networkText + "\n" + subtitleText);
                    Invalidate();
                })); } catch { }
            });
        }

        internal void PauseCountdown() {
            StopTimer();
            btnActivate.ButtonText = (needSwitch || accountMismatch) ? "优选切号并进入" : "进入反重力";
        }

        private void StopTimer()
        {
            countdownPaused = true;
            if (countdownTimer != null)
            {
                countdownTimer.Stop();
                countdownTimer.Dispose();
                countdownTimer = null;
            }
            if (spinnerTimer != null)
            {
                spinnerTimer.Stop();
                spinnerTimer.Dispose();
                spinnerTimer = null;
            }
        }

        protected override void OnKeyDown(KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Enter || e.KeyCode == Keys.Space)
            {
                StopTimer();
                Action = HotLaunchAction.Activate;
                Close();
            }
            else if (e.KeyCode == Keys.Escape)
            {
                StopTimer();
                Action = HotLaunchAction.Cancel;
                Close();
            }
            base.OnKeyDown(e);
        }

        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams cp = base.CreateParams;
                cp.ClassStyle |= 0x00020000; // CS_DROPSHADOW
                return cp;
            }
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            try
            {
                int val = Program.DWMWCP_ROUND;
                Program.DwmSetWindowAttribute(Handle, Program.DWMWA_WINDOW_CORNER_PREFERENCE, ref val, sizeof(int));
            }
            catch { }
        }

        protected override void WndProc(ref Message m)
        {
            const int WM_PRINTCLIENT = 0x0318;
            const int WM_PRINT = 0x0317;
            if (m.Msg == WM_PRINTCLIENT || m.Msg == WM_PRINT)
            {
                using (Graphics g = Graphics.FromHdc(m.WParam))
                {
                    OnPaint(new PaintEventArgs(g, ClientRectangle));
                }
                return;
            }
            base.WndProc(ref m);
        }

        private static GraphicsPath RoundedRectangle(Rectangle r, int radius)
        {
            var path = new GraphicsPath();
            int d = radius * 2;
            path.AddArc(r.Left, r.Top, d, d, 180, 90);
            path.AddArc(r.Right - d, r.Top, d, d, 270, 90);
            path.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            path.AddArc(r.Left, r.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }

        private static void DrawCardText(Graphics g, string text, Font font, Rectangle bounds, Color color, bool centered) {
            g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;
            using (var brush = new SolidBrush(color))
            using (var format = new StringFormat { Trimming = StringTrimming.EllipsisCharacter, FormatFlags = StringFormatFlags.NoWrap, LineAlignment = StringAlignment.Center, Alignment = centered ? StringAlignment.Center : StringAlignment.Near })
                g.DrawString(text, font, brush, bounds, format);
        }

        private void DrawSpinnerCircle(Graphics g, Rectangle rect, int angle)
        {
            using (var trackPen = new Pen(Color.FromArgb(219, 234, 254), Math.Max(1.6F, 2F * uiScale)))
            using (var arcPen = new Pen(Color.FromArgb(37, 99, 235), Math.Max(1.6F, 2F * uiScale)))
            {
                arcPen.StartCap = LineCap.Round;
                arcPen.EndCap = LineCap.Round;
                g.DrawEllipse(trackPen, rect);
                g.DrawArc(arcPen, rect, angle, 250);
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var bounds = new Rectangle(0, 0, Width - 1, Height - 1);
            using (var path = RoundedRectangle(bounds, (int)(16 * uiScale)))
            using (var fill = new SolidBrush(Color.FromArgb(250, 252, 255)))
            using (var border = new Pen(Color.FromArgb(211, 221, 234))) {
                e.Graphics.FillPath(fill, path); e.Graphics.DrawPath(border, path);
            }
            if (appIcon != null) {
                e.Graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                e.Graphics.DrawImage(appIcon, Px(20, 18, 34, 34));
            }
            using (var title = new Font("微软雅黑", 12F, FontStyle.Bold, GraphicsUnit.Point, 134))
                DrawCardText(e.Graphics, "Antigravity", title, Px(64, 18, 160, 34), Color.FromArgb(20, 34, 54), false);

            using (var sepPen = new Pen(Color.FromArgb(232, 238, 246)))
                e.Graphics.DrawLine(sepPen, Px(20, 60, 0, 0).X, Px(0, 60, 0, 0).Y, Width - Px(20, 0, 0, 0).X, Px(0, 60, 0, 0).Y);

            using (var body = new Font("微软雅黑", 10F, FontStyle.Regular, GraphicsUnit.Point, 134))
            using (var small = new Font("微软雅黑", 9F, FontStyle.Regular, GraphicsUnit.Point, 134)) {
                DrawCardText(e.Graphics, subtitleText, small, Px(20, 64, 520, 22), Color.FromArgb(85, 101, 123), false);
                if (isLoadingIdentity) {
                    DrawSpinnerCircle(e.Graphics, Px(20, 99, 14, 14), spinnerAngle);
                    DrawCardText(e.Graphics, accountText, body, Px(41, 94, 499, 24), Color.FromArgb(23, 38, 59), false);
                } else {
                    DrawCardText(e.Graphics, accountText, body, Px(20, 94, 520, 24), Color.FromArgb(23, 38, 59), false);
                }
                DrawCardText(e.Graphics, selectedText, small, Px(20, 124, 520, 22), (needSwitch || accountMismatch) ? Color.FromArgb(194, 65, 12) : Color.FromArgb(22, 101, 52), false);
                DrawCardText(e.Graphics, networkText, body, Px(20, 154, 520, 24), Color.FromArgb(23, 38, 59), false);
            }
        }
    }

    // ==========================================
    // 拟态状态卡片：包含清晰通路与链路核验反馈 (无缝渲染)
    // ==========================================
    internal class AntigravityLaunchCapsuleForm : Form
    {
        internal int ExitCode { get; private set; }
        private string recoveryReason;
        private bool userCancelled = false;
        private Process supervisorProc = null;

        private CapsuleProgress progressBar;
        private Image appIcon = null;
        private System.Windows.Forms.Timer spinnerTimer = null;
        private int spinnerAngle = 0;

        // 动态状态模型
        // Account-first launch state. A stage turns green only after a real logged gate passes.
        private string accountStatusText = "正在读取 Cockpit 当前账号与缓存额度…";
        private bool accountPassed = false;
        private string lineStatusText = "等待账号就绪…";
        private bool linePassed = false;
        private string googleStatusText = "等待专线就绪…";
        private bool googlePassed = false;
        private string modelStatusText = "等待 Google 链路验证…";
        private bool modelPassed = false;
        private string workspaceStatusText = "等待启动检查完成…";
        private bool workspacePassed = false;
        private int activeStep = 0;
        private string footerStatusText = "正在确认账号与工作环境…";

        public AntigravityLaunchCapsuleForm(string reason)
        {
            recoveryReason = reason;
            ExitCode = 0;
            InitializeComponent();
        }

        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams cp = base.CreateParams;
                cp.ClassStyle |= 0x00020000; // CS_DROPSHADOW
                return cp;
            }
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            try
            {
                int val = Program.DWMWCP_ROUND;
                Program.DwmSetWindowAttribute(this.Handle, Program.DWMWA_WINDOW_CORNER_PREFERENCE, ref val, sizeof(int));
            }
            catch { }
        }

        protected override void WndProc(ref Message m)
        {
            const int WM_PRINTCLIENT = 0x0318;
            const int WM_PRINT = 0x0317;
            if (m.Msg == WM_PRINTCLIENT || m.Msg == WM_PRINT)
            {
                using (Graphics g = Graphics.FromHdc(m.WParam))
                {
                    OnPaint(new PaintEventArgs(g, ClientRectangle));
                }
                return;
            }
            base.WndProc(ref m);
        }

        private static GraphicsPath RoundedRectangle(Rectangle r, int radius)
        {
            var path = new GraphicsPath();
            int d = radius * 2;
            path.AddArc(r.Left, r.Top, d, d, 180, 90);
            path.AddArc(r.Right - d, r.Top, d, d, 270, 90);
            path.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            path.AddArc(r.Left, r.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }

        private static void DrawPillBadge(Graphics g, string text, int x, int y, Color bg, Color border, Color fg)
        {
            using (var font = new Font("Microsoft YaHei UI", 8F, FontStyle.Bold))
            {
                var size = TextRenderer.MeasureText(text, font);
                var rect = new Rectangle(x, y, size.Width + 12, 19);
                using (var path = RoundedRectangle(rect, 9))
                using (var brush = new SolidBrush(bg))
                using (var pen = new Pen(border, 1F))
                {
                    g.FillPath(brush, path);
                    g.DrawPath(pen, path);
                }
                TextRenderer.DrawText(g, text, font, rect, fg, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;
            var bounds = new Rectangle(0, 0, Width - 1, Height - 1);

            // A calm native card: five truthful stages, no synthetic percent or promotional badges.
            using (var path = RoundedRectangle(bounds, 18))
            using (var fill = new LinearGradientBrush(bounds, Color.FromArgb(253, 254, 255), Color.FromArgb(245, 248, 253), 90F))
            using (var border = new Pen(Color.FromArgb(215, 227, 240), 1F))
            {
                e.Graphics.FillPath(fill, path);
                e.Graphics.DrawPath(border, path);
            }

            if (appIcon != null)
            {
                e.Graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                e.Graphics.DrawImage(appIcon, new Rectangle(24, 17, 38, 38));
            }
            using (var titleFont = new Font("Microsoft YaHei UI", 12.5F, FontStyle.Bold))
            using (var subtitleFont = new Font("Microsoft YaHei UI", 8.5F))
            {
                TextRenderer.DrawText(e.Graphics, "Antigravity", titleFont, new Point(72, 17), Color.FromArgb(23, 37, 61));
                TextRenderer.DrawText(e.Graphics, "正在准备工作环境 · 实时检测", subtitleFont, new Point(73, 45), Color.FromArgb(112, 125, 143));
            }
            using (var separator = new Pen(Color.FromArgb(232, 238, 246)))
            {
                e.Graphics.DrawLine(separator, 24, 76, Width - 24, 76);
                e.Graphics.DrawLine(separator, 24, 381, Width - 24, 381);
            }

            DrawStepRow(e.Graphics, 1, 88, "当前账号", accountStatusText, accountPassed, activeStep == 0);
            DrawStepRow(e.Graphics, 2, 146, "本地专线", lineStatusText, linePassed, activeStep == 1);
            DrawStepRow(e.Graphics, 3, 204, "Google 通路", googleStatusText, googlePassed, activeStep == 2);
            DrawStepRow(e.Graphics, 4, 262, "AI 模型验证", modelStatusText, modelPassed, activeStep == 3);
            DrawStepRow(e.Graphics, 5, 320, "启动工作区", workspaceStatusText, workspacePassed, activeStep == 4);

            using (var footerFont = new Font("Microsoft YaHei UI", 8.5F))
            {
                TextRenderer.DrawText(e.Graphics, footerStatusText, footerFont,
                    new Rectangle(27, 391, Width - 54, 23), Color.FromArgb(104, 119, 139),
                    TextFormatFlags.SingleLine | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPrefix);
            }
        }

        private void DrawStepRow(Graphics g, int number, int y, string label, string detail, bool passed, bool active)
        {
            var rowRect = new Rectangle(20, y, Width - 40, 54);
            if (active && !passed)
            {
                using (var path = RoundedRectangle(rowRect, 11))
                using (var brush = new SolidBrush(Color.FromArgb(234, 243, 255)))
                using (var rowBorder = new Pen(Color.FromArgb(191, 219, 254), 1F))
                {
                    g.FillPath(brush, path);
                    g.DrawPath(rowBorder, path);
                }
                using (var accentRect = new SolidBrush(Color.FromArgb(37, 99, 235)))
                using (var accentPath = RoundedRectangle(new Rectangle(21, y + 11, 3, 32), 2))
                {
                    g.FillPath(accentRect, accentPath);
                }
            }

            Color dotFill = passed ? Color.FromArgb(220, 247, 231) :
                active ? Color.FromArgb(216, 231, 255) : Color.FromArgb(241, 245, 249);
            Color dotRing = passed ? Color.FromArgb(134, 239, 172) :
                active ? Color.FromArgb(147, 197, 253) : Color.FromArgb(226, 232, 240);
            Color dotText = passed ? Color.FromArgb(21, 128, 61) :
                active ? Color.FromArgb(39, 103, 220) : Color.FromArgb(157, 169, 183);
            var circle = new Rectangle(33, y + 13, 26, 26);
            using (var brush = new SolidBrush(dotFill)) g.FillEllipse(brush, circle);
            using (var ring = new Pen(dotRing, 1F)) g.DrawEllipse(ring, circle);
            if (active && !passed)
            {
                var spinRect = Rectangle.Inflate(circle, 2, 2);
                using (var spinPen = new Pen(Color.FromArgb(37, 99, 235), 2F))
                {
                    spinPen.StartCap = LineCap.Round;
                    spinPen.EndCap = LineCap.Round;
                    g.DrawArc(spinPen, spinRect, spinnerAngle, 240);
                }
            }
            using (var iconFont = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold))
            {
                TextRenderer.DrawText(g, passed ? "✓" : number.ToString(), iconFont, circle,
                    dotText, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPrefix);
            }

            using (var labelFont = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold))
            using (var detailFont = new Font("Microsoft YaHei UI", 8.5F))
            {
                TextRenderer.DrawText(g, label, labelFont, new Rectangle(74, y + 5, Width - 112, 23),
                    Color.FromArgb(36, 53, 77), TextFormatFlags.SingleLine | TextFormatFlags.NoPrefix);
                TextRenderer.DrawText(g, detail ?? "", detailFont, new Rectangle(74, y + 28, Width - 115, 22),
                    passed ? Color.FromArgb(29, 120, 81) : active ? Color.FromArgb(57, 101, 164) : Color.FromArgb(121, 135, 153),
                    TextFormatFlags.SingleLine | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPrefix);
            }
        }

        private void InitializeComponent()
        {
            Text = "Antigravity";
            ClientSize = new Size(580, 428);
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            ShowInTaskbar = true;
            TopMost = false;
            BackColor = Color.FromArgb(236, 244, 252);
            DoubleBuffered = true;

            // Do not show yesterday's email as if the current account were already verified.

            appIcon = Program.LoadIconOrPng(Program.IconPath);
            if (File.Exists(Program.IconPath))
            {
                try { Icon = new Icon(Program.IconPath); } catch { }
            }

            MouseDown += OnWindowDrag;

            var btnClose = new CapsuleCloseButton
            {
                Location = new Point(Width - 34, 11),
                Size = new Size(22, 22)
            };
            btnClose.Click += delegate
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
                Close();
            };

            var btnMinimize = new CapsuleMinimizeButton
            {
                Location = new Point(Width - 64, 11),
                Size = new Size(22, 22)
            };
            btnMinimize.Click += delegate
            {
                WindowState = FormWindowState.Minimized;
            };

            // Keep the legacy animation object for compatibility with existing observers,
            // but never display percentages unrelated to actual completion.
            progressBar = new CapsuleProgress
            {
                Location = new Point(22, 417),
                Size = new Size(536, 4),
                ProgressValue = 3,
                Visible = false
            };

            Controls.AddRange(new Control[] { btnClose, btnMinimize, progressBar });

            spinnerTimer = new System.Windows.Forms.Timer { Interval = 75 };
            spinnerTimer.Tick += delegate
            {
                spinnerAngle = (spinnerAngle + 28) % 360;
                Invalidate(new Rectangle(26, 86, 40, 300));
            };
            FormClosed += delegate
            {
                if (spinnerTimer != null)
                {
                    spinnerTimer.Stop();
                    spinnerTimer.Dispose();
                    spinnerTimer = null;
                }
            };

            Shown += delegate
            {
                if (spinnerTimer != null) spinnerTimer.Start();
                try
                {
                    // 启动瞬间短暂置顶提醒（0.8秒），向用户明确反馈启动器已拉起运行
                    Program.SetWindowPos(Handle, Program.HWND_TOPMOST, 0, 0, 0, 0, Program.SWP_NOMOVE | Program.SWP_NOSIZE | Program.SWP_SHOWWINDOW);
                    BringToFront();
                    Activate();
                    var unpinTimer = new System.Windows.Forms.Timer { Interval = 800 };
                    unpinTimer.Tick += delegate
                    {
                        unpinTimer.Stop();
                        unpinTimer.Dispose();
                        try { Program.SetWindowPos(Handle, Program.HWND_NOTOPMOST, 0, 0, 0, 0, Program.SWP_NOMOVE | Program.SWP_NOSIZE | Program.SWP_NOACTIVATE); } catch { }
                    };
                    unpinTimer.Start();
                }
                catch { }
                Task.Run(delegate { RunLaunchTask(); });
            };

            Deactivate += delegate
            {
                // 一旦失焦或点击其他应用，立即彻底解除置顶，允许任何其他窗口自由覆盖
                try { Program.SetWindowPos(Handle, Program.HWND_NOTOPMOST, 0, 0, 0, 0, Program.SWP_NOMOVE | Program.SWP_NOSIZE | Program.SWP_NOACTIVATE); } catch { }
            };
        }

        private void OnWindowDrag(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                Program.ReleaseCapture();
                Program.SendMessage(Handle, 0xA1, 0x2, 0);
            }
        }

        private void OnLaunchSuccess()
        {
            BeginInvoke(new Action(delegate
            {
                if (spinnerTimer != null) spinnerTimer.Stop();
                // Preserve the measured RTT, HTTP statuses and model response time.
                if (!linePassed) { lineStatusText = "专线已就绪"; linePassed = true; }
                if (!googlePassed) { googleStatusText = "Google 服务已响应"; googlePassed = true; }
                if (!modelPassed) { modelStatusText = "真实模型验证通过"; modelPassed = true; }
                if (!accountPassed) { accountStatusText = "当前账号门禁已通过"; accountPassed = true; }
                workspaceStatusText = "编辑器与语言服务已就绪";
                workspacePassed = true;
                activeStep = 5;
                footerStatusText = "工作环境已就绪，正在进入 Antigravity…";
                progressBar.ProgressValue = 100;
                Invalidate();
            }));
            Thread.Sleep(380);
            Invoke(new Action(delegate
            {
                ExitCode = 0;
                Close();
            }));
        }

        private bool WaitForExistingSupervisor(long logStartOffset, ref int displayedProgress)
        {
            DateTime waitStart = DateTime.Now;
            DateTime waitStartUtc = DateTime.UtcNow;
            int animationTick = 0;

            BeginInvoke(new Action(delegate
            {
                lineStatusText = "专线自愈中 · 已接管检测进度…";
                footerStatusText = "⚡ 检测到专线自愈正在进行，正在无缝接管…";
                Invalidate();
            }));

            while ((DateTime.Now - waitStart).TotalSeconds < 120)
            {
                if (userCancelled) { ExitCode = 0; return true; }

                string logChunk = ReadLogSince(logStartOffset);
                CapsuleState state = ParseLogState(logChunk);

                animationTick++;
                if (displayedProgress < state.TargetProgress)
                {
                    displayedProgress += Math.Max(1, (state.TargetProgress - displayedProgress + 2) / 3);
                }
                else if (displayedProgress < Math.Max(state.Ceiling, 92) && animationTick % 2 == 0)
                {
                    displayedProgress++;
                }

                int prog = displayedProgress;
                BeginInvoke(new Action(delegate
                {
                    if (!string.IsNullOrEmpty(state.LineText))
                    {
                        lineStatusText = state.LineText;
                        linePassed = state.LinePassed;
                    }
                    if (!string.IsNullOrEmpty(state.GoogleText))
                    {
                        googleStatusText = state.GoogleText;
                        googlePassed = state.GooglePassed;
                    }
                    if (!string.IsNullOrEmpty(state.ModelText))
                    {
                        modelStatusText = state.ModelText;
                        modelPassed = state.ModelPassed;
                    }
                    if (!string.IsNullOrEmpty(state.AccountText))
                    {
                        accountStatusText = state.AccountText;
                        accountPassed = state.AccountPassed;
                    }
                    if (!string.IsNullOrEmpty(state.WorkspaceText))
                    {
                        workspaceStatusText = state.WorkspaceText;
                        workspacePassed = state.WorkspacePassed;
                    }
                    activeStep = state.ActiveStep;
                    if (!string.IsNullOrEmpty(state.FooterText)) footerStatusText = state.FooterText;
                    progressBar.ProgressValue = prog;
                    Invalidate();
                }));

                // 检查是否有新鲜就绪标记
                if (logChunk.Contains("antigravity_live_seamless_attached") || logChunk.Contains("antigravity_ready"))
                {
                    OnLaunchSuccess();
                    return true;
                }

                if (File.Exists(Program.SupervisorStatePath))
                {
                    try
                    {
                        var fi = new FileInfo(Program.SupervisorStatePath);
                        if (fi.LastWriteTimeUtc >= waitStartUtc.AddSeconds(-2))
                        {
                            string json = File.ReadAllText(Program.SupervisorStatePath);
                            if (json.Contains("\"status\":  \"ready\"") || json.Contains("\"status\":\"ready\""))
                            {
                                OnLaunchSuccess();
                                return true;
                            }
                        }
                    }
                    catch { }
                }

                // 检查前序 Supervisor 互斥锁是否已释放
                if (!Program.IsSupervisorRunning())
                {
                    Thread.Sleep(500);
                    string finalChunk = ReadLogSince(logStartOffset);
                    if (finalChunk.Contains("antigravity_live_seamless_attached") || finalChunk.Contains("antigravity_ready"))
                    {
                        OnLaunchSuccess();
                        return true;
                    }
                    if (File.Exists(Program.SupervisorStatePath))
                    {
                        try
                        {
                            var fi = new FileInfo(Program.SupervisorStatePath);
                            if (fi.LastWriteTimeUtc >= waitStartUtc.AddSeconds(-2))
                            {
                                string json = File.ReadAllText(Program.SupervisorStatePath);
                                if (json.Contains("\"status\":  \"ready\"") || json.Contains("\"status\":\"ready\""))
                                {
                                    OnLaunchSuccess();
                                    return true;
                                }
                            }
                        }
                        catch { }
                    }
                    return false;
                }

                Thread.Sleep(200);
            }

            return false;
        }

        private void RunLaunchTask()
        {
            if (!File.Exists(Program.ScriptPath))
            {
                Invoke(new Action(delegate
                {
                    ExitCode = 2;
                    Close();
                    MessageBox.Show("缺少 Antigravity 启动核心脚本：\n" + Program.ScriptPath, "启动提示", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }));
                return;
            }

            long logStartOffset = GetLogLength();
            int displayedProgress = 3;
            int animationTick = 0;

            // 1. 若检测到后台或已有 Supervisor 正在运行，直接进入平滑接管监控模式
            if (Program.IsSupervisorRunning())
            {
                Program.TraceLog("Supervisor mutex is currently held. Entering takeover monitor.");
                if (WaitForExistingSupervisor(logStartOffset, ref displayedProgress))
                {
                    if (recoveryReason != "UserRequestedRepair")
                    {
                        return;
                    }
                    Program.TraceLog("Background supervisor completed, but user requested repair. Proceeding with full restart.");
                }
                logStartOffset = GetLogLength();
            }

            var psi = new ProcessStartInfo
            {
                FileName = @"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + Program.ScriptPath + "\" -RecoveryReason " + recoveryReason + " -PrelaunchClient",
                WorkingDirectory = Program.AppDirectory,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };

            using (var process = Process.Start(psi))
            {
                supervisorProc = process;
                if (process == null)
                {
                    Invoke(new Action(delegate { ExitCode = 3; Close(); }));
                    return;
                }

                var output = new StringBuilder();
                var error = new StringBuilder();
                process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) output.AppendLine(e.Data); };
                process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) error.AppendLine(e.Data); };
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                string lastRenderedChunk = "";
                while (!process.HasExited)
                {
                    if (userCancelled) { ExitCode = 0; return; }
                    string logChunk = ReadLogSince(logStartOffset);
                    bool logChanged = (logChunk.Length != lastRenderedChunk.Length);
                    if (logChanged)
                    {
                        lastRenderedChunk = logChunk;
                        CapsuleState state = ParseLogState(logChunk);

                        animationTick++;
                        if (displayedProgress < state.TargetProgress)
                        {
                            displayedProgress += Math.Max(1, (state.TargetProgress - displayedProgress + 2) / 3);
                        }
                        else if (displayedProgress < state.Ceiling && animationTick % 2 == 0)
                        {
                            displayedProgress++;
                        }

                        int prog = displayedProgress;
                        BeginInvoke(new Action(delegate
                        {
                            if (!string.IsNullOrEmpty(state.LineText))
                            {
                                lineStatusText = state.LineText;
                                linePassed = state.LinePassed;
                            }
                            if (!string.IsNullOrEmpty(state.GoogleText))
                            {
                                googleStatusText = state.GoogleText;
                                googlePassed = state.GooglePassed;
                            }
                            if (!string.IsNullOrEmpty(state.ModelText))
                            {
                                modelStatusText = state.ModelText;
                                modelPassed = state.ModelPassed;
                            }
                            if (!string.IsNullOrEmpty(state.AccountText))
                            {
                                accountStatusText = state.AccountText;
                                accountPassed = state.AccountPassed;
                            }
                            if (!string.IsNullOrEmpty(state.WorkspaceText))
                            {
                                workspaceStatusText = state.WorkspaceText;
                                workspacePassed = state.WorkspacePassed;
                            }
                            activeStep = state.ActiveStep;
                            if (!string.IsNullOrEmpty(state.FooterText)) footerStatusText = state.FooterText;
                            progressBar.ProgressValue = prog;
                            Invalidate();
                        }));
                    }

                    Thread.Sleep(100);
                }

                if (userCancelled) { ExitCode = 0; return; }
                process.WaitForExit();
                int result = process.ExitCode;
                string finalLog = ReadLogSince(logStartOffset);

                if (result == 0)
                {
                    OnLaunchSuccess();
                    return;
                }
                else if (result == 4)
                {
                    Program.TraceLog("Supervisor reported exit=4 (busy). Entering takeover monitor.");
                    if (WaitForExistingSupervisor(logStartOffset, ref displayedProgress))
                    {
                        return;
                    }
                    if (!Program.IsSupervisorRunning())
                    {
                        Program.TraceLog("Retrying supervisor start after exit=4 wait...");
                        RunLaunchTask();
                        return;
                    }
                }

                Directory.CreateDirectory(Path.GetDirectoryName(Program.LauncherLogPath));
                File.AppendAllText(Program.LauncherLogPath, DateTime.Now.ToString("o") + " exit=" + result + Environment.NewLine + output + Environment.NewLine + error + Environment.NewLine);
                Invoke(new Action(delegate
                {
                    ExitCode = result;
                    Close();
                    MessageBox.Show(TranslateFailure(finalLog, error.ToString()), "Antigravity 启动提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }));
            }
        }

        private static long GetLogLength()
        {
            try { return File.Exists(Program.SupervisorLogPath) ? new FileInfo(Program.SupervisorLogPath).Length : 0; }
            catch { return 0; }
        }

        private static string ReadLogSince(long startOffset)
        {
            try
            {
                if (!File.Exists(Program.SupervisorLogPath)) return "";
                using (var stream = new FileStream(Program.SupervisorLogPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                {
                    stream.Position = Math.Min(startOffset, stream.Length);
                    using (var reader = new StreamReader(stream, Encoding.UTF8, true)) return reader.ReadToEnd();
                }
            }
            catch { return ""; }
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

        private static CapsuleState ParseLogState(string logText)
        {
            var state = new CapsuleState();
            state.TargetProgress = 10;
            state.Ceiling = 25;
            state.ActiveStep = 0;
            state.FooterText = "正在确认账号与工作环境…";
            state.WorkspaceText = "等待前置检测完成…";

            string egressCountry = "";
            foreach (string line in logText.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                if (line.Contains("preflight_account_check_started"))
                {
                    state.ActiveStep = 0;
                    state.AccountPassed = false;
                    state.AccountText = "正在读取 Cockpit 账号与缓存额度…";
                    state.FooterText = "正在验证本地账号状态";
                }
                else if (line.Contains("preflight_account_check_completed"))
                {
                    string rawPlan = GetValue(line, "plan");
                    string planUpper = (rawPlan ?? "").ToUpperInvariant();
                    string plan = planUpper == "PRO" ? "Pro" : planUpper == "FREE" ? "Free" : rawPlan;
                    string h5 = GetValue(line, "gemini_5h");
                    string week = GetValue(line, "gemini_weekly");
                    state.AccountText = (string.IsNullOrEmpty(plan) ? "账号就绪" : plan) +
                        " · 5 小时 " + h5 + "% · 周 " + week + "%（本地缓存）";
                    state.AccountPassed = true;
                    state.ActiveStep = 1;
                    state.FooterText = "账号已就绪，正在选择专线…";
                    state.TargetProgress = Math.Max(state.TargetProgress, 22);
                }
                else if (line.Contains("candidate_discovery_completed"))
                {
                    string total = GetValue(line, "candidate_count");
                    state.LineText = "发现 " + total + " 条候选 · 正在准备测速";
                    state.ActiveStep = 1;
                    state.TargetProgress = Math.Max(state.TargetProgress, 25);
                }
                else if (line.Contains("pool_probe_started"))
                {
                    state.ActiveStep = 1;
                    state.LinePassed = false;
                    state.LineText = "多核并发探活中 · 同时竞速 " + GetValue(line, "pool_size") + " 条专线…";
                    state.FooterText = "多路并发校验 Google 204 / CloudCode / OAuth 与出口国家";
                    state.TargetProgress = Math.Max(state.TargetProgress, 30);
                }
                else if (line.Contains("pool_probe_completed"))
                {
                    state.ActiveStep = 1;
                    state.LineText = "并发竞速完成 · 耗时 " + GetValue(line, "elapsed_ms") + "ms · 优选可用 " + GetValue(line, "winners") + " 条";
                    state.TargetProgress = Math.Max(state.TargetProgress, 42);
                }
                else if (line.Contains("latency_probe_started"))
                {
                    state.ActiveStep = 1;
                    bool isPool = line.Contains("concurrent_pool");
                    state.LineText = (isPool ? "并发测速 " : "测速 ") + GetValue(line, "candidate_index") + "/" +
                        GetValue(line, "candidate_total") + " · " + GetValue(line, "region") + " 出口";
                }
                else if (line.Contains("latency_probe_passed"))
                {
                    bool isPool = line.Contains("concurrent_pool");
                    state.LineText = (isPool ? "并发优选 " : "已测速 ") + GetValue(line, "candidate_index") + "/" +
                        GetValue(line, "candidate_total") + " · " + GetValue(line, "region") +
                        " · 请求延迟 " + GetValue(line, "rtt_ms") + "ms";
                }
                else if (line.Contains("isolated_latency_failed"))
                {
                    bool isPool = line.Contains("concurrent_pool");
                    state.LineText = isPool
                        ? ("并发过滤 " + GetValue(line, "candidate_index") + "/" + GetValue(line, "candidate_total") + " · " + GetValue(line, "region") + " 未通，其他专线继续竞速")
                        : ("测速 " + GetValue(line, "candidate_index") + "/" + GetValue(line, "candidate_total") + " 未响应，继续检查其他节点");
                }
                else if (line.Contains("proxy_reused") && line.Contains("warm_fast_path"))
                {
                    state.ActiveStep = 1;
                    state.LinePassed = true;
                    state.LineText = "已复用本地专线 · 127.0.0.1:" + GetValue(line, "port");
                    state.FooterText = "正在秒级复检 Google 通路与真实 AI 生成…";
                    state.TargetProgress = Math.Max(state.TargetProgress, 35);
                }
                else if (line.Contains("warm_proxy_api_unhealthy"))
                {
                    state.ActiveStep = 1;
                    state.LinePassed = false;
                    state.LineText = "旧专线端点已失效 · 秒级切入多核重选…";
                    state.GooglePassed = false;
                    state.GoogleText = "等待新专线重新检验…";
                    state.FooterText = "检测到模型 API 不可达，自动切入多核并发重选";
                }
                else if (line.Contains("candidate_preflight_started"))
                {
                    state.ActiveStep = 1;
                    state.LinePassed = false;
                    state.LineText = "正式验证候选 " + GetValue(line, "candidate_index") + "/" +
                        GetValue(line, "candidate_total") + " · " + GetValue(line, "region");
                    state.GooglePassed = false;
                    state.GoogleText = "等待当前候选网络检查…";
                    state.ModelPassed = false;
                    state.ModelText = "等待当前候选模型验证…";
                    state.FooterText = "找到可用专线后即停止检测";
                    state.TargetProgress = Math.Max(state.TargetProgress, 35);
                }
                else if (line.Contains("candidate_preflight_passed"))
                {
                    state.LinePassed = true;
                    state.LineText = "专线已就绪 · " + GetValue(line, "region") +
                        " · 请求延迟 " + GetValue(line, "rtt_ms") + "ms";
                }
                else if (line.Contains("fast_startup_reused"))
                {
                    state.LinePassed = true;
                    state.LineText = "复用已验证专线 · 本轮延迟 " + GetValue(line, "rtt_ms") + "ms";
                    state.GooglePassed = true;
                    state.GoogleText = "Google 网络本轮探活成功";
                    state.ModelPassed = true;
                    state.ModelText = "本轮真实模型验证通过";
                    state.ActiveStep = 4;
                    state.TargetProgress = Math.Max(state.TargetProgress, 90);
                }
                else if (line.Contains("google_connectivity_started"))
                {
                    state.ActiveStep = 2;
                    state.GooglePassed = false;
                    state.GoogleText = "正在连接 Google 服务…";
                    state.FooterText = "检查 Google、模型 API 与 OAuth 网络可达性";
                }
                else if (line.Contains("google_probe_started"))
                {
                    state.ActiveStep = 2;
                    state.GoogleText = "正在请求 " + GetValue(line, "service") + "…";
                }
                else if (line.Contains("google_probe_completed"))
                {
                    string status = GetValue(line, "status");
                    state.GoogleText = GetValue(line, "service") + (status == "0" ?
                        " · 连接超时或失败" : " · HTTP " + status + " · " + GetValue(line, "rtt_ms") + "ms");
                }
                else if (line.Contains("google_connectivity_passed"))
                {
                    state.GooglePassed = true;
                    state.GoogleText = "端点已响应 · Google " + GetValue(line, "google") +
                        " / API " + GetValue(line, "api") + " / OAuth " + GetValue(line, "oauth");
                    state.TargetProgress = Math.Max(state.TargetProgress, 68);
                }
                else if (line.Contains("proxy_egress_country_passed"))
                {
                    egressCountry = GetValue(line, "country");
                    state.GoogleText = (state.GoogleText ?? "端点已响应") + " · 出口 " + egressCountry;
                }
                else if (line.Contains("formal_model_gate_started") || line.Contains("model_probe_waiting"))
                {
                    state.ActiveStep = 3;
                    state.ModelPassed = false;
                    string elapsed = GetValue(line, "elapsed_seconds");
                    state.ModelText = "正在请求真实 AI 回复" +
                        (string.IsNullOrEmpty(elapsed) ? "…" : " · 已等待 " + elapsed + " 秒 / 上限 40 秒");
                    state.FooterText = "正在使用 agy 验证真实模型生成";
                }
                else if (line.Contains("model_probe_aborted") || line.Contains("model_generation_probe_failed"))
                {
                    bool location = line.Contains("model_location");
                    state.ModelPassed = false;
                    state.ModelText = location ? "当前线路受地区限制 · 正在换线…" : "AI 验证失败或超时 · 正在换线…";
                    state.FooterText = location ? "地区限制，正在换线…" : "模型请求失败，正在尝试其他候选…";
                }
                else if (line.Contains("model_generation_probe_passed"))
                {
                    state.ModelText = "真实生成通过 · " + GetValue(line, "duration_ms") + "ms" +
                        (string.IsNullOrEmpty(egressCountry) ? "" : " · " + egressCountry + " 出口");
                    state.ModelPassed = true;
                    state.ActiveStep = 4;
                    state.FooterText = "模型验证通过，正在完成工作区启动…";
                    state.TargetProgress = Math.Max(state.TargetProgress, 88);
                }
                else if (line.Contains("antigravity_prelaunched_before_model_gate"))
                {
                    state.WorkspaceText = "编辑器已预启动，等待模型检查…";
                }
                else if (line.Contains("antigravity_started"))
                {
                    state.ActiveStep = 4;
                    state.WorkspaceText = "正在启动 Antigravity 客户端…";
                    state.TargetProgress = Math.Max(state.TargetProgress, 95);
                }
                else if (line.Contains("antigravity_ready") || line.Contains("antigravity_live_seamless_attached"))
                {
                    state.ActiveStep = 5;
                    state.WorkspacePassed = true;
                    state.WorkspaceText = "客户端与语言服务已就绪";
                    state.FooterText = "工作环境已就绪，正在打开工作区…";
                    state.TargetProgress = 100;
                }
            }

            return state;
        }

        private static string TranslateFailure(string logText, string stderr)
        {
            string all = logText + "\n" + stderr;
            if (all.Contains("mihomo_missing"))
                return "💡 未检测到本地代理软件\n\n请先确认电脑中已安装并启动 Clash Verge 或 Mihomo Party。";
            if (all.Contains("antigravity_missing"))
                return "💡 未找到 Antigravity 程序\n\n请确认 Antigravity 已安装在默认应用路径。";
            if (all.Contains("target_node_not_found"))
                return "💡 未发现可用专线\n\n请在你的 Clash 代理软件中更新一次订阅节点，确保包含日本或美国高速专线。";
            if (all.Contains("google_connectivity_failed") || all.Contains("proxy_egress_network_failure"))
                return "💡 无法连接 Google 服务\n\n当前网络暂无法连通 Google，请检查网络或在 Clash 中切换其他可用节点。";
            if (all.Contains("model_generation_probe_failed") || all.Contains("model_location"))
                return "💡 专线未通过 AI 模型验证\n\n当前节点可能受到地区限制，请在代理软件中切换到支持 Gemini 的专线。";
            if (all.Contains("localization_loader_failed"))
                return "💡 Antigravity 已启动，中文组件将在后台自动加载完成。";
            return "💡 启动连接稍有延迟\n\n网络通道尚未完全就绪，请确认代理软件运行正常后重试。";
        }

        private sealed class CapsuleState
        {
            internal string LineText;
            internal bool LinePassed = false;
            internal string GoogleText;
            internal bool GooglePassed = false;
            internal string ModelText;
            internal bool ModelPassed = false;
            internal string AccountText;
            internal bool AccountPassed = false;
            internal string WorkspaceText;
            internal bool WorkspacePassed = false;
            internal int ActiveStep = 0;
            internal string FooterText;
            internal int TargetProgress;
            internal int Ceiling;
        }
    }

    // ==========================================
    // 启动器设置面板 (LauncherSettingsForm)
    // ==========================================
    internal class LauncherSettingsForm : Form
    {
        private float uiScale = 1F;

        public LauncherSettingsForm()
        {
            Text = "启动器设置与工作台";
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterParent;
            AutoScaleMode = AutoScaleMode.None;
            DoubleBuffered = true;
            using (Graphics dpiGraphics = CreateGraphics()) { uiScale = Math.Max(1F, dpiGraphics.DpiX / 96F); }
            ClientSize = new Size(490, 304);
            BackColor = Color.FromArgb(248, 250, 252);
            ShowInTaskbar = false;
            TopMost = false;

            var lblTitle = new Label
            {
                Text = "启动器设置与工作台",
                Font = new Font("Microsoft YaHei UI", 11.5F, FontStyle.Bold),
                ForeColor = Color.FromArgb(23, 37, 61),
                Location = new Point(22, 16),
                Size = new Size(390, 28),
                TextAlign = ContentAlignment.MiddleLeft
            };
            var sep = new Panel
            {
                Location = new Point(22, 54),
                Size = new Size(446, 1),
                BackColor = Color.FromArgb(226, 232, 240)
            };
            var settings = LauncherSettings.Load();
            var chkAutoResume = new CheckBox
            {
                Text = "切号或网络重连后，自动恢复会话与任务上下文",
                Font = new Font("Microsoft YaHei UI", 10F),
                ForeColor = Color.FromArgb(30, 41, 59),
                Location = new Point(22, 68),
                Size = new Size(446, 26),
                AutoSize = false,
                Checked = settings.AutoResumeEnabled
            };
            var lblHint = new Label
            {
                Text = "账号切换或专线刷新后自动发送“继续”接力任务；关闭则仅静默换号。",
                Font = new Font("Microsoft YaHei UI", 8.8F),
                ForeColor = Color.FromArgb(100, 116, 139),
                Location = new Point(42, 98),
                Size = new Size(426, 36),
                AutoSize = false
            };

            var sep2 = new Panel
            {
                Location = new Point(22, 142),
                Size = new Size(446, 1),
                BackColor = Color.FromArgb(226, 232, 240)
            };
            var lblWorkbench = new Label
            {
                Text = "多分屏工作台记忆与恢复",
                Font = new Font("Microsoft YaHei UI", 10F, FontStyle.Bold),
                ForeColor = Color.FromArgb(30, 41, 59),
                Location = new Point(22, 154),
                Size = new Size(446, 24),
                TextAlign = ContentAlignment.MiddleLeft
            };

            var btnRestorePanes = new Button
            {
                Text = "恢复昨日 6 分屏",
                Font = new Font("Microsoft YaHei UI", 9.5F),
                Location = new Point(22, 186),
                Size = new Size(215, 36),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(241, 245, 249),
                ForeColor = Color.FromArgb(30, 41, 59),
                Cursor = Cursors.Hand
            };
            btnRestorePanes.FlatAppearance.BorderColor = Color.FromArgb(203, 213, 225);

            var btnSavePanes = new Button
            {
                Text = "记忆当前分屏",
                Font = new Font("Microsoft YaHei UI", 9.5F),
                Location = new Point(253, 186),
                Size = new Size(215, 36),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(241, 245, 249),
                ForeColor = Color.FromArgb(30, 41, 59),
                Cursor = Cursors.Hand
            };
            btnSavePanes.FlatAppearance.BorderColor = Color.FromArgb(203, 213, 225);

            var lblPanesStatus = new Label
            {
                Text = "",
                Font = new Font("Microsoft YaHei UI", 9F),
                ForeColor = Color.FromArgb(22, 163, 74),
                Location = new Point(22, 230),
                Size = new Size(446, 22),
                TextAlign = ContentAlignment.MiddleLeft
            };

            btnRestorePanes.Click += delegate
            {
                try
                {
                    string py = Program.ResolvePythonw();
                    string script = Path.Combine(Program.AppDirectory, "restore_workspace_panes.py");
                    if (File.Exists(script))
                    {
                        Process.Start(new ProcessStartInfo
                        {
                            FileName = py,
                            Arguments = "\"" + script + "\"",
                            WorkingDirectory = Program.AppDirectory,
                            UseShellExecute = false,
                            CreateNoWindow = true
                        });
                        lblPanesStatus.ForeColor = Color.FromArgb(22, 163, 74);
                        lblPanesStatus.Text = "✓ 已发送恢复指令，1~2 秒内自动布局";
                    }
                    else
                    {
                        lblPanesStatus.ForeColor = Color.FromArgb(220, 38, 38);
                        lblPanesStatus.Text = "× 脚本文件不存在: restore_workspace_panes.py";
                    }
                }
                catch (Exception ex)
                {
                    lblPanesStatus.ForeColor = Color.FromArgb(220, 38, 38);
                    lblPanesStatus.Text = "× " + ex.Message;
                }
            };

            btnSavePanes.Click += delegate
            {
                try
                {
                    string py = Program.ResolvePythonw();
                    string script = Path.Combine(Program.AppDirectory, "restore_workspace_panes.py");
                    if (File.Exists(script))
                    {
                        Process.Start(new ProcessStartInfo
                        {
                            FileName = py,
                            Arguments = "\"" + script + "\" --save",
                            WorkingDirectory = Program.AppDirectory,
                            UseShellExecute = false,
                            CreateNoWindow = true
                        });
                        lblPanesStatus.ForeColor = Color.FromArgb(22, 163, 74);
                        lblPanesStatus.Text = "✓ 已保存当前多窗口分屏布局";
                    }
                    else
                    {
                        lblPanesStatus.ForeColor = Color.FromArgb(220, 38, 38);
                        lblPanesStatus.Text = "× 脚本文件不存在: restore_workspace_panes.py";
                    }
                }
                catch (Exception ex)
                {
                    lblPanesStatus.ForeColor = Color.FromArgb(220, 38, 38);
                    lblPanesStatus.Text = "× " + ex.Message;
                }
            };

            var btnOk = new Button
            {
                Text = "确定",
                Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold),
                Location = new Point(ClientSize.Width - 106, ClientSize.Height - 44),
                Size = new Size(84, 32),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(37, 99, 235),
                ForeColor = Color.White,
                Cursor = Cursors.Hand
            };
            btnOk.FlatAppearance.BorderSize = 0;
            btnOk.Click += delegate
            {
                settings.AutoResumeEnabled = chkAutoResume.Checked;
                settings.Save();
                Close();
            };
            var closeBtn = new CapsuleCloseButton
            {
                Location = new Point(ClientSize.Width - 36, 14),
                Size = new Size(22, 22)
            };
            closeBtn.Click += delegate { Close(); };

            Controls.Add(lblTitle);
            Controls.Add(sep);
            Controls.Add(chkAutoResume);
            Controls.Add(lblHint);
            Controls.Add(sep2);
            Controls.Add(lblWorkbench);
            Controls.Add(btnRestorePanes);
            Controls.Add(btnSavePanes);
            Controls.Add(lblPanesStatus);
            Controls.Add(btnOk);
            Controls.Add(closeBtn);

            if (uiScale != 1F) Scale(new SizeF(uiScale, uiScale));

            MouseDown += delegate(object s, MouseEventArgs me)
            {
                if (me.Button == MouseButtons.Left)
                {
                    Program.ReleaseCapture();
                    Program.SendMessage(Handle, 0xA1, 0x2, 0);
                }
            };
        }

        protected override void OnHandleCreated(EventArgs e)
        {
            base.OnHandleCreated(e);
            try
            {
                int val = Program.DWMWCP_ROUND;
                Program.DwmSetWindowAttribute(Handle, Program.DWMWA_WINDOW_CORNER_PREFERENCE, ref val, sizeof(int));
            }
            catch { }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            using (var pen = new Pen(Color.FromArgb(203, 213, 225), 1F))
            {
                e.Graphics.DrawRectangle(pen, 0, 0, Width - 1, Height - 1);
            }
        }

        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams cp = base.CreateParams;
                cp.ClassStyle |= 0x00020000;
                return cp;
            }
        }
    }
}
