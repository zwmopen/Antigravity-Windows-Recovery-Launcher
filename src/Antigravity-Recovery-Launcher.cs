using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

[assembly: AssemblyTitle("Antigravity 智能启动器与节点中控台")]
[assembly: AssemblyProduct("Antigravity 智能启动器")]
[assembly: AssemblyCopyright("Copyright © 2026 zwmopen")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]
[assembly: AssemblyInformationalVersion("1.0.0-preview")]

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
        private const string ShowPanelEventName = @"Local\AntigravityLauncherShowPanelEvent";
        private const string BackgroundMutexName = @"Local\AntigravitySelfHealingLauncherBackground";
        internal const string SupervisorMutexName = @"Local\AntigravitySupervisorRun";

        private static Mutex singleInstanceMutex;
        private static EventWaitHandle showPanelEvent;

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
            TraceLog("Main invoked: " + (args != null ? string.Join(" ", args) : "null"));
            bool backgroundMode = HasArgument(args, "--background");
            bool forceLaunch = HasArgument(args, "--force-launch");
            bool showPanelDirect = HasArgument(args, "--show-panel");

            // 1. 后台静默自愈模式 (由 AccountWatcher 调度)
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

            // 2. 检查是否已有常驻实例正在运行
            bool createdNew;
            try
            {
                singleInstanceMutex = new Mutex(true, SingleInstanceMutexName, out createdNew);
            }
            catch (AbandonedMutexException)
            {
                createdNew = true;
            }

            TraceLog("singleInstanceMutex createdNew=" + createdNew);

            if (!createdNew)
            {
                // 已有常驻实例在跑：发送 IPC 信号呼出毛玻璃控制中心
                TraceLog("Existing instance detected, signaling show panel...");
                SignalShowPanel();
                return 0;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
            Application.ThreadException += delegate(object sender, ThreadExceptionEventArgs e)
            {
                TraceLog("UI_THREAD_EXCEPTION: " + e.Exception.ToString());
            };
            AppDomain.CurrentDomain.UnhandledException += delegate(object sender, UnhandledExceptionEventArgs e)
            {
                TraceLog("DOMAIN_EXCEPTION: " + (e.ExceptionObject != null ? e.ExceptionObject.ToString() : "unknown"));
            };

            // 3. 单实例初始化事件监听器
            InitializeNamedEventWatcher();

            bool antigravityRunning = IsAntigravityRunning();
            TraceLog("antigravityRunning=" + antigravityRunning + ", showPanelDirect=" + showPanelDirect + ", forceLaunch=" + forceLaunch);

            // 4. 场景判断：
            // 如果 Antigravity 已经在正常运行中，或者显式指定 --show-panel：
            // 直接展示毛玻璃节点控制中心，绝不打扰正在编写的代码！
            if ((antigravityRunning || showPanelDirect) && !forceLaunch)
            {
                TraceLog("Creating LauncherAppContext with showControlCenterOnStartup=true");
                try
                {
                    var context = new LauncherAppContext(showControlCenterOnStartup: true);
                    TraceLog("Entering Application.Run(context)...");
                    Application.Run(context);
                    TraceLog("Application.Run(context) returned normally");
                }
                catch (Exception ex)
                {
                    TraceLog("Application.Run threw: " + ex.ToString());
                }
                return 0;
            }

            // 5. 冷启动或强制自愈模式：显示毛玻璃自愈进度窗口
            TraceLog("Launching RecoveryLauncherForm...");
            var recoveryForm = new RecoveryLauncherForm(GetRecoveryReason(args));
            var dialogResult = recoveryForm.ShowDialog();

            if (dialogResult == DialogResult.OK)
            {
                // 自愈完成，确保守护进程运行，并转入后台常驻托盘模式
                EnsureWatcherRunning();
                var context = new LauncherAppContext(showControlCenterOnStartup: false);
                Application.Run(context);
                return 0;
            }

            return recoveryForm.ExitCode;
        }

        private static void InitializeNamedEventWatcher()
        {
            try
            {
                bool createdNew;
                showPanelEvent = new EventWaitHandle(false, EventResetMode.AutoReset, ShowPanelEventName, out createdNew);
                ThreadPool.RegisterWaitForSingleObject(showPanelEvent, delegate
                {
                    if (LauncherAppContext.CurrentContext != null)
                    {
                        LauncherAppContext.CurrentContext.PostShowControlCenter();
                    }
                }, null, -1, false);
            }
            catch { }
        }

        internal static void SignalShowPanel()
        {
            try
            {
                EventWaitHandle evt;
                if (EventWaitHandle.TryOpenExisting(ShowPanelEventName, out evt))
                {
                    evt.Set();
                    evt.Dispose();
                }
            }
            catch { }
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
                if (!File.Exists(WatcherPath) || IsOwnWatcherRunning()) return;
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

        internal static bool IsAntigravityRunning()
        {
            try
            {
                Process[] procs = Process.GetProcessesByName("Antigravity");
                return procs != null && procs.Length > 0;
            }
            catch { return false; }
        }

        // ==========================================
        // Win32 穿透唤醒与置顶逻辑 (突破 Windows 焦点限制)
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
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll")]
        private static extern int GetClassName(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

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

        [DllImport("kernel32.dll")]
        private static extern uint GetCurrentThreadId();

        [StructLayout(LayoutKind.Sequential)]
        private struct RECT { public int Left, Top, Right, Bottom; }

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

            IntPtr foundHwnd = IntPtr.Zero;
            EnumWindowsProc checkWindow = delegate(IntPtr hWnd, IntPtr lParam)
            {
                uint pid;
                GetWindowThreadProcessId(hWnd, out pid);
                if (!pids.Contains(pid)) return true;
                if (!IsWindowVisible(hWnd)) return true;

                RECT r;
                if (!GetWindowRect(hWnd, out r)) return true;
                int width = r.Right - r.Left;
                int height = r.Bottom - r.Top;
                if (width < 300 || height < 200) return true;

                var sbClass = new StringBuilder(256);
                GetClassName(hWnd, sbClass, 256);
                string className = sbClass.ToString();
                if (className.Contains("Host") || className.Contains("Dde") || className.Contains("IME"))
                    return true;

                foundHwnd = hWnd;
                return false;
            };

            EnumWindows(checkWindow, IntPtr.Zero);
            if (foundHwnd == IntPtr.Zero)
            {
                IntPtr hDesk = OpenDesktop("default", 0, false, 0x01FF);
                if (hDesk != IntPtr.Zero)
                {
                    try { EnumDesktopWindows(hDesk, checkWindow, IntPtr.Zero); }
                    finally { CloseDesktop(hDesk); }
                }
            }

            return foundHwnd;
        }

        internal static bool ActivateExistingAntigravity()
        {
            IntPtr hWnd = FindAntigravityMainWindow();
            if (hWnd == IntPtr.Zero) return false;

            try
            {
                ShowWindowAsync(hWnd, 9); // SW_RESTORE
                ShowWindow(hWnd, 5);      // SW_SHOW

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

                return true;
            }
            catch
            {
                return false;
            }
        }

        internal static void ForceForeground(IntPtr hWnd)
        {
            try
            {
                ShowWindowAsync(hWnd, 9); // SW_RESTORE
                ShowWindow(hWnd, 5);      // SW_SHOW

                IntPtr fgWnd = GetForegroundWindow();
                uint fgPid;
                uint fgThread = GetWindowThreadProcessId(fgWnd, out fgPid);
                uint curThread = GetCurrentThreadId();
                bool attached = false;
                if (fgThread != 0 && fgThread != curThread)
                {
                    attached = AttachThreadInput(curThread, fgThread, true);
                }

                keybd_event(0x12, 0, 0, 0);
                keybd_event(0x12, 0, 2, 0);

                BringWindowToTop(hWnd);
                SetForegroundWindow(hWnd);
                SwitchToThisWindow(hWnd, true);

                if (attached)
                {
                    AttachThreadInput(curThread, fgThread, false);
                }
            }
            catch { }
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
    }

    // ==========================================
    // 视觉核心：毛玻璃圆角卡片渲染组件
    // ==========================================
    internal class GlassPanel : Panel
    {
        internal GlassPanel()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
        }

        internal static GraphicsPath RoundedRectangle(Rectangle rectangle, int radius)
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
            using (var fill = new LinearGradientBrush(bounds, Color.FromArgb(250, 252, 255), Color.FromArgb(235, 244, 252), 90F))
            using (var border = new Pen(Color.FromArgb(235, 255, 255, 255), 1.2F))
            {
                e.Graphics.FillPath(fill, path);
                e.Graphics.DrawPath(border, path);
            }
            using (var highlight = new Pen(Color.FromArgb(120, 255, 255, 255), 2F))
            {
                e.Graphics.DrawLine(highlight, 24, 3, Width - 24, 3);
            }
        }
    }

    // ==========================================
    // 拟态与玻璃卡片组件 (NeoCardPanel)
    // ==========================================
    internal class NeoCardPanel : Panel
    {
        public int CornerRadius { get; set; }

        internal NeoCardPanel()
        {
            CornerRadius = 16;
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
        }

        protected override void OnResize(EventArgs eventArgs)
        {
            base.OnResize(eventArgs);
            if (Width > CornerRadius * 2 && Height > CornerRadius * 2)
            {
                this.Region = new Region(GlassPanel.RoundedRectangle(new Rectangle(0, 0, Width, Height), CornerRadius));
            }
            Invalidate();
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var bounds = new Rectangle(0, 0, Width - 1, Height - 1);
            using (var path = GlassPanel.RoundedRectangle(bounds, CornerRadius))
            using (var fill = new LinearGradientBrush(bounds, Color.FromArgb(250, 253, 255), Color.FromArgb(236, 245, 252), 90F))
            using (var border = new Pen(Color.FromArgb(240, 255, 255, 255), 1.2F))
            {
                e.Graphics.FillPath(fill, path);
                e.Graphics.DrawPath(border, path);
            }
            using (var highlight = new Pen(Color.FromArgb(140, 255, 255, 255), 2F))
            {
                e.Graphics.DrawLine(highlight, CornerRadius + 4, 2, Width - CornerRadius - 4, 2);
            }
        }
    }

    // ==========================================
    // 自绘拟态按键与胶囊药丸组件 (NeoButton)
    // ==========================================
    internal class NeoButton : Control, IButtonControl
    {
        public bool IsPrimary { get; set; }
        public bool IsPill { get; set; }
        public int CornerRadius { get; set; }
        public DialogResult DialogResult { get; set; }
        private bool isHovered = false;
        private bool isPressed = false;

        public void NotifyDefault(bool value) { }
        public void PerformClick() { OnClick(EventArgs.Empty); }

        public NeoButton()
        {
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.ResizeRedraw, true);
            Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold);
            Cursor = Cursors.Hand;
            CornerRadius = 12;
            Size = new Size(120, 36);
        }

        protected override void OnMouseEnter(EventArgs e) { isHovered = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { isHovered = false; isPressed = false; Invalidate(); base.OnMouseLeave(e); }
        protected override void OnMouseDown(MouseEventArgs mevent) { if (mevent.Button == MouseButtons.Left) { isPressed = true; Invalidate(); } base.OnMouseDown(mevent); }
        protected override void OnMouseUp(MouseEventArgs mevent) { isPressed = false; Invalidate(); base.OnMouseUp(mevent); }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
            e.Graphics.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;

            Color parentBg = Color.FromArgb(223, 234, 242);
            if (Parent != null)
            {
                if (Parent.BackColor != Color.Transparent) parentBg = Parent.BackColor;
                else if (Parent.Parent != null && Parent.Parent.BackColor != Color.Transparent) parentBg = Parent.Parent.BackColor;
            }
            e.Graphics.Clear(parentBg);

            int radius = IsPill ? (Height / 2) : CornerRadius;
            var rect = new Rectangle(0, 0, Width - 1, Height - 1);

            using (var path = GlassPanel.RoundedRectangle(rect, radius))
            {
                if (!Enabled)
                {
                    using (var brush = new SolidBrush(Color.FromArgb(214, 225, 235)))
                        e.Graphics.FillPath(brush, path);
                    using (var pen = new Pen(Color.FromArgb(198, 210, 222), 1F))
                        e.Graphics.DrawPath(pen, path);
                    TextRenderer.DrawText(e.Graphics, Text, Font, rect, Color.FromArgb(145, 165, 185), TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
                    return;
                }

                if (IsPrimary)
                {
                    Color cTop = isPressed ? Color.FromArgb(20, 95, 205) : (isHovered ? Color.FromArgb(60, 145, 255) : Color.FromArgb(47, 127, 245));
                    Color cBottom = isPressed ? Color.FromArgb(15, 80, 180) : (isHovered ? Color.FromArgb(35, 115, 235) : Color.FromArgb(25, 105, 225));
                    using (var brush = new LinearGradientBrush(rect, cTop, cBottom, 90F))
                        e.Graphics.FillPath(brush, path);

                    if (!isPressed)
                    {
                        using (var pen = new Pen(Color.FromArgb(120, 255, 255, 255), 1.2F))
                            e.Graphics.DrawPath(pen, path);
                    }
                    TextRenderer.DrawText(e.Graphics, Text, Font, rect, Color.White, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
                }
                else
                {
                    Color cTop = isPressed ? Color.FromArgb(218, 228, 238) : (isHovered ? Color.FromArgb(250, 252, 255) : Color.FromArgb(240, 246, 251));
                    Color cBottom = isPressed ? Color.FromArgb(210, 220, 230) : (isHovered ? Color.FromArgb(232, 240, 248) : Color.FromArgb(224, 234, 242));
                    using (var brush = new LinearGradientBrush(rect, cTop, cBottom, 90F))
                        e.Graphics.FillPath(brush, path);

                    using (var pen = new Pen(isPressed ? Color.FromArgb(180, 195, 210) : Color.FromArgb(255, 255, 255), 1.2F))
                        e.Graphics.DrawPath(pen, path);

                    Color textColor = isHovered ? Color.FromArgb(16, 43, 69) : Color.FromArgb(60, 85, 110);
                    TextRenderer.DrawText(e.Graphics, Text, Font, rect, textColor, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
                }
            }
        }
    }

    // ==========================================
    // 沉浸式窗口顶栏与控制按钮 (CustomTitleBar)
    // ==========================================
    internal class CustomTitleBar : Panel
    {
        private Label lblTitle;
        private Label lblBadge;
        private NeoWindowButton btnMin;
        private NeoWindowButton btnClose;
        private Form parentForm;

        public CustomTitleBar(Form form, string titleText)
        {
            parentForm = form;
            Height = 42;
            Dock = DockStyle.Top;
            BackColor = Color.FromArgb(223, 234, 242);
            Padding = new Padding(16, 6, 16, 6);

            var picIcon = new PictureBox
            {
                Size = new Size(18, 18),
                Location = new Point(18, 12),
                SizeMode = PictureBoxSizeMode.StretchImage
            };
            if (File.Exists(Program.IconPath))
            {
                try { picIcon.Image = Image.FromFile(Program.IconPath); } catch { }
            }

            lblTitle = new Label
            {
                Text = titleText,
                AutoSize = true,
                Location = new Point(42, 11),
                Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold),
                ForeColor = Color.FromArgb(16, 43, 69)
            };

            lblBadge = new Label
            {
                Text = "独立隔离通道 17897",
                AutoSize = true,
                Location = new Point(195, 11),
                Font = new Font("Microsoft YaHei UI", 8F, FontStyle.Bold),
                ForeColor = Color.FromArgb(47, 127, 245),
                BackColor = Color.FromArgb(214, 231, 248),
                Padding = new Padding(6, 2, 6, 2)
            };

            btnMin = new NeoWindowButton("─", false)
            {
                Size = new Size(28, 28)
            };
            btnMin.Click += delegate { parentForm.WindowState = FormWindowState.Minimized; };

            btnClose = new NeoWindowButton("✕", true)
            {
                Size = new Size(28, 28)
            };
            btnClose.Click += delegate { parentForm.Hide(); };

            Controls.AddRange(new Control[] { picIcon, lblTitle, lblBadge, btnMin, btnClose });

            MouseDown += OnTitleMouseDown;
            lblTitle.MouseDown += OnTitleMouseDown;
            lblBadge.MouseDown += OnTitleMouseDown;
            picIcon.MouseDown += OnTitleMouseDown;

            UpdateButtonsPosition();
        }

        protected override void OnResize(EventArgs eventargs)
        {
            base.OnResize(eventargs);
            UpdateButtonsPosition();
        }

        private void UpdateButtonsPosition()
        {
            if (btnClose != null) btnClose.Location = new Point(Width - 42, 7);
            if (btnMin != null) btnMin.Location = new Point(Width - 76, 7);
        }

        private void OnTitleMouseDown(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                Program.ReleaseCapture();
                Program.SendMessage(parentForm.Handle, 0xA1, 0x2, 0);
            }
        }
    }

    internal class NeoWindowButton : Control
    {
        private string text;
        private bool isClose;
        private bool isHovered;

        public NeoWindowButton(string text, bool isClose)
        {
            this.text = text;
            this.isClose = isClose;
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint, true);
            Cursor = Cursors.Hand;
        }

        protected override void OnMouseEnter(EventArgs e) { isHovered = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { isHovered = false; Invalidate(); base.OnMouseLeave(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var rect = new Rectangle(1, 1, Width - 3, Height - 3);
            using (var path = GlassPanel.RoundedRectangle(rect, 8))
            {
                if (isHovered)
                {
                    Color bg = isClose ? Color.FromArgb(254, 226, 226) : Color.FromArgb(235, 244, 252);
                    using (var b = new SolidBrush(bg)) e.Graphics.FillPath(b, path);
                }
                Color tc = isHovered && isClose ? Color.FromArgb(220, 38, 38) : Color.FromArgb(97, 122, 145);
                TextRenderer.DrawText(e.Graphics, text, new Font("Segoe UI", 9F, FontStyle.Bold), rect, tc, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
            }
        }
    }

    // ==========================================
    // 进度条渲染组件
    // ==========================================
    internal sealed class StatusProgress : Control
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

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var track = new Rectangle(0, 2, Width - 1, Height - 5);
            using (var trackPath = GlassPanel.RoundedRectangle(track, 9))
            using (var trackBrush = new SolidBrush(Color.FromArgb(214, 224, 237)))
            {
                e.Graphics.FillPath(trackBrush, trackPath);
            }

            int fillWidth = Math.Max(18, (int)Math.Round(track.Width * currentValue / 100.0));
            var fill = new Rectangle(track.Left, track.Top, Math.Min(track.Width, fillWidth), track.Height);
            using (var fillPath = GlassPanel.RoundedRectangle(fill, 9))
            using (var fillBrush = new LinearGradientBrush(fill, Color.FromArgb(96, 165, 250), Color.FromArgb(37, 99, 235), 0F))
            {
                e.Graphics.FillPath(fillBrush, fillPath);
            }

            string percent = currentValue.ToString() + "%";
            SizeF textSize = e.Graphics.MeasureString(percent, Font);
            using (var textBrush = new SolidBrush(currentValue > 88 ? Color.White : Color.FromArgb(30, 64, 175)))
            {
                e.Graphics.DrawString(percent, Font, textBrush, Width - textSize.Width - 8, (Height - textSize.Height) / 2F);
            }
        }
    }

    // ==========================================
    // 常驻应用程序上下文 (系统托盘与控制中心枢纽)
    // ==========================================
    internal class LauncherAppContext : ApplicationContext
    {
        internal static LauncherAppContext CurrentContext { get; private set; }

        private NotifyIcon notifyIcon;
        private ContextMenuStrip contextMenu;
        private System.Windows.Forms.Timer pollTimer;
        private NodeControlForm controlForm;
        private SynchronizationContext uiContext;
        private Icon appIcon;

        private int currentLat = 9999;
        private string currentEgress = "US";
        private string currentServer = "";
        private string currentNodeName = "检测中…";
        private int notRunningCount = 0;

        public LauncherAppContext(bool showControlCenterOnStartup = false)
        {
            CurrentContext = this;
            uiContext = SynchronizationContext.Current ?? new WindowsFormsSynchronizationContext();
            LoadAppIcon();
            InitializeTray();
            UpdateStatus();

            pollTimer = new System.Windows.Forms.Timer { Interval = 15000 };
            pollTimer.Tick += delegate { OnTimerTick(); };
            pollTimer.Start();

            if (showControlCenterOnStartup)
            {
                ShowControlCenter();
            }
        }

        private void LoadAppIcon()
        {
            try
            {
                if (File.Exists(Program.IconPath))
                {
                    appIcon = new Icon(Program.IconPath);
                }
            }
            catch { }
        }

        private void InitializeTray()
        {
            contextMenu = new ContextMenuStrip();
            contextMenu.Font = new Font("Microsoft YaHei UI", 9F);

            var titleItem = new ToolStripMenuItem("🚀 Antigravity 智能启动器") { Enabled = false, Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold) };
            var latItem = new ToolStripMenuItem("⚡ 实时延迟: 检测中…") { Enabled = false };
            var egressItem = new ToolStripMenuItem("🌐 当前出口: 检测中…") { Enabled = false };

            var openItem = new ToolStripMenuItem("🖥 打开节点控制中心 (测速 / 切换)") { Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold) };
            openItem.Click += delegate { ShowControlCenter(); };

            var switchCodeItem = new ToolStripMenuItem("👉 切换至 Antigravity 代码窗口");
            switchCodeItem.Click += delegate { Program.ActivateExistingAntigravity(); };

            var refreshItem = new ToolStripMenuItem("🔄 刷新状态与延迟");
            refreshItem.Click += delegate { UpdateStatus(); };

            var rehealItem = new ToolStripMenuItem("🛡️ 强制重新自愈检测…");
            rehealItem.Click += delegate { TriggerRehealWorkflow(); };

            var exitItem = new ToolStripMenuItem("❌ 退出启动器与托盘");
            exitItem.Click += delegate { ExitApp(); };

            contextMenu.Items.Add(titleItem);
            contextMenu.Items.Add(latItem);
            contextMenu.Items.Add(egressItem);
            contextMenu.Items.Add(new ToolStripSeparator());
            contextMenu.Items.Add(openItem);
            contextMenu.Items.Add(switchCodeItem);
            contextMenu.Items.Add(refreshItem);
            contextMenu.Items.Add(rehealItem);
            contextMenu.Items.Add(new ToolStripSeparator());
            contextMenu.Items.Add(exitItem);

            notifyIcon = new NotifyIcon
            {
                Text = "Antigravity 智能启动器",
                ContextMenuStrip = contextMenu,
                Icon = appIcon ?? SystemIcons.Application,
                Visible = true
            };
            notifyIcon.DoubleClick += delegate { ShowControlCenter(); };
            notifyIcon.Click += delegate { ShowControlCenter(); };
        }

        private void OnTimerTick()
        {
            if (!Program.IsAntigravityRunning())
            {
                notRunningCount++;
                if (notRunningCount >= 8) // 120 秒无 Antigravity 则自动退出托盘
                {
                    ExitApp();
                    return;
                }
            }
            else
            {
                notRunningCount = 0;
            }

            UpdateStatus();
        }

        internal void PostShowControlCenter()
        {
            if (uiContext != null)
            {
                uiContext.Post(delegate { ShowControlCenter(); }, null);
            }
        }

        public void ShowControlCenter()
        {
            Program.TraceLog("ShowControlCenter entered");
            if (controlForm == null || controlForm.IsDisposed)
            {
                Program.TraceLog("Creating NodeControlForm...");
                controlForm = new NodeControlForm(this);
                Program.TraceLog("NodeControlForm created successfully");
            }

            if (!controlForm.Visible)
            {
                Program.TraceLog("Calling controlForm.Show()...");
                controlForm.Show();
                Program.TraceLog("controlForm.Show() returned");
            }
            if (controlForm.WindowState == FormWindowState.Minimized)
            {
                controlForm.WindowState = FormWindowState.Normal;
            }

            Program.ForceForeground(controlForm.Handle);
            Program.TraceLog("ShowControlCenter completed");
        }

        public void UpdateStatus()
        {
            Task.Run(delegate
            {
                try
                {
                    string proxyRoot = Program.RuntimeDirectory;
                    string configFile = Path.Combine(proxyRoot, "mihomo-antigravity.yaml");
                    string stateFile = Program.SupervisorStatePath;
                    string prefFile = Path.Combine(proxyRoot, "user-preferred-node.json");

                    string server = "";
                    int port = 0;
                    string nodeName = "";
                    if (File.Exists(configFile))
                    {
                        string txt = File.ReadAllText(configFile, Encoding.UTF8);
                        var m = Regex.Match(txt, @"server:\s*([^\s,]+),\s*port:\s*(\d+)");
                        if (m.Success)
                        {
                            server = m.Groups[1].Value;
                            int.TryParse(m.Groups[2].Value, out port);
                        }
                    }

                    if (File.Exists(prefFile))
                    {
                        try
                        {
                            string prefTxt = File.ReadAllText(prefFile, Encoding.UTF8);
                            var mName = Regex.Match(prefTxt, @"""name""\s*:\s*""([^""]+)""");
                            var mSrv = Regex.Match(prefTxt, @"""server""\s*:\s*""([^""]+)""");
                            var mP = Regex.Match(prefTxt, @"""port""\s*:\s*(\d+)");
                            if (mName.Success && mSrv.Success && mP.Success)
                            {
                                int pP;
                                if (int.TryParse(mP.Groups[1].Value, out pP) && mSrv.Groups[1].Value == server && pP == port)
                                {
                                    nodeName = mName.Groups[1].Value;
                                }
                            }
                        }
                        catch { }
                    }

                    if (string.IsNullOrEmpty(nodeName) && controlForm != null)
                    {
                        nodeName = controlForm.GetActiveNodeDisplayName();
                    }

                    int lat = 9999;
                    if (!string.IsNullOrEmpty(server) && port > 0)
                    {
                        var sw = Stopwatch.StartNew();
                        try
                        {
                            using (var tcp = new TcpClient())
                            {
                                var ar = tcp.BeginConnect(server, port, null, null);
                                if (ar.AsyncWaitHandle.WaitOne(1500))
                                {
                                    tcp.EndConnect(ar);
                                    sw.Stop();
                                    lat = (int)sw.ElapsedMilliseconds;
                                }
                            }
                        }
                        catch { }
                    }

                    string country = "US";
                    if (File.Exists(stateFile))
                    {
                        string stateTxt = File.ReadAllText(stateFile, Encoding.UTF8);
                        var m = Regex.Match(stateTxt, @"""egress_country""\s*:\s*""([^""]+)""");
                        if (m.Success) country = m.Groups[1].Value;
                    }

                    currentLat = lat;
                    currentEgress = country;
                    currentServer = string.IsNullOrEmpty(server) ? "" : (server + ":" + port);
                    currentNodeName = string.IsNullOrEmpty(nodeName) ? (currentEgress + " 专线 (" + currentServer + ")") : nodeName;

                    UpdateTrayUi(currentLat, currentEgress, currentServer, currentNodeName);
                }
                catch { }
            });
        }

        private void UpdateTrayUi(int lat, string egress, string server, string nodeName)
        {
            if (contextMenu.InvokeRequired)
            {
                contextMenu.BeginInvoke(new Action(delegate { UpdateTrayUi(lat, egress, server, nodeName); }));
                return;
            }

            string latStr = lat < 9000 ? (lat + "ms") : "检测中";
            contextMenu.Items[1].Text = "⚡ 实时延迟: " + latStr + " [" + egress + "]";
            contextMenu.Items[2].Text = "🌐 当前出口: " + (string.IsNullOrEmpty(server) ? "未连接" : server);

            string title = "Antigravity 启动器: [" + egress + "] " + latStr + "\n节点: " + nodeName;
            if (title.Length > 63) title = title.Substring(0, 63);
            notifyIcon.Text = title;

            if (controlForm != null && !controlForm.IsDisposed && controlForm.Visible)
            {
                controlForm.UpdateCurrentActiveView(nodeName, egress, server, lat);
            }
        }

        internal void TriggerRehealWorkflow()
        {
            var res = MessageBox.Show(
                "是否确定要对 Antigravity 独立代理执行强制重新自愈检测？\n\n这会重新扫描所有候选节点、运行 Google 握手并验证真实模型通过。",
                "确认重新自愈",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question
            );
            if (res != DialogResult.Yes) return;

            if (controlForm != null && !controlForm.IsDisposed)
            {
                controlForm.Hide();
            }

            var recoveryForm = new RecoveryLauncherForm("ManualTrigger");
            recoveryForm.ShowDialog();
            UpdateStatus();
        }

        public void ExitApp()
        {
            if (pollTimer != null) pollTimer.Stop();
            if (notifyIcon != null)
            {
                notifyIcon.Visible = false;
                notifyIcon.Dispose();
            }
            if (controlForm != null && !controlForm.IsDisposed)
            {
                controlForm.Dispose();
            }
            Application.Exit();
        }
    }

    // ==========================================
    // 核心窗体：克制玻璃与拟态节点中控台 (Control Center)
    // ==========================================
    internal class NodeControlForm : Form
    {
        private LauncherAppContext appContext;
        private Label lblActiveTitle;
        private Label lblActiveLatency;
        private Label lblActiveDetails;
        private Label lblActiveSecurity;
        private Label lblTunnelBadge;
        private Label lblFeedback;
        private ListView listNodes;
        private NeoButton btnTestAll;
        private NeoButton btnApplySelected;
        private NeoButton btnSwitchCode;
        private NeoButton btnReheal;
        private FlowLayoutPanel filterPanel;
        private List<NeoButton> filterPillButtons = new List<NeoButton>();
        private string currentRegionFilter = "全部";

        private List<NodeItem> allNodes = new List<NodeItem>();
        private string currentConnectedServer = "";
        private int currentConnectedPort = 0;
        private string currentNodeName = "";
        private string currentEgressCountry = "";
        private bool switchInProgress = false;

        public NodeControlForm(LauncherAppContext context)
        {
            appContext = context;
            InitializeComponent();
            LoadAppIcon();
            LoadNodesAndState();
        }

        private void LoadAppIcon()
        {
            try
            {
                if (File.Exists(Program.IconPath))
                {
                    Icon = new Icon(Program.IconPath);
                }
            }
            catch { }
        }

        private void InitializeComponent()
        {
            Text = "Antigravity 启动与节点控制中心";
            FormBorderStyle = FormBorderStyle.None;
            ClientSize = new Size(960, 680);
            MinimumSize = new Size(860, 600);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Microsoft YaHei UI", 9F);
            BackColor = Color.FromArgb(223, 234, 242);
            DoubleBuffered = true;
            ShowInTaskbar = true;

            // 关闭按钮行为：安静缩回托盘，不打断用户工作
            FormClosing += delegate(object s, FormClosingEventArgs e)
            {
                if (e.CloseReason == CloseReason.UserClosing)
                {
                    e.Cancel = true;
                    Hide();
                }
            };

            // 1. 沉浸式自定义窗口标题栏 (含无边框平滑拖动)
            var titleBar = new CustomTitleBar(this, "Antigravity 控制中心");

            // 2. 顶部状态卡片 (NeoCardPanel)
            var topPanel = new Panel
            {
                Dock = DockStyle.Top,
                Height = 160,
                BackColor = Color.Transparent,
                Padding = new Padding(18, 8, 18, 6)
            };

            var glassCard = new NeoCardPanel
            {
                Dock = DockStyle.Fill,
                CornerRadius = 18,
                Padding = new Padding(20, 12, 20, 12)
            };

            lblTunnelBadge = new Label
            {
                Text = "🟢 专属通道 127.0.0.1:17897 · 正常运行",
                Left = 20,
                Top = 14,
                AutoSize = true,
                Height = 22,
                TextAlign = ContentAlignment.MiddleLeft,
                BackColor = Color.FromArgb(209, 250, 229),
                ForeColor = Color.FromArgb(6, 95, 70),
                Font = new Font("Microsoft YaHei UI", 8.5F, FontStyle.Bold),
                Padding = new Padding(8, 2, 8, 2)
            };

            lblActiveTitle = new Label
            {
                Text = "当前连接：正在检测当前节点…",
                AutoSize = false,
                Left = 20,
                Top = 42,
                Width = 550,
                Height = 28,
                Font = new Font("Microsoft YaHei UI", 13.5F, FontStyle.Bold),
                ForeColor = Color.FromArgb(16, 43, 69)
            };

            lblActiveLatency = new Label
            {
                Text = "⚡ 实时延迟: -- ms",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 11.5F, FontStyle.Bold),
                ForeColor = Color.FromArgb(21, 128, 61),
                Left = 22,
                Top = 73
            };

            lblActiveDetails = new Label
            {
                Text = "出口地区：-- ｜ 专属独立通道 17897（与系统 Clash 互不干扰）",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 9F),
                ForeColor = Color.FromArgb(97, 122, 145),
                Left = 22,
                Top = 100
            };

            lblActiveSecurity = new Label
            {
                Text = "✔ Google 账号与 AI 编程模型已全部通畅",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold),
                ForeColor = Color.FromArgb(21, 128, 61),
                Left = 22,
                Top = 122
            };

            // 右侧辅助功能按钮 (自绘拟态次级按钮，尺寸匀称，不抢占视觉焦点)
            btnSwitchCode = new NeoButton
            {
                Text = "🚀 呼出代码窗口",
                Left = 760,
                Top = 38,
                Size = new Size(140, 34),
                CornerRadius = 10,
                IsPrimary = false
            };
            btnSwitchCode.Click += delegate
            {
                bool ok = Program.ActivateExistingAntigravity();
                if (ok)
                {
                    lblFeedback.Text = "✅ 已将 Antigravity 代码窗口置于最前台！";
                    lblFeedback.ForeColor = Color.FromArgb(21, 128, 61);
                }
                else
                {
                    lblFeedback.Text = "⚠️ 未找到运行中的 Antigravity 窗口。";
                    lblFeedback.ForeColor = Color.FromArgb(220, 38, 38);
                }
            };

            btnReheal = new NeoButton
            {
                Text = "🔄 异常诊断自愈",
                Left = 760,
                Top = 82,
                Size = new Size(140, 34),
                CornerRadius = 10,
                IsPrimary = false
            };
            btnReheal.Click += delegate
            {
                appContext.TriggerRehealWorkflow();
            };

            glassCard.Resize += delegate
            {
                btnSwitchCode.Left = glassCard.ClientSize.Width - 160;
                btnReheal.Left = glassCard.ClientSize.Width - 160;
            };

            glassCard.Controls.AddRange(new Control[] { lblTunnelBadge, lblActiveTitle, lblActiveLatency, lblActiveDetails, lblActiveSecurity, btnSwitchCode, btnReheal });
            topPanel.Controls.Add(glassCard);

            // 3. 地区筛选栏 (真拟态胶囊分段药丸)
            filterPanel = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 44,
                BackColor = Color.FromArgb(223, 234, 242),
                Padding = new Padding(18, 6, 18, 6)
            };

            string[] regions = new string[] { "全部专线", "美国专线", "日本专线" };
            filterPillButtons.Clear();
            foreach (var r in regions)
            {
                string tag = r.Contains("美国") ? "美国" : (r.Contains("日本") ? "日本" : "全部");
                var btnPill = new NeoButton
                {
                    Text = r,
                    Size = new Size(96, 32),
                    IsPill = true,
                    Margin = new Padding(0, 0, 10, 0),
                    Tag = tag,
                    IsPrimary = (tag == "全部")
                };
                filterPillButtons.Add(btnPill);
                btnPill.Click += delegate
                {
                    currentRegionFilter = tag;
                    foreach (var b in filterPillButtons)
                    {
                        b.IsPrimary = (b.Tag.ToString() == currentRegionFilter);
                        b.Invalidate();
                    }
                    FilterListView();
                };
                filterPanel.Controls.Add(btnPill);
            }

            // 4. 底部操作栏 (主次分明：单一主按钮 + 测速辅助 + 直觉化引导)
            var bottomPanel = new Panel
            {
                Dock = DockStyle.Bottom,
                Height = 64,
                BackColor = Color.FromArgb(223, 234, 242),
                Padding = new Padding(18, 12, 18, 12)
            };

            btnTestAll = new NeoButton
            {
                Text = "⚡ 重新测速",
                Size = new Size(115, 40),
                Left = 20,
                Top = 12,
                CornerRadius = 12,
                IsPrimary = false
            };
            btnTestAll.Click += delegate { StartSpeedTest(); };

            btnApplySelected = new NeoButton
            {
                Text = "立即切换专线",
                Size = new Size(160, 40),
                Left = 145,
                Top = 12,
                CornerRadius = 12,
                IsPrimary = false,
                Enabled = false
            };
            btnApplySelected.Click += delegate { SwitchSelectedNode(); };

            lblFeedback = new Label
            {
                Text = "💡 提示：双击列表中任意专线即可直接切换",
                AutoSize = true,
                ForeColor = Color.FromArgb(97, 122, 145),
                Font = new Font("Microsoft YaHei UI", 9F),
                Left = 320,
                Top = 22
            };

            bottomPanel.Controls.AddRange(new Control[] { btnTestAll, btnApplySelected, lblFeedback });

            // 5. 节点列表卡片 (NeoCardPanel 嵌套 OwnerDraw ListView)
            listNodes = new ListView
            {
                Dock = DockStyle.Fill,
                View = View.Details,
                FullRowSelect = true,
                GridLines = false,
                HideSelection = false,
                MultiSelect = false,
                HeaderStyle = ColumnHeaderStyle.Nonclickable,
                Font = new Font("Microsoft YaHei UI", 9.5F),
                BorderStyle = BorderStyle.None,
                BackColor = Color.FromArgb(242, 247, 251),
                OwnerDraw = true
            };

            var imgList = new ImageList();
            imgList.ImageSize = new Size(1, 34); // 撑开行距至 34px 舒适阅读高度
            listNodes.SmallImageList = imgList;

            listNodes.Columns.Add("地区", 100);
            listNodes.Columns.Add("专线名称", 480);
            listNodes.Columns.Add("实时延迟", 110);
            listNodes.Columns.Add("状态", 140);
            listNodes.SelectedIndexChanged += delegate { UpdateSelectedAction(); };
            listNodes.DoubleClick += delegate { SwitchSelectedNode(); };

            listNodes.DrawColumnHeader += delegate(object s, DrawListViewColumnHeaderEventArgs e)
            {
                e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
                using (var b = new SolidBrush(Color.FromArgb(226, 237, 246)))
                    e.Graphics.FillRectangle(b, e.Bounds);
                using (var linePen = new Pen(Color.FromArgb(205, 220, 232), 1F))
                    e.Graphics.DrawLine(linePen, e.Bounds.Left, e.Bounds.Bottom - 1, e.Bounds.Right, e.Bounds.Bottom - 1);
                TextRenderer.DrawText(e.Graphics, e.Header.Text, new Font("Microsoft YaHei UI", 9F, FontStyle.Bold), e.Bounds, Color.FromArgb(71, 85, 105), TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.LeftAndRightPadding);
            };

            listNodes.DrawSubItem += delegate(object s, DrawListViewSubItemEventArgs e)
            {
                var item = e.Item;
                var node = item.Tag as NodeItem;
                bool isSelected = item.Selected;
                bool isCurrent = node != null && node.IsCurrent;

                Color bg = isCurrent ? Color.FromArgb(234, 247, 238) : (isSelected ? Color.FromArgb(218, 235, 248) : (e.ItemIndex % 2 == 0 ? Color.FromArgb(248, 251, 254) : Color.FromArgb(240, 246, 251)));
                using (var b = new SolidBrush(bg))
                    e.Graphics.FillRectangle(b, e.Bounds);

                if (isSelected && e.ColumnIndex == 0)
                {
                    using (var b = new SolidBrush(Color.FromArgb(47, 127, 245)))
                        e.Graphics.FillRectangle(b, e.Bounds.Left, e.Bounds.Top + 2, 3, e.Bounds.Height - 4);
                }

                Rectangle textRect = new Rectangle(e.Bounds.Left + 8, e.Bounds.Top, e.Bounds.Width - 14, e.Bounds.Height);

                if (e.ColumnIndex == 0)
                {
                    Color tc = isCurrent ? Color.FromArgb(21, 128, 61) : Color.FromArgb(51, 65, 85);
                    TextRenderer.DrawText(e.Graphics, e.SubItem.Text, new Font("Microsoft YaHei UI", 9F, FontStyle.Bold), textRect, tc, TextFormatFlags.Left | TextFormatFlags.VerticalCenter);
                }
                else if (e.ColumnIndex == 1)
                {
                    Color tc = isCurrent ? Color.FromArgb(21, 128, 61) : Color.FromArgb(30, 41, 59);
                    FontStyle fs = isCurrent ? FontStyle.Bold : FontStyle.Regular;
                    TextRenderer.DrawText(e.Graphics, e.SubItem.Text, new Font("Microsoft YaHei UI", 9.5F, fs), textRect, tc, TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis);
                }
                else if (e.ColumnIndex == 2)
                {
                    Color latColor = Color.FromArgb(140, 155, 170);
                    if (node != null && node.Latency < 9000)
                    {
                        if (node.Latency < 200) latColor = Color.FromArgb(22, 163, 74);
                        else if (node.Latency < 500) latColor = Color.FromArgb(217, 119, 6);
                        else latColor = Color.FromArgb(220, 38, 38);
                    }
                    TextRenderer.DrawText(e.Graphics, e.SubItem.Text, new Font("Microsoft YaHei UI", 9F, FontStyle.Bold), textRect, latColor, TextFormatFlags.Left | TextFormatFlags.VerticalCenter);
                }
                else if (e.ColumnIndex == 3)
                {
                    if (isCurrent)
                    {
                        var badgeRect = new Rectangle(textRect.Left, textRect.Top + (textRect.Height - 22) / 2, 84, 22);
                        using (var p = GlassPanel.RoundedRectangle(badgeRect, 11))
                        using (var bb = new SolidBrush(Color.FromArgb(209, 250, 229)))
                        using (var border = new Pen(Color.FromArgb(110, 231, 183), 1F))
                        {
                            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
                            e.Graphics.FillPath(bb, p);
                            e.Graphics.DrawPath(border, p);
                        }
                        TextRenderer.DrawText(e.Graphics, "🟢 当前在用", new Font("Microsoft YaHei UI", 8F, FontStyle.Bold), badgeRect, Color.FromArgb(6, 95, 70), TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
                    }
                    else
                    {
                        Color tc = Color.FromArgb(100, 116, 139);
                        if (node != null && node.Latency < 200) tc = Color.FromArgb(22, 163, 74);
                        else if (node != null && node.Latency < 500) tc = Color.FromArgb(217, 119, 6);
                        TextRenderer.DrawText(e.Graphics, e.SubItem.Text, new Font("Microsoft YaHei UI", 8.5F), textRect, tc, TextFormatFlags.Left | TextFormatFlags.VerticalCenter);
                    }
                }
            };

            var listGlassCard = new NeoCardPanel
            {
                Dock = DockStyle.Fill,
                CornerRadius = 16,
                Padding = new Padding(2, 2, 2, 2)
            };
            listGlassCard.Controls.Add(listNodes);

            var listContainer = new Panel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(18, 2, 18, 6),
                BackColor = Color.FromArgb(223, 234, 242)
            };
            listContainer.Controls.Add(listGlassCard);

            Controls.Add(listContainer);
            Controls.Add(filterPanel);
            Controls.Add(bottomPanel);
            Controls.Add(topPanel);
            Controls.Add(titleBar);
        }

        protected override void OnResize(EventArgs e)
        {
            base.OnResize(e);
            if (Width > 0 && Height > 0)
            {
                this.Region = new Region(GlassPanel.RoundedRectangle(new Rectangle(0, 0, Width, Height), 20));
                Invalidate();
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            using (var path = GlassPanel.RoundedRectangle(new Rectangle(0, 0, Width - 1, Height - 1), 20))
            using (var borderPen = new Pen(Color.FromArgb(165, 192, 216), 1.5F))
            {
                e.Graphics.DrawPath(borderPen, path);
            }
        }

        internal static string CleanNodeName(string rawName)
        {
            if (string.IsNullOrWhiteSpace(rawName)) return "";
            string s = rawName.Trim();
            s = Regex.Replace(s, @"[\uD800-\uDBFF][\uDC00-\uDFFF]", "");
            s = Regex.Replace(s, @"^(?:US|JP|us|jp)\b[\s\-_|]*", "", RegexOptions.IgnoreCase);
            s = Regex.Replace(s, @"^(?:US|JP|us|jp)\s*(?:美国|日本)", "$1", RegexOptions.IgnoreCase);
            s = Regex.Replace(s, @"^(美国|日本)[\s\-_|]*(?:美国|日本)", "$1");
            return s.Trim(' ', '-', '|', ':', '_');
        }

        public string GetActiveNodeDisplayName()
        {
            foreach (var n in allNodes)
            {
                if (n.IsCurrent) return n.DisplayName;
            }
            return "";
        }

        public void UpdateCurrentActiveView(string name, string egress, string server, int lat)
        {
            string clean = CleanNodeName(name);
            string safeName = string.IsNullOrWhiteSpace(clean) ? "当前链路待确认" : clean;
            string country = string.IsNullOrWhiteSpace(egress) ? "--" : egress;
            lblActiveTitle.Text = "当前专线：" + safeName;
            string latStr = lat < 9000 ? (lat + " ms") : "检测中";
            lblActiveLatency.Text = "⚡ 实时延迟: " + latStr + (lat < 200 ? " · 极速" : (lat < 500 ? " · 良好" : ""));
            lblActiveLatency.ForeColor = (lat < 200) ? Color.FromArgb(22, 163, 74) : ((lat < 500) ? Color.FromArgb(217, 119, 6) : Color.FromArgb(220, 38, 38));
            lblActiveDetails.Text = "出口地区：[" + country + "] ｜ 专属独立通道 17897（与系统 Clash 互不干扰）";
        }

        private void LoadNodesAndState()
        {
            Task.Run(delegate
            {
                ReadCurrentProxyConfig();
                var nodes = DiscoverySubscriptionNodes();
                allNodes = nodes;

                NodeItem activeNode = null;
                foreach (var n in allNodes)
                {
                    if (n.IsCurrent) { activeNode = n; break; }
                }

                BeginInvoke(new Action(delegate
                {
                    if (activeNode != null)
                    {
                        currentNodeName = activeNode.Name;
                        UpdateCurrentActiveView(activeNode.DisplayName, currentEgressCountry, activeNode.Server, activeNode.Latency);
                    }
                    else if (!string.IsNullOrEmpty(currentNodeName))
                    {
                        UpdateCurrentActiveView(currentNodeName, currentEgressCountry, "", 9999);
                    }
                    UpdateGateStatus();
                    FilterListView();
                    StartSpeedTest();
                }));
            });
        }

        private void ReadCurrentProxyConfig()
        {
            try
            {
                string stateFile = Program.SupervisorStatePath;
                if (File.Exists(stateFile))
                {
                    string stateText = File.ReadAllText(stateFile, Encoding.UTF8);
                    var nameMatch = Regex.Match(stateText, @"""target_node""\s*:\s*""([^""]+)""");
                    var countryMatch = Regex.Match(stateText, @"""egress_country""\s*:\s*""([^""]+)""");
                    if (nameMatch.Success) currentNodeName = Regex.Unescape(nameMatch.Groups[1].Value);
                    if (countryMatch.Success) currentEgressCountry = countryMatch.Groups[1].Value;
                }
                string proxyRoot = Program.RuntimeDirectory;
                string configFile = Path.Combine(proxyRoot, "mihomo-antigravity.yaml");
                if (File.Exists(configFile))
                {
                    string txt = File.ReadAllText(configFile, Encoding.UTF8);
                    var m = Regex.Match(txt, @"server:\s*([^\s,]+),\s*port:\s*(\d+)");
                    if (m.Success)
                    {
                        currentConnectedServer = m.Groups[1].Value;
                        int.TryParse(m.Groups[2].Value, out currentConnectedPort);
                    }
                }
            }
            catch { }
        }

        private List<NodeItem> DiscoverySubscriptionNodes()
        {
            var result = new List<NodeItem>();
            try
            {
                string clashProfilesDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), @"io.github.clash-verge-rev.clash-verge-rev\profiles");
                if (Directory.Exists(clashProfilesDir))
                {
                    foreach (var file in Directory.GetFiles(clashProfilesDir, "*.yaml"))
                    {
                        string subName = Path.GetFileNameWithoutExtension(file);
                        string[] lines = File.ReadAllLines(file, Encoding.UTF8);
                        bool inProxies = false;
                        foreach (var line in lines)
                        {
                            if (line.Trim().StartsWith("proxies:"))
                            {
                                inProxies = true;
                                continue;
                            }
                            if (inProxies && (line.StartsWith("proxy-groups:") || line.StartsWith("rules:")))
                            {
                                inProxies = false;
                                break;
                            }

                            if (inProxies && line.Contains("server:") && line.Contains("port:"))
                            {
                                var mName = Regex.Match(line, @"name:\s*([^,}]+)");
                                var mServer = Regex.Match(line, @"server:\s*([^,}]+)");
                                var mPort = Regex.Match(line, @"port:\s*(\d+)");
                                if (mServer.Success && mPort.Success)
                                {
                                    string name = mName.Success ? mName.Groups[1].Value.Trim('\'', '"', ' ') : "未知节点";
                                    string srv = mServer.Groups[1].Value.Trim('\'', '"', ' ');
                                    int port = int.Parse(mPort.Groups[1].Value);

                                    string country = "其他";
                                    if (Regex.IsMatch(name, @"日本|Japan|Tokyo|JP", RegexOptions.IgnoreCase)) { country = "日本"; }
                                    else if (Regex.IsMatch(name, @"美国|USA|United States|US", RegexOptions.IgnoreCase)) { country = "美国"; }
                                    if (country == "其他") continue;

                                    bool isCurrent = false;
                                    if (!string.IsNullOrEmpty(currentConnectedServer) && srv == currentConnectedServer && port == currentConnectedPort)
                                    {
                                        isCurrent = true;
                                    }
                                    else if (string.IsNullOrEmpty(currentConnectedServer) && !string.IsNullOrEmpty(currentNodeName) && string.Equals(name, currentNodeName, StringComparison.OrdinalIgnoreCase))
                                    {
                                        isCurrent = true;
                                    }

                                    string clean = CleanNodeName(name);
                                    string display = string.IsNullOrWhiteSpace(clean) ? name : clean;

                                    result.Add(new NodeItem
                                    {
                                        Name = name,
                                        DisplayName = display,
                                        Server = srv,
                                        Port = port,
                                        Country = country,
                                        Subscription = subName,
                                        RawLine = line.Trim().TrimStart('-').Trim(),
                                        Latency = isCurrent ? 160 : 9999,
                                        IsCurrent = isCurrent
                                    });
                                }
                            }
                        }
                    }
                }
            }
            catch { }
            return result;
        }

        private void FilterListView()
        {
            if (listNodes == null) return;
            string selectedKey = "";
            if (listNodes.SelectedItems.Count > 0)
            {
                var selected = listNodes.SelectedItems[0].Tag as NodeItem;
                if (selected != null) selectedKey = selected.Name + "|" + selected.Server + "|" + selected.Port;
            }
            listNodes.Items.Clear();
            var displayList = new List<NodeItem>(allNodes);
            displayList.Sort(delegate(NodeItem a, NodeItem b)
            {
                int latencyOrder = a.Latency.CompareTo(b.Latency);
                if (latencyOrder != 0) return latencyOrder;
                return string.Compare(a.DisplayName, b.DisplayName, StringComparison.CurrentCultureIgnoreCase);
            });

            foreach (var n in displayList)
            {
                if (currentRegionFilter != "全部" && n.Country != currentRegionFilter)
                    continue;

                string latStr = n.Latency < 9000 ? (n.Latency + " ms") : "--";
                string status = n.IsCurrent ? "当前在用" : (n.Latency < 200 ? "⚡ 极速" : (n.Latency < 500 ? "★ 良好" : (n.Latency < 9000 ? "延迟偏高" : "超时 / 未测")));

                var item = new ListViewItem(n.Country);
                item.SubItems.Add(n.DisplayName);
                item.SubItems.Add(latStr);
                item.SubItems.Add(status);
                item.Tag = n;

                listNodes.Items.Add(item);
                if ((n.Name + "|" + n.Server + "|" + n.Port) == selectedKey) item.Selected = true;
            }
            UpdateSelectedAction();
        }

        private void UpdateSelectedAction()
        {
            if (btnApplySelected == null) return;
            bool hasSelection = listNodes != null && listNodes.SelectedItems.Count == 1 && !switchInProgress;
            btnApplySelected.Enabled = hasSelection;
            btnApplySelected.IsPrimary = hasSelection;
            btnApplySelected.Invalidate();
            if (!hasSelection)
            {
                btnApplySelected.Text = switchInProgress ? "正在切换…" : "立即切换专线";
                return;
            }
            btnApplySelected.Text = "👉 立即切换专线";
        }

        private void UpdateGateStatus()
        {
            string state = "";
            try { if (File.Exists(Program.SupervisorStatePath)) state = File.ReadAllText(Program.SupervisorStatePath, Encoding.UTF8); } catch { }
            bool ready = Regex.IsMatch(state, @"""status""\s*:\s*""ready""", RegexOptions.IgnoreCase);
            bool modelPassed = Regex.IsMatch(state, @"""real_model_probe""\s*:\s*""passed""", RegexOptions.IgnoreCase);
            if (ready && modelPassed)
            {
                lblTunnelBadge.Text = "🟢 专属通道 127.0.0.1:17897 · 正常运行";
                lblTunnelBadge.ForeColor = Color.FromArgb(6, 95, 70);
                lblTunnelBadge.BackColor = Color.FromArgb(209, 250, 229);
                lblActiveSecurity.Text = "✔ Google 账号与 AI 编程模型已全部通畅";
                lblActiveSecurity.ForeColor = Color.FromArgb(21, 128, 61);
            }
            else
            {
                lblTunnelBadge.Text = "🟠 专属通道正在检测链路…";
                lblTunnelBadge.ForeColor = Color.FromArgb(146, 64, 14);
                lblTunnelBadge.BackColor = Color.FromArgb(254, 243, 199);
                lblActiveSecurity.Text = "正在验证真实模型门禁与链路完整性…";
                lblActiveSecurity.ForeColor = Color.FromArgb(180, 83, 9);
            }
        }

        private void StartSpeedTest()
        {
            btnTestAll.Enabled = false;
            btnTestAll.Text = "⚡ 测速中…";
            lblFeedback.Text = "⚡ 正在向所有候选专线并发发起高精度延迟探测…";

            Task.Run(delegate
            {
                var tasks = new List<Task>();
                foreach (var node in allNodes)
                {
                    var n = node;
                    tasks.Add(Task.Run(delegate
                    {
                        var sw = Stopwatch.StartNew();
                        try
                        {
                            using (var tcp = new TcpClient())
                            {
                                var ar = tcp.BeginConnect(n.Server, n.Port, null, null);
                                if (ar.AsyncWaitHandle.WaitOne(1200))
                                {
                                    tcp.EndConnect(ar);
                                    sw.Stop();
                                    n.Latency = (int)sw.ElapsedMilliseconds;
                                }
                                else
                                {
                                    n.Latency = 9999;
                                }
                            }
                        }
                        catch
                        {
                            n.Latency = 9999;
                        }
                    }));
                }
                Task.WaitAll(tasks.ToArray());

                allNodes.Sort(delegate(NodeItem a, NodeItem b) { return a.Latency.CompareTo(b.Latency); });

                NodeItem activeNode = null;
                foreach (var n in allNodes)
                {
                    if (n.IsCurrent) { activeNode = n; break; }
                }

                BeginInvoke(new Action(delegate
                {
                    FilterListView();
                    if (activeNode != null)
                    {
                        UpdateCurrentActiveView(activeNode.DisplayName, currentEgressCountry, "", activeNode.Latency);
                    }
                    btnTestAll.Enabled = true;
                    btnTestAll.Text = "⚡ 重新测速";
                    lblFeedback.Text = "✔ 已按延迟最优完成排序 · 共 " + allNodes.Count + " 条可用专线";
                }));
            });
        }

        private async void SwitchSelectedNode()
        {
            if (switchInProgress || listNodes.SelectedItems.Count == 0) return;

            var selectedNode = listNodes.SelectedItems[0].Tag as NodeItem;
            if (selectedNode == null) return;

            switchInProgress = true;
            UpdateSelectedAction();
            lblFeedback.Text = "正在验证并切换至 " + selectedNode.DisplayName + "…";
            lblFeedback.ForeColor = Color.FromArgb(47, 127, 245);
            bool ok = await Task.Run(delegate { return RunVerifiedSwitch(selectedNode); });
            switchInProgress = false;
            if (ok)
            {
                foreach (var n in allNodes) n.IsCurrent = (n == selectedNode);
                currentConnectedServer = selectedNode.Server;
                currentConnectedPort = selectedNode.Port;
                currentNodeName = selectedNode.Name;

                ReadCurrentProxyConfig();
                lblFeedback.Text = "✅ 真实模型验证通过，已安全切换至 " + selectedNode.DisplayName;
                lblFeedback.ForeColor = Color.FromArgb(21, 128, 61);

                UpdateCurrentActiveView(selectedNode.DisplayName, currentEgressCountry, "", selectedNode.Latency);
                UpdateGateStatus();
                FilterListView();
                appContext.UpdateStatus();
            }
            else
            {
                lblFeedback.Text = "未切换：该线路未通过完整真实模型门禁，原链路保持不变。";
                lblFeedback.ForeColor = Color.FromArgb(220, 38, 38);
                UpdateGateStatus();
                UpdateSelectedAction();
            }
        }

        private bool RunVerifiedSwitch(NodeItem node)
        {
            try
            {
                if (!File.Exists(Program.ScriptPath)) return false;
                string country = node.Country == "日本" ? "JP" : "US";
                var psi = new ProcessStartInfo
                {
                    FileName = @"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                    Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + Program.ScriptPath +
                        "\" -TargetNodeOverride \"" + EscapeCommandArgument(node.Name) + "\" -ExpectedEgressCountryOverride " + country + " -RecoveryReason Startup",
                    WorkingDirectory = Program.AppDirectory,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };
                using (var proc = Process.Start(psi))
                {
                    if (proc == null) return false;
                    proc.BeginOutputReadLine();
                    proc.BeginErrorReadLine();
                    proc.WaitForExit();
                    return proc.ExitCode == 0;
                }
            }
            catch (Exception ex)
            {
                Program.TraceLog("verified switch failed type=" + ex.GetType().Name);
                return false;
            }
        }

        private static string EscapeCommandArgument(string value)
        {
            return (value ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"");
        }
    }

    // ==========================================
    // 自愈与启动进度窗体 (RecoveryLauncherForm)
    // ==========================================
    internal class RecoveryLauncherForm : Form
    {
        internal int ExitCode { get; private set; }
        private string recoveryReason;
        private bool userCancelled = false;
        private bool allowClose = false;
        private Process supervisorProc = null;

        public RecoveryLauncherForm(string reason)
        {
            recoveryReason = reason;
            ExitCode = 0;
            InitializeComponent();
        }

        private static Label MakeStepLabel(string text, int top)
        {
            return new Label
            {
                Text = text,
                AutoSize = false,
                Left = 34,
                Top = top,
                Width = 540,
                Height = 25,
                Font = new Font("Microsoft YaHei UI", 9F),
                ForeColor = Color.FromArgb(55, 65, 81)
            };
        }

        private void InitializeComponent()
        {
            Text = "Antigravity 智能启动器";
            ClientSize = new Size(640, 430);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = true;
            StartPosition = FormStartPosition.CenterScreen;
            ShowInTaskbar = true;
            BackColor = Color.FromArgb(215, 229, 242);
            Font = new Font("Microsoft YaHei UI", 9F);

            if (File.Exists(Program.IconPath))
            {
                try { Icon = new Icon(Program.IconPath); } catch { }
            }

            // 允许用户随时点击右上角叉叉退出，绝不强制锁定！
            FormClosing += delegate(object sender, FormClosingEventArgs e)
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
            Controls.Add(card);

            Shown += delegate
            {
                Task.Run(delegate
                {
                    RunRecoveryTask(headline, proxyStep, nodeStep, verificationStep, localizationStep, launchStep, progress);
                });
            };
        }

        private void RunRecoveryTask(Label headline, Label proxyStep, Label nodeStep, Label verificationStep, Label localizationStep, Label launchStep, StatusProgress progress)
        {
            if (!File.Exists(Program.ScriptPath))
            {
                Invoke(new Action(delegate
                {
                    allowClose = true;
                    ExitCode = 2;
                    DialogResult = DialogResult.Abort;
                    Close();
                    MessageBox.Show("缺少 Antigravity 恢复脚本：\n" + Program.ScriptPath, "启动错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }));
                return;
            }

            long logStartOffset = GetLogLength();
            int displayedProgress = 1;
            int animationTick = 0;
            DateTime supervisorRequestedUtc = DateTime.UtcNow;

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
                    Invoke(new Action(delegate { allowClose = true; ExitCode = 3; DialogResult = DialogResult.Abort; Close(); }));
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
                    StatusView status = BuildStatus(ReadLogSince(logStartOffset));
                    animationTick++;
                    if (displayedProgress < status.Progress)
                    {
                        displayedProgress += Math.Max(1, (status.Progress - displayedProgress + 3) / 4);
                    }
                    else if (displayedProgress < status.Ceiling && animationTick % 2 == 0)
                    {
                        displayedProgress++;
                    }

                    int prog = displayedProgress;
                    BeginInvoke(new Action(delegate
                    {
                        headline.Text = status.Headline;
                        proxyStep.Text = status.Proxy;
                        nodeStep.Text = status.Nodes;
                        verificationStep.Text = status.Verification;
                        localizationStep.Text = status.Localization;
                        launchStep.Text = status.Launch;
                        progress.ProgressValue = prog;
                    }));

                    Thread.Sleep(250);
                }

                if (userCancelled) { ExitCode = 0; return; }
                process.WaitForExit();
                int result = process.ExitCode;
                string currentLog = ReadLogSince(logStartOffset);

                if (result == 4)
                {
                    Invoke(new Action(delegate
                    {
                        headline.Text = "已有后台恢复正在进行，正在接收结果…";
                        verificationStep.Text = "● 后台检查已占用恢复通道，等待它完成";
                        launchStep.Text = "● 等待后台恢复完成后接管 Antigravity";
                    }));
                    string concurrentLog;
                    bool joined = WaitForConcurrentRecovery(
                        supervisorRequestedUtc,
                        logStartOffset,
                        delegate(StatusView st)
                        {
                            BeginInvoke(new Action(delegate
                            {
                                headline.Text = st.Headline;
                                proxyStep.Text = st.Proxy;
                                nodeStep.Text = st.Nodes;
                                verificationStep.Text = st.Verification;
                                localizationStep.Text = st.Localization;
                                launchStep.Text = st.Launch;
                            }));
                        },
                        out concurrentLog);
                    currentLog = concurrentLog;
                    if (joined) result = 0;
                }

                if (result == 0)
                {
                    BeginInvoke(new Action(delegate
                    {
                        headline.Text = "中文翻译注入成功，Antigravity 已就绪";
                        progress.ProgressValue = 100;
                    }));
                    Thread.Sleep(1200);
                    Invoke(new Action(delegate
                    {
                        allowClose = true;
                        ExitCode = 0;
                        DialogResult = DialogResult.OK;
                        Close();
                    }));
                }
                else
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(Program.LauncherLogPath));
                    File.AppendAllText(Program.LauncherLogPath, DateTime.Now.ToString("o") + " exit=" + result + Environment.NewLine + output + Environment.NewLine + error + Environment.NewLine);
                    Invoke(new Action(delegate
                    {
                        allowClose = true;
                        ExitCode = result;
                        DialogResult = DialogResult.Abort;
                        Close();
                        MessageBox.Show(TranslateFailure(currentLog, error.ToString()), "Antigravity 启动未通过", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }));
                }
            }
        }

        private static bool IsSupervisorMutexAvailable()
        {
            bool createdNew;
            try
            {
                using (var mutex = new Mutex(false, Program.SupervisorMutexName, out createdNew))
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
                if (!File.Exists(Program.SupervisorStatePath)) return false;
                if (File.GetLastWriteTimeUtc(Program.SupervisorStatePath) < requestedUtc.AddSeconds(-2)) return false;
                string compact = File.ReadAllText(Program.SupervisorStatePath, Encoding.UTF8)
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

        private bool WaitForConcurrentRecovery(
            DateTime requestedUtc,
            long logStartOffset,
            Action<StatusView> updateStatus,
            out string concurrentLog)
        {
            DateTime deadline = DateTime.UtcNow.AddMinutes(20);
            concurrentLog = "";
            while (DateTime.UtcNow < deadline)
            {
                if (userCancelled) return false;
                concurrentLog = ReadLogSince(logStartOffset);
                if (updateStatus != null) updateStatus(BuildStatus(concurrentLog));
                if (HasFreshReadyState(requestedUtc)) return true;

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
                    int parsedIndex, parsedTotal;
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
                    int parsedIndex, parsedTotal;
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
    }

    internal sealed class StatusView
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

    internal class NodeItem
    {
        public string Name { get; set; }
        public string DisplayName { get; set; }
        public string Server { get; set; }
        public int Port { get; set; }
        public string Country { get; set; }
        public string Subscription { get; set; }
        public string RawLine { get; set; }
        public int Latency { get; set; }
        public bool IsCurrent { get; set; }
    }
}
