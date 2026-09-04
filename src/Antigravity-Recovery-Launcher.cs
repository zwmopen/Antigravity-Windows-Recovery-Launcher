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
    // 核心窗体：毛玻璃节点中控台 (Control Center)
    // ==========================================
    internal class NodeControlForm : Form
    {
        private LauncherAppContext appContext;
        private Label lblActiveTitle;
        private Label lblActiveLatency;
        private Label lblActiveDetails;
        private Label lblActiveSecurity;
        private Label lblFeedback;
        private ListView listNodes;
        private Button btnTestAll;
        private Button btnApplySelected;
        private Button btnSwitchCode;
        private Button btnReheal;
        private Button btnHideToTray;
        private FlowLayoutPanel filterPanel;
        private string currentRegionFilter = "全部";

        private List<NodeItem> allNodes = new List<NodeItem>();
        private string currentConnectedServer = "";
        private int currentConnectedPort = 0;

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
            Text = "Antigravity 智能启动器 · 控制中心";
            ClientSize = new Size(960, 680);
            MinimumSize = new Size(860, 600);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Microsoft YaHei UI", 9F);
            BackColor = Color.FromArgb(215, 229, 242);

            // 关闭按钮行为：安静缩回托盘，不打断用户工作
            FormClosing += delegate(object s, FormClosingEventArgs e)
            {
                if (e.CloseReason == CloseReason.UserClosing)
                {
                    e.Cancel = true;
                    Hide();
                }
            };

            // 1. 顶部毛玻璃大卡片 (展示当前在用专线与快速置顶按钮)
            var topPanel = new Panel
            {
                Dock = DockStyle.Top,
                Height = 175,
                BackColor = Color.FromArgb(215, 229, 242),
                Padding = new Padding(16, 12, 16, 6)
            };

            var glassCard = new GlassPanel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(22, 12, 22, 12)
            };

            var badge = new Label
            {
                Text = "🟢 状态正常 · 独立隧道 127.0.0.1:17897 守护中",
                Left = 20,
                Top = 14,
                Width = 360,
                Height = 24,
                TextAlign = ContentAlignment.MiddleLeft,
                BackColor = Color.FromArgb(220, 231, 245),
                ForeColor = Color.FromArgb(30, 82, 160),
                Font = new Font("Microsoft YaHei UI", 8.5F, FontStyle.Bold)
            };

            lblActiveTitle = new Label
            {
                Text = "💡 [当前专线] 正在检测当前连接节点…",
                AutoSize = false,
                Left = 20,
                Top = 42,
                Width = 540,
                Height = 28,
                Font = new Font("Microsoft YaHei UI", 13.5F, FontStyle.Bold),
                ForeColor = Color.FromArgb(20, 35, 55)
            };

            lblActiveLatency = new Label
            {
                Text = "⚡ 实时延迟: -- ms",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 12F, FontStyle.Bold),
                ForeColor = Color.FromArgb(22, 163, 74),
                Left = 22,
                Top = 72
            };

            lblActiveDetails = new Label
            {
                Text = "🌐 独立出口: 正在读取…   ·   独占隧道 127.0.0.1:17897 (不影响外部 Clash 模式)",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 9F),
                ForeColor = Color.FromArgb(75, 85, 99),
                Left = 22,
                Top = 100
            };

            lblActiveSecurity = new Label
            {
                Text = "🛡️ 状态认证: Google 204 通畅 · 真实模型握手正常 · 自动记忆首选节点",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold),
                ForeColor = Color.FromArgb(37, 99, 235),
                Left = 22,
                Top = 124
            };

            // 核心功能按钮 1：切换至代码窗口
            btnSwitchCode = new Button
            {
                Text = "👉 切换至代码窗口",
                Left = 580,
                Top = 38,
                Width = 200,
                Height = 42,
                BackColor = Color.FromArgb(37, 99, 235),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 10.5F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnSwitchCode.FlatAppearance.BorderSize = 0;
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

            // 核心功能按钮 2：强制重新自愈检测
            btnReheal = new Button
            {
                Text = "🔄 重新自愈检测",
                Left = 580,
                Top = 90,
                Width = 140,
                Height = 32,
                BackColor = Color.FromArgb(254, 242, 242),
                ForeColor = Color.FromArgb(185, 28, 28),
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnReheal.FlatAppearance.BorderColor = Color.FromArgb(254, 202, 202);
            btnReheal.Click += delegate
            {
                appContext.TriggerRehealWorkflow();
            };

            glassCard.Controls.AddRange(new Control[] { badge, lblActiveTitle, lblActiveLatency, lblActiveDetails, lblActiveSecurity, btnSwitchCode, btnReheal });
            topPanel.Controls.Add(glassCard);

            // 0. 预先初始化节点列表 ListView，防止单选按钮事件触发空引用
            listNodes = new ListView
            {
                Dock = DockStyle.Fill,
                View = View.Details,
                FullRowSelect = true,
                GridLines = true,
                HeaderStyle = ColumnHeaderStyle.Nonclickable,
                Font = new Font("Microsoft YaHei UI", 9F),
                BorderStyle = BorderStyle.FixedSingle
            };
            listNodes.Columns.Add("序号", 55);
            listNodes.Columns.Add("地区", 80);
            listNodes.Columns.Add("节点名称 (当前正在使用的专线已高亮置顶)", 350);
            listNodes.Columns.Add("TCP 延迟", 95);
            listNodes.Columns.Add("状态", 100);
            listNodes.Columns.Add("订阅来源", 110);
            listNodes.Columns.Add("服务器地址", 130);
            listNodes.DoubleClick += delegate { SwitchSelectedNode(); };

            // 2. 地区筛选栏
            filterPanel = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 42,
                BackColor = Color.FromArgb(215, 229, 242),
                Padding = new Padding(20, 6, 20, 4)
            };

            string[] regions = new string[] { "全部", "🇺🇸 美国", "🇯🇵 日本", "🇸🇬 新加坡", "🇭🇰 香港", "🇰🇷 韩国" };
            foreach (var r in regions)
            {
                var rb = new RadioButton
                {
                    Text = r,
                    AutoSize = true,
                    Checked = (r == "全部"),
                    Margin = new Padding(0, 0, 16, 0),
                    Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold),
                    ForeColor = Color.FromArgb(30, 50, 75),
                    Cursor = Cursors.Hand
                };
                string captured = r.Replace("🇺🇸 ", "").Replace("🇯🇵 ", "").Replace("🇸🇬 ", "").Replace("🇭🇰 ", "").Replace("🇰🇷 ", "");
                rb.CheckedChanged += delegate
                {
                    if (rb.Checked && listNodes != null)
                    {
                        currentRegionFilter = captured;
                        FilterListView();
                    }
                };
                filterPanel.Controls.Add(rb);
            }

            // 3. 底部操作栏
            var bottomPanel = new Panel
            {
                Dock = DockStyle.Bottom,
                Height = 65,
                BackColor = Color.FromArgb(215, 229, 242),
                Padding = new Padding(16, 10, 16, 12)
            };

            btnTestAll = new Button
            {
                Text = "⚡ 一键全量并发测速",
                Size = new Size(170, 38),
                Left = 20,
                Top = 12,
                BackColor = Color.FromArgb(37, 99, 235),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnTestAll.FlatAppearance.BorderSize = 0;
            btnTestAll.Click += delegate { StartSpeedTest(); };

            btnApplySelected = new Button
            {
                Text = "👉 一键应用并切换",
                Size = new Size(160, 38),
                Left = 205,
                Top = 12,
                BackColor = Color.FromArgb(22, 163, 74),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnApplySelected.FlatAppearance.BorderSize = 0;
            btnApplySelected.Click += delegate { SwitchSelectedNode(); };

            btnHideToTray = new Button
            {
                Text = "❌ 隐藏到托盘",
                Size = new Size(120, 38),
                Left = 380,
                Top = 12,
                BackColor = Color.FromArgb(243, 247, 252),
                ForeColor = Color.FromArgb(70, 90, 115),
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnHideToTray.FlatAppearance.BorderColor = Color.FromArgb(191, 219, 254);
            btnHideToTray.Click += delegate { Hide(); };

            lblFeedback = new Label
            {
                Text = "💡 双击下方任意节点直接无感热切换，反重力写代码无需重启！",
                AutoSize = true,
                ForeColor = Color.FromArgb(70, 90, 115),
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold),
                Left = 520,
                Top = 22
            };

            bottomPanel.Controls.AddRange(new Control[] { btnTestAll, btnApplySelected, btnHideToTray, lblFeedback });

            var listContainer = new Panel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(16, 4, 16, 6),
                BackColor = Color.FromArgb(215, 229, 242)
            };
            listContainer.Controls.Add(listNodes);

            Controls.Add(listContainer);
            Controls.Add(filterPanel);
            Controls.Add(bottomPanel);
            Controls.Add(topPanel);
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
            lblActiveTitle.Text = "💡 [当前专线] " + name;
            string latStr = lat < 9000 ? (lat + " ms (极速)") : "已连通";
            lblActiveLatency.Text = "⚡ 实时延迟: " + latStr;
            lblActiveLatency.ForeColor = (lat < 220) ? Color.FromArgb(22, 163, 74) : ((lat < 500) ? Color.FromArgb(217, 119, 6) : Color.FromArgb(220, 38, 38));
            lblActiveDetails.Text = "🌐 独立出口: [" + egress + "] " + server + "   ·   独占隧道 127.0.0.1:17897 (不影响外部 Clash)";
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
                        UpdateCurrentActiveView(activeNode.DisplayName, activeNode.Country, activeNode.Server + ":" + activeNode.Port, activeNode.Latency);
                    }
                    else if (!string.IsNullOrEmpty(currentConnectedServer))
                    {
                        UpdateCurrentActiveView("当前已连通专线 (" + currentConnectedServer + ")", "专线", currentConnectedServer + ":" + currentConnectedPort, 120);
                    }
                    FilterListView();
                    StartSpeedTest();
                }));
            });
        }

        private void ReadCurrentProxyConfig()
        {
            try
            {
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
                                    string flag = "🌐 ";
                                    if (Regex.IsMatch(name, @"日本|Japan|Tokyo|JP", RegexOptions.IgnoreCase)) { country = "日本"; flag = "🇯🇵 "; }
                                    else if (Regex.IsMatch(name, @"新加坡|Singapore|SG", RegexOptions.IgnoreCase)) { country = "新加坡"; flag = "🇸🇬 "; }
                                    else if (Regex.IsMatch(name, @"美国|USA|United States|US", RegexOptions.IgnoreCase)) { country = "美国"; flag = "🇺🇸 "; }
                                    else if (Regex.IsMatch(name, @"香港|Hong Kong|HK", RegexOptions.IgnoreCase)) { country = "香港"; flag = "🇭🇰 "; }
                                    else if (Regex.IsMatch(name, @"韩国|Korea|KR", RegexOptions.IgnoreCase)) { country = "韩国"; flag = "🇰🇷 "; }

                                    bool isCurrent = (!string.IsNullOrEmpty(currentConnectedServer) && srv == currentConnectedServer && port == currentConnectedPort);

                                    result.Add(new NodeItem
                                    {
                                        Name = name,
                                        DisplayName = flag + name,
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
            listNodes.Items.Clear();
            int idx = 1;

            var displayList = new List<NodeItem>();
            foreach (var n in allNodes)
            {
                if (n.IsCurrent) displayList.Insert(0, n);
                else displayList.Add(n);
            }

            foreach (var n in displayList)
            {
                if (currentRegionFilter != "全部" && n.Country != currentRegionFilter)
                    continue;

                string latStr = n.Latency < 9000 ? (n.Latency + "ms") : "--";
                string status = n.IsCurrent ? "🟢 当前在用" : (n.Latency < 200 ? "⚡ 极速" : (n.Latency < 500 ? "★ 良好" : "超时/未测"));
                string titleText = n.IsCurrent ? ("🟢 [当前使用] " + n.DisplayName) : n.DisplayName;

                var item = new ListViewItem(idx.ToString());
                item.SubItems.Add(n.Country);
                item.SubItems.Add(titleText);
                item.SubItems.Add(latStr);
                item.SubItems.Add(status);
                item.SubItems.Add(n.Subscription);
                item.SubItems.Add(n.Server + ":" + n.Port);
                item.Tag = n;

                if (n.IsCurrent)
                {
                    item.BackColor = Color.FromArgb(236, 253, 245);
                    item.ForeColor = Color.FromArgb(21, 128, 61);
                    item.Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold);
                }
                else if (n.Latency < 200) item.ForeColor = Color.FromArgb(21, 128, 61);
                else if (n.Latency < 500) item.ForeColor = Color.FromArgb(180, 83, 9);
                else if (n.Latency < 9000) item.ForeColor = Color.FromArgb(75, 85, 99);
                else item.ForeColor = Color.FromArgb(156, 163, 175);

                listNodes.Items.Add(item);
                idx++;
            }
        }

        private void StartSpeedTest()
        {
            btnTestAll.Enabled = false;
            btnTestAll.Text = "⚡ 正在并发测速中…";
            lblFeedback.Text = "正在向所有候选专线并发发起高精度延迟探测…";

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

                allNodes.Sort((a, b) =>
                {
                    if (a.IsCurrent) return -1;
                    if (b.IsCurrent) return 1;
                    return a.Latency.CompareTo(b.Latency);
                });

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
                        UpdateCurrentActiveView(activeNode.DisplayName, activeNode.Country, activeNode.Server + ":" + activeNode.Port, activeNode.Latency);
                    }
                    btnTestAll.Enabled = true;
                    btnTestAll.Text = "⚡ 一键全量并发测速";
                    lblFeedback.Text = "测速完成！所有优质低延迟专线已置顶。双击即可一键热切换！";
                }));
            });
        }

        private void SwitchSelectedNode()
        {
            if (listNodes.SelectedItems.Count == 0)
            {
                MessageBox.Show("请先在列表中点击选择一个节点！", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            var selectedNode = listNodes.SelectedItems[0].Tag as NodeItem;
            if (selectedNode == null) return;

            lblFeedback.Text = "正在热切换私有代理内核…";
            lblFeedback.ForeColor = Color.FromArgb(37, 99, 235);
            Application.DoEvents();

            bool ok = HotSwitchNode(selectedNode);
            if (ok)
            {
                foreach (var n in allNodes) n.IsCurrent = (n == selectedNode);
                currentConnectedServer = selectedNode.Server;
                currentConnectedPort = selectedNode.Port;

                lblFeedback.Text = "切换成功！已热切换至: " + selectedNode.Name;
                lblFeedback.ForeColor = Color.FromArgb(21, 128, 61);

                UpdateCurrentActiveView(selectedNode.DisplayName, selectedNode.Country, selectedNode.Server + ":" + selectedNode.Port, selectedNode.Latency);
                FilterListView();
                appContext.UpdateStatus();

                MessageBox.Show("已成功热切换到专线：\n" + selectedNode.Name + "\n\nAntigravity 反重力软件完全无需重启，已立即走新专线！", "切换成功", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            else
            {
                lblFeedback.Text = "切换失败，请重试！";
                lblFeedback.ForeColor = Color.FromArgb(220, 38, 38);
                MessageBox.Show("切换失败，未能重新启动私有代理内核。", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private bool HotSwitchNode(NodeItem node)
        {
            // 检查后台 Supervisor 是否正在执行自愈或探针
            try
            {
                using (var probeSupervisor = Mutex.OpenExisting(Program.SupervisorMutexName))
                {
                    MessageBox.Show("后台自愈守护程序正在测速与配置，请稍候 3 秒后再切换！", "系统提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return false;
                }
            }
            catch { }

            Mutex crossProcessLock = null;
            bool lockTaken = false;
            try
            {
                crossProcessLock = new Mutex(false, @"Local\AntigravityMihomoLock");
                try { lockTaken = crossProcessLock.WaitOne(3000); } catch { lockTaken = true; }
                if (!lockTaken)
                {
                    MessageBox.Show("后台自愈程序正在测试节点，请稍候 3 秒后再切换！", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return false;
                }

                string proxyRoot = Program.RuntimeDirectory;
                string configFile = Path.Combine(proxyRoot, "mihomo-antigravity.yaml");
                string pidFile = Path.Combine(proxyRoot, "mihomo.pid");

                string configContent = "# Generated by Antigravity NodeTray hot switch\n" +
                    "mixed-port: 17897\n" +
                    "allow-lan: false\n" +
                    "bind-address: 127.0.0.1\n" +
                    "mode: rule\n" +
                    "log-level: silent\n" +
                    "ipv6: true\n" +
                    "tun:\n  enable: false\n" +
                    "proxies:\n" +
                    "  - " + node.RawLine + "\n" +
                    "proxy-groups:\n" +
                    "  - name: ANTIGRAVITY-ROUTE\n" +
                    "    type: select\n" +
                    "    proxies:\n" +
                    "      - " + node.Name + "\n" +
                    "rules:\n" +
                    "  - MATCH,ANTIGRAVITY-ROUTE\n";

                File.WriteAllText(configFile, configContent, Encoding.UTF8);

                if (File.Exists(pidFile))
                {
                    try
                    {
                        int oldPid;
                        if (int.TryParse(File.ReadAllText(pidFile).Trim(), out oldPid))
                        {
                            var oldP = Process.GetProcessById(oldPid);
                            oldP.Kill();
                        }
                    }
                    catch { }
                }

                string mihomoPath = ResolveMihomoPath();
                if (!File.Exists(mihomoPath)) return false;

                var psi = new ProcessStartInfo
                {
                    FileName = mihomoPath,
                    Arguments = "-d \"" + proxyRoot + "\" -f \"" + configFile + "\"",
                    WorkingDirectory = proxyRoot,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
                var proc = Process.Start(psi);
                File.WriteAllText(pidFile, proc.Id.ToString());

                string prefFile = Path.Combine(proxyRoot, "user-preferred-node.json");
                string country = "US";
                if (node.Country == "日本") country = "JP";
                else if (node.Country == "新加坡") country = "SG";
                else if (node.Country == "香港") country = "HK";
                else if (node.Country == "韩国") country = "KR";

                string prefJson = "{\n" +
                    "  \"name\": \"" + node.Name.Replace("\"", "\\\"") + "\",\n" +
                    "  \"server\": \"" + node.Server + "\",\n" +
                    "  \"port\": " + node.Port + ",\n" +
                    "  \"country\": \"" + country + "\",\n" +
                    "  \"updated_at\": \"" + DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss+08:00") + "\"\n" +
                    "}\n";
                File.WriteAllText(prefFile, prefJson, Encoding.UTF8);

                return true;
            }
            catch
            {
                return false;
            }
            finally
            {
                if (lockTaken && crossProcessLock != null)
                {
                    try { crossProcessLock.ReleaseMutex(); } catch { }
                    crossProcessLock.Dispose();
                }
            }
        }

        private string ResolveMihomoPath()
        {
            string[] candidates = new string[]
            {
                @"D:\Program Files\Clash Verge\verge-mihomo.exe",
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Clash Verge\verge-mihomo.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Clash Verge\verge-mihomo.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Mihomo Party\resources\sidecar\mihomo-windows-amd64.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Mihomo Party\resources\sidecar\mihomo-windows-amd64.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Flclash\mihomo.exe")
            };
            foreach (var c in candidates)
            {
                if (File.Exists(c)) return c;
            }
            return @"D:\Program Files\Clash Verge\verge-mihomo.exe";
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
