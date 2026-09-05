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
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]
[assembly: AssemblyInformationalVersion("1.0.0")]

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
        internal static readonly string IconPath = Path.Combine(AppDirectory, "Antigravity-Launcher.ico");

        private const string SingleInstanceMutexName = @"Local\AntigravityLauncherSingleInstance";
        private const string BackgroundMutexName = @"Local\AntigravitySelfHealingLauncherBackground";
        internal const string SupervisorMutexName = @"Local\AntigravitySupervisorRun";

        private static Mutex singleInstanceMutex;

        internal static void TraceLog(string msg)
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(LauncherLogPath));
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

            // 3. 检查 Antigravity 是否已经在运行中 (热启动场景：带 3 秒自动进入的双选卡片)
            bool antigravityRunning = IsAntigravityRunning();
            TraceLog("antigravityRunning=" + antigravityRunning + ", forceLaunch=" + forceLaunch);

            if (antigravityRunning && !forceLaunch)
            {
                TraceLog("Displaying AntigravityHotLaunchChoiceForm...");
                var choiceForm = new AntigravityHotLaunchChoiceForm();
                Application.Run(choiceForm);

                if (choiceForm.Action == HotLaunchAction.Activate)
                {
                    TraceLog("Hot launch: activating existing main window...");
                    bool activated = ActivateExistingAntigravity();
                    TraceLog("Activate result: " + activated);
                    return 0;
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
            var capsule = new AntigravityLaunchCapsuleForm(forceLaunch ? "UserRequestedRepair" : GetRecoveryReason(args));
            Application.Run(capsule);

            if (capsule.ExitCode == 0)
            {
                ActivateExistingAntigravity();
                EnsureWatcherRunning();
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
                if (value == "NetworkFailure" || value == "LocationFailure") return value;
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
            try
            {
                Process[] procs = Process.GetProcessesByName("Antigravity");
                return procs != null && procs.Length > 0;
            }
            catch { return false; }
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

                TraceLog("ActivateExistingAntigravity: successfully brought to foreground.");
                return true;
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
    // 热启动选择动作枚举
    // ==========================================
    internal enum HotLaunchAction { Activate, Repair, Cancel }

    // ==========================================
    // 视觉核心：热启动拟态胶囊按钮 (HotLaunchButton)
    // ==========================================
    internal sealed class HotLaunchButton : Control
    {
        private bool isHovered = false;
        private bool isPressed = false;
        private string buttonText;

        internal HotLaunchButton(string text)
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
            buttonText = text;
            Cursor = Cursors.Hand;
        }

        internal string ButtonText
        {
            get { return buttonText; }
            set { buttonText = value; Invalidate(); }
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

                using (var fill = new LinearGradientBrush(r, c1, c2, 90F))
                using (var pen = new Pen(border, 1.2F))
                {
                    e.Graphics.FillPath(fill, path);
                    e.Graphics.DrawPath(pen, path);
                }

                using (var font = new Font("Microsoft YaHei UI", 10F, FontStyle.Bold))
                using (var brush = new SolidBrush(textColor))
                using (var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center })
                {
                    e.Graphics.DrawString(buttonText, font, brush, r, sf);
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
    // 热启动拟态选项卡片：带 3 秒自动进入倒计时 (AntigravityHotLaunchChoiceForm)
    // ==========================================
    internal class AntigravityHotLaunchChoiceForm : Form
    {
        internal HotLaunchAction Action { get; private set; }
        private int remainingSeconds = 3;
        private System.Windows.Forms.Timer countdownTimer;
        private HotLaunchButton btnActivate;
        private HotLaunchButton btnRepair;
        private CapsuleCloseButton closeButton;
        private Image appIcon = null;
        private string egressBadgeText = "美国专线就绪";
        private string statusBadgeText = "● 运行中";
        private string subtitleText = "当前专线连接畅通 · 可秒切代码窗口，或一键重启自愈";

        internal AntigravityHotLaunchChoiceForm()
        {
            Action = HotLaunchAction.Cancel;
            Text = "Antigravity 启动助手";
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(480, 146);
            BackColor = Color.FromArgb(248, 250, 252);
            ShowInTaskbar = false;
            TopMost = true;
            KeyPreview = true;

            appIcon = Program.LoadIconOrPng(Program.IconPath);

            try
            {
                if (File.Exists(Program.SupervisorStatePath))
                {
                    string json = File.ReadAllText(Program.SupervisorStatePath);
                    var mEgress = System.Text.RegularExpressions.Regex.Match(json, "\"egress_country\"\\s*:\\s*\"([^\"]+)\"");
                    string egress = mEgress.Success ? mEgress.Groups[1].Value.Trim().ToUpperInvariant() : "";
                    if (egress == "US")
                        egressBadgeText = "美国专线就绪";
                    else if (egress == "JP")
                        egressBadgeText = "日本专线就绪";
                    else if (!string.IsNullOrEmpty(egress))
                        egressBadgeText = egress + " 专线就绪";
                }
            }
            catch { }

            closeButton = new CapsuleCloseButton
            {
                Location = new Point(ClientSize.Width - 32, 12),
                Size = new Size(22, 22)
            };
            closeButton.Click += delegate
            {
                StopTimer();
                Action = HotLaunchAction.Cancel;
                Close();
            };

            btnActivate = new HotLaunchButton("进入代码窗口 (3s)")
            {
                Location = new Point(20, 78),
                Size = new Size(212, 46)
            };
            btnActivate.Click += delegate
            {
                StopTimer();
                Action = HotLaunchAction.Activate;
                Close();
            };

            btnRepair = new HotLaunchButton("⚡ 一键重启修复")
            {
                Location = new Point(248, 78),
                Size = new Size(212, 46)
            };
            btnRepair.Click += delegate
            {
                StopTimer();
                Action = HotLaunchAction.Repair;
                Close();
            };

            Controls.Add(closeButton);
            Controls.Add(btnActivate);
            Controls.Add(btnRepair);

            MouseDown += delegate(object s, MouseEventArgs me)
            {
                if (me.Button == MouseButtons.Left)
                {
                    Program.ReleaseCapture();
                    Program.SendMessage(Handle, 0xA1, 0x2, 0);
                }
            };

            countdownTimer = new System.Windows.Forms.Timer { Interval = 1000 };
            countdownTimer.Tick += delegate
            {
                remainingSeconds--;
                if (remainingSeconds <= 0)
                {
                    StopTimer();
                    Action = HotLaunchAction.Activate;
                    Close();
                }
                else
                {
                    btnActivate.ButtonText = "进入代码窗口 (" + remainingSeconds + "s)";
                }
            };
            countdownTimer.Start();
        }

        private void StopTimer()
        {
            if (countdownTimer != null)
            {
                countdownTimer.Stop();
                countdownTimer.Dispose();
                countdownTimer = null;
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

        private static void DrawPillBadge(Graphics g, string text, int x, int y, Color bg, Color border, Color fg)
        {
            using (var font = new Font("Microsoft YaHei UI", 8.5F, FontStyle.Bold))
            {
                var size = g.MeasureString(text, font);
                var rect = new Rectangle(x, y, (int)size.Width + 14, 20);
                using (var path = RoundedRectangle(rect, 10))
                using (var brush = new SolidBrush(bg))
                using (var pen = new Pen(border, 1F))
                using (var fgBrush = new SolidBrush(fg))
                using (var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center })
                {
                    g.FillPath(brush, path);
                    g.DrawPath(pen, path);
                    g.DrawString(text, font, fgBrush, rect, sf);
                }
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;
            var bounds = new Rectangle(0, 0, Width - 1, Height - 1);

            using (var path = RoundedRectangle(bounds, 16))
            using (var fill = new LinearGradientBrush(bounds, Color.FromArgb(252, 254, 255), Color.FromArgb(238, 246, 254), 90F))
            using (var border = new Pen(Color.FromArgb(200, 220, 240), 1.2F))
            {
                e.Graphics.FillPath(fill, path);
                e.Graphics.DrawPath(border, path);
            }

            using (var highlight = new Pen(Color.FromArgb(180, 255, 255, 255), 1.5F))
            {
                e.Graphics.DrawLine(highlight, 20, 2, Width - 20, 2);
            }

            if (appIcon != null)
            {
                e.Graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                e.Graphics.DrawImage(appIcon, new Rectangle(20, 16, 36, 36));
            }

            using (var fontTitle = new Font("Microsoft YaHei UI", 12F, FontStyle.Bold))
            using (var titleBrush = new SolidBrush(Color.FromArgb(15, 35, 60)))
            {
                e.Graphics.DrawString("Antigravity", fontTitle, titleBrush, new PointF(64, 15));
            }

            int currentBadgeX = 168;
            using (var fontBadge = new Font("Microsoft YaHei UI", 8.5F, FontStyle.Bold))
            {
                var size1 = e.Graphics.MeasureString(egressBadgeText, fontBadge);
                DrawPillBadge(e.Graphics, egressBadgeText, currentBadgeX, 16, Color.FromArgb(224, 238, 255), Color.FromArgb(147, 197, 253), Color.FromArgb(29, 78, 216));
                currentBadgeX += (int)size1.Width + 14 + 8;
                DrawPillBadge(e.Graphics, statusBadgeText, currentBadgeX, 16, Color.FromArgb(220, 252, 231), Color.FromArgb(134, 239, 172), Color.FromArgb(21, 128, 61));
            }

            using (var fontSubtitle = new Font("Microsoft YaHei UI", 9F))
            using (var subBrush = new SolidBrush(Color.FromArgb(71, 85, 105)))
            {
                e.Graphics.DrawString(subtitleText, fontSubtitle, subBrush, new PointF(66, 44));
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

        // 动态状态模型
        private string lineStatusText = "正在检索可用专线…";
        private bool linePassed = false;
        private string googleStatusText = "等待网络握手…";
        private bool googlePassed = false;
        private string modelStatusText = "等待链路验证…";
        private bool modelPassed = false;
        private string footerStatusText = "正在匹配最优专线通道…";

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
            var bounds = new Rectangle(0, 0, Width - 1, Height - 1);

            // 1. 卡片磨砂与拟态背景
            using (var path = RoundedRectangle(bounds, 16))
            using (var fill = new LinearGradientBrush(bounds, Color.FromArgb(250, 252, 255), Color.FromArgb(236, 244, 252), 90F))
            using (var border = new Pen(Color.FromArgb(205, 222, 238), 1.2F))
            {
                e.Graphics.FillPath(fill, path);
                e.Graphics.DrawPath(border, path);
            }

            using (var highlight = new Pen(Color.FromArgb(140, 255, 255, 255), 1.5F))
            {
                e.Graphics.DrawLine(highlight, 20, 2, Width - 20, 2);
            }

            // 2. 高清 Antigravity 图标
            if (appIcon != null)
            {
                e.Graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                e.Graphics.DrawImage(appIcon, new Rectangle(20, 16, 36, 36));
            }

            // 3. 标题
            using (var fontTitle = new Font("Microsoft YaHei UI", 12F, FontStyle.Bold))
            {
                TextRenderer.DrawText(e.Graphics, "Antigravity", fontTitle, new Point(64, 16), Color.FromArgb(16, 43, 69));
            }

            // 4. 拟态策略徽标 (直观体现底层：美国优先、延迟优选、记忆好用)
            DrawPillBadge(e.Graphics, "🇺🇸 美国优先", 170, 19, Color.FromArgb(219, 234, 254), Color.FromArgb(147, 197, 253), Color.FromArgb(29, 78, 216));
            DrawPillBadge(e.Graphics, "⚡ 延迟优选", 260, 19, Color.FromArgb(224, 231, 255), Color.FromArgb(165, 180, 252), Color.FromArgb(67, 56, 202));
            DrawPillBadge(e.Graphics, "⭐ 记忆好用", 348, 19, Color.FromArgb(220, 252, 231), Color.FromArgb(134, 239, 172), Color.FromArgb(21, 128, 61));

            // 5. 三行直观、清晰的通路状态步骤 (无白边缝隙，融入背景)
            using (var fontStep = new Font("Microsoft YaHei UI", 9F))
            using (var fontDot = new Font("Segoe UI", 8.5F, FontStyle.Bold))
            {
                // 行 1：本地专线
                DrawStepRow(e.Graphics, fontStep, fontDot, 22, 64, "本地专线", lineStatusText, linePassed);
                // 行 2：Google 通路
                DrawStepRow(e.Graphics, fontStep, fontDot, 22, 90, "Google 通路", googleStatusText, googlePassed);
                // 行 3：AI 模型服务
                DrawStepRow(e.Graphics, fontStep, fontDot, 22, 116, "AI 模型服务", modelStatusText, modelPassed);
            }

            // 6. 底部柔和状态文字
            using (var fontFooter = new Font("Microsoft YaHei UI", 8.5F))
            {
                TextRenderer.DrawText(e.Graphics, footerStatusText, fontFooter, new Point(22, 168), Color.FromArgb(100, 116, 139));
            }
        }

        private void DrawStepRow(Graphics g, Font fontText, Font fontDot, int x, int y, string label, string text, bool passed)
        {
            string symbol = passed ? "✔" : "●";
            Color symbolColor = passed ? Color.FromArgb(22, 163, 74) : Color.FromArgb(59, 130, 246);
            Color labelColor = Color.FromArgb(30, 41, 59);
            Color contentColor = passed ? Color.FromArgb(21, 128, 61) : Color.FromArgb(71, 85, 105);

            TextRenderer.DrawText(g, symbol, fontDot, new Point(x, y + 1), symbolColor);
            TextRenderer.DrawText(g, label + "：", fontText, new Point(x + 18, y), labelColor);
            int labelWidth = TextRenderer.MeasureText(label + "：", fontText).Width;
            TextRenderer.DrawText(g, text, fontText, new Point(x + 18 + labelWidth - 2, y), contentColor);
        }

        private void InitializeComponent()
        {
            Text = "Antigravity";
            ClientSize = new Size(520, 204);
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            ShowInTaskbar = true;
            TopMost = true;
            BackColor = Color.FromArgb(236, 244, 252);
            DoubleBuffered = true;

            appIcon = Program.LoadIconOrPng(Program.IconPath);
            if (File.Exists(Program.IconPath))
            {
                try { Icon = new Icon(Program.IconPath); } catch { }
            }

            MouseDown += OnWindowDrag;

            var btnClose = new CapsuleCloseButton
            {
                Location = new Point(Width - 32, 10)
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

            progressBar = new CapsuleProgress
            {
                Location = new Point(22, 148),
                Size = new Size(476, 7),
                ProgressValue = 3
            };

            Controls.AddRange(new Control[] { btnClose, progressBar });

            Shown += delegate
            {
                try
                {
                    BringToFront();
                    Activate();
                }
                catch { }
                Task.Run(delegate { RunLaunchTask(); });
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
                lineStatusText = "已锁定高速专线 [美日低延迟]";
                linePassed = true;
                googleStatusText = "连通正常 · 授权畅通";
                googlePassed = true;
                modelStatusText = "Gemini 编程模型验证通过";
                modelPassed = true;
                footerStatusText = Program.IsAntigravityRunning() ? "🚀 最优专线已就绪，正在切回代码窗口…" : "🚀 通路已全部就绪，正在打开 Antigravity…";
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

            while ((DateTime.Now - waitStart).TotalSeconds < 55)
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
                    return;
                }
                logStartOffset = GetLogLength();
            }

            var psi = new ProcessStartInfo
            {
                FileName = @"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + Program.ScriptPath + "\" -RecoveryReason " + recoveryReason,
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

                while (!process.HasExited)
                {
                    if (userCancelled) { ExitCode = 0; return; }
                    string logChunk = ReadLogSince(logStartOffset);
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
                        if (!string.IsNullOrEmpty(state.FooterText)) footerStatusText = state.FooterText;
                        progressBar.ProgressValue = prog;
                        Invalidate();
                    }));

                    Thread.Sleep(200);
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
            state.FooterText = "正在匹配最优专线通道…";

            int discoveredTotal = 0;
            int candidateIndex = 0;
            int candidateTotal = 0;
            string egressCountry = "US";
            string rttStr = "";

            foreach (string line in logText.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                if (line.Contains("candidate_discovery_completed"))
                {
                    string countStr = GetValue(line, "candidate_count");
                    int parsed;
                    if (int.TryParse(countStr, out parsed) && parsed > 0)
                    {
                        discoveredTotal = parsed;
                        candidateTotal = parsed;
                    }
                    state.TargetProgress = Math.Max(state.TargetProgress, 25);
                    state.Ceiling = Math.Max(state.Ceiling, 35);
                }
                else if (line.Contains("candidate_preflight_started"))
                {
                    int pIndex, pTotal;
                    if (int.TryParse(GetValue(line, "candidate_index"), out pIndex) && pIndex > 0) candidateIndex = pIndex;
                    else candidateIndex++;
                    if (int.TryParse(GetValue(line, "candidate_total"), out pTotal) && pTotal > 0) candidateTotal = pTotal;
                    state.TargetProgress = Math.Max(state.TargetProgress, 35);
                    state.Ceiling = Math.Max(state.Ceiling, 45);
                }
                else if (line.Contains("candidate_preflight_passed"))
                {
                    state.LinePassed = true;
                }
                else if (line.Contains("proxy_started") || line.Contains("proxy_reused"))
                {
                    state.GoogleText = "专属通道 17897 已连通，正在测速…";
                    state.TargetProgress = Math.Max(state.TargetProgress, 50);
                    state.Ceiling = Math.Max(state.Ceiling, 60);
                }
                else if (line.Contains("google_connectivity_passed"))
                {
                    rttStr = GetValue(line, "rtt_ms");
                    string suffix = string.IsNullOrEmpty(rttStr) ? "" : (" · 延迟 " + rttStr + "ms");
                    state.GoogleText = "连通正常" + suffix;
                    state.GooglePassed = true;
                    state.TargetProgress = Math.Max(state.TargetProgress, 68);
                    state.Ceiling = Math.Max(state.Ceiling, 78);
                }
                else if (line.Contains("proxy_egress_country_passed"))
                {
                    string c = GetValue(line, "country");
                    if (!string.IsNullOrEmpty(c)) egressCountry = c;
                    state.TargetProgress = Math.Max(state.TargetProgress, 75);
                    state.Ceiling = Math.Max(state.Ceiling, 82);
                }
                else if (line.Contains("model_generation_probe_passed") || line.Contains("model_generation_fast_passed"))
                {
                    string countryDesc = egressCountry == "US" ? "美国 US" : (egressCountry == "JP" ? "日本 JP" : egressCountry);
                    state.ModelText = "Gemini 编程模型验证通过 [出口 " + countryDesc + "]";
                    state.ModelPassed = true;
                    state.FooterText = "🚀 通路已全部通过，正在拉起 Antigravity…";
                    state.TargetProgress = Math.Max(state.TargetProgress, 88);
                    state.Ceiling = Math.Max(state.Ceiling, 94);
                }
                else if (line.Contains("antigravity_started"))
                {
                    state.FooterText = "正在启动 Antigravity 代码编辑器…";
                    state.TargetProgress = Math.Max(state.TargetProgress, 95);
                    state.Ceiling = Math.Max(state.Ceiling, 98);
                }
                else if (line.Contains("antigravity_ready") || line.Contains("localization_loader_succeeded"))
                {
                    state.FooterText = "已就绪，正在打开工作区…";
                    state.TargetProgress = 100;
                    state.Ceiling = 100;
                }
            }

            // 组合专线状态文本
            if (discoveredTotal > 0 || candidateTotal > 0)
            {
                int total = candidateTotal > 0 ? candidateTotal : discoveredTotal;
                int current = candidateIndex > 0 ? candidateIndex : 1;
                state.LineText = "已发现 " + total + " 条可用专线 · 正在验证 " + current + "/" + total + " [美国 · 低延迟]";
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
                return "💡 未发现可用专线\n\n请在你的 Clash 代理软件中更新一次订阅节点，确保包含美国或日本专线。";
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
            internal string FooterText;
            internal int TargetProgress;
            internal int Ceiling;
        }
    }
}
