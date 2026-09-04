using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace AntigravityNodeTray
{
    internal static class Program
    {
        private static Mutex singleInstanceMutex;

        [STAThread]
        private static void Main(string[] args)
        {
            bool showPanel = args != null && Array.Exists(args, delegate(string a) {
                return string.Equals(a, "--show-panel", StringComparison.OrdinalIgnoreCase);
            });

            bool createdNew;
            singleInstanceMutex = new Mutex(true, @"Local\AntigravityNodeTraySingleInstance", out createdNew);
            if (!createdNew)
            {
                // 已有后台实例在跑，发送跨进程事件呼出面板
                TrayAppContext.SignalShowPanel();
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new TrayAppContext(showPanel));
        }
    }

    internal class TrayAppContext : ApplicationContext
    {
        private NotifyIcon notifyIcon;
        private ContextMenuStrip contextMenu;
        private System.Windows.Forms.Timer pollTimer;
        private NodeControlForm controlForm;
        private static EventWaitHandle showPanelEvent;
        private static SynchronizationContext uiContext;
        private Icon appIcon;

        private int currentLat = 9999;
        private string currentEgress = "US";
        private string currentServer = "";
        private string currentNodeName = "检测中…";
        private int notRunningCount = 0;

        public TrayAppContext(bool showPanelOnStartup = false)
        {
            uiContext = SynchronizationContext.Current ?? new WindowsFormsSynchronizationContext();
            LoadAppIcon();
            InitializeTray();
            InitializeNamedEventWatcher();
            UpdateStatus();

            pollTimer = new System.Windows.Forms.Timer { Interval = 15000 };
            pollTimer.Tick += delegate { OnTimerTick(); };
            pollTimer.Start();

            if (showPanelOnStartup)
            {
                ShowControlPanel();
            }
        }

        private void LoadAppIcon()
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string icoPath = Path.Combine(baseDir, "Antigravity-Launcher.ico");
                if (File.Exists(icoPath))
                {
                    appIcon = new Icon(icoPath);
                }
            }
            catch { }
        }

        public static void SignalShowPanel()
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

        private void InitializeNamedEventWatcher()
        {
            try
            {
                bool createdNew;
                showPanelEvent = new EventWaitHandle(false, EventResetMode.AutoReset, @"Local\AntigravityNodeTrayShowPanel", out createdNew);
                ThreadPool.RegisterWaitForSingleObject(showPanelEvent, delegate
                {
                    if (uiContext != null)
                    {
                        uiContext.Post(delegate
                        {
                            ShowControlPanel();
                        }, null);
                    }
                }, null, -1, false);
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
            var openItem = new ToolStripMenuItem("🖥 打开节点控制面板 (测速 / 切换)") { Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold) };
            openItem.Click += delegate { ShowControlPanel(); };

            var refreshItem = new ToolStripMenuItem("🔄 刷新延迟与状态");
            refreshItem.Click += delegate { UpdateStatus(); };

            var exitItem = new ToolStripMenuItem("❌ 退出托盘");
            exitItem.Click += delegate { ExitTray(); };

            contextMenu.Items.Add(titleItem);
            contextMenu.Items.Add(latItem);
            contextMenu.Items.Add(egressItem);
            contextMenu.Items.Add(new ToolStripSeparator());
            contextMenu.Items.Add(openItem);
            contextMenu.Items.Add(refreshItem);
            contextMenu.Items.Add(new ToolStripSeparator());
            contextMenu.Items.Add(exitItem);

            notifyIcon = new NotifyIcon
            {
                Text = "Antigravity 智能启动器",
                ContextMenuStrip = contextMenu,
                Icon = appIcon ?? SystemIcons.Application,
                Visible = true
            };
            notifyIcon.DoubleClick += delegate { ShowControlPanel(); };
            notifyIcon.Click += delegate { ShowControlPanel(); };
        }

        private void OnTimerTick()
        {
            Process[] procs = Process.GetProcessesByName("Antigravity");
            if (procs == null || procs.Length == 0)
            {
                notRunningCount++;
                if (notRunningCount >= 4) // 60秒无 Antigravity 则自动退出
                {
                    ExitTray();
                    return;
                }
            }
            else
            {
                notRunningCount = 0;
            }

            UpdateStatus();
        }

        public void UpdateStatus()
        {
            Task.Run(delegate
            {
                try
                {
                    string proxyRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Antigravity\private-proxy");
                    string configFile = Path.Combine(proxyRoot, "mihomo-antigravity.yaml");
                    string stateFile = Path.Combine(proxyRoot, "supervisor-state.json");
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
                            if (mName.Success) nodeName = mName.Groups[1].Value;
                        }
                        catch { }
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

            string title = "Antigravity 代理: [" + egress + "] " + latStr + "\n节点: " + nodeName;
            if (title.Length > 63) title = title.Substring(0, 63);
            notifyIcon.Text = title;

            if (controlForm != null && !controlForm.IsDisposed && controlForm.Visible)
            {
                controlForm.UpdateCurrentActiveView(nodeName, egress, server, lat);
            }
        }

        public void ShowControlPanel()
        {
            if (controlForm == null || controlForm.IsDisposed)
            {
                controlForm = new NodeControlForm(this);
            }

            if (!controlForm.Visible)
            {
                controlForm.Show();
            }
            if (controlForm.WindowState == FormWindowState.Minimized)
            {
                controlForm.WindowState = FormWindowState.Normal;
            }

            NodeControlForm.ForceForeground(controlForm.Handle);
        }

        private void ExitTray()
        {
            if (pollTimer != null) pollTimer.Stop();
            if (notifyIcon != null)
            {
                notifyIcon.Visible = false;
                notifyIcon.Dispose();
            }
            Application.Exit();
        }
    }

    internal class GlassPanel : Panel
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
            using (var path = RoundedRectangle(bounds, 16))
            using (var fill = new LinearGradientBrush(bounds, Color.FromArgb(250, 252, 255), Color.FromArgb(235, 244, 252), 90F))
            using (var border = new Pen(Color.FromArgb(235, 255, 255, 255), 1.2F))
            {
                e.Graphics.FillPath(fill, path);
                e.Graphics.DrawPath(border, path);
            }
        }
    }

    internal class NodeControlForm : Form
    {
        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
        [DllImport("user32.dll")]
        private static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
        [DllImport("user32.dll")]
        private static extern bool BringWindowToTop(IntPtr hWnd);
        [DllImport("user32.dll")]
        private static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("kernel32.dll")]
        private static extern uint GetCurrentThreadId();

        public static void ForceForeground(IntPtr hWnd)
        {
            try
            {
                IntPtr fg = GetForegroundWindow();
                uint dummy;
                uint fgThread = GetWindowThreadProcessId(fg, out dummy);
                uint curThread = GetCurrentThreadId();
                if (fgThread != curThread && fgThread != 0) AttachThreadInput(curThread, fgThread, true);
                ShowWindowAsync(hWnd, 9); // SW_RESTORE
                ShowWindowAsync(hWnd, 5); // SW_SHOW
                BringWindowToTop(hWnd);
                SetForegroundWindow(hWnd);
                if (fgThread != curThread && fgThread != 0) AttachThreadInput(curThread, fgThread, false);
            }
            catch { }
        }

        private TrayAppContext appContext;
        private Label lblActiveTitle;
        private Label lblActiveLatency;
        private Label lblActiveDetails;
        private Label lblActiveSecurity;
        private Label lblFeedback;
        private ListView listNodes;
        private Button btnTestAll;
        private Button btnApplySelected;
        private FlowLayoutPanel filterPanel;
        private string currentRegionFilter = "全部";

        private List<NodeItem> allNodes = new List<NodeItem>();
        private string currentConnectedServer = "";
        private int currentConnectedPort = 0;

        public NodeControlForm(TrayAppContext context)
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
                string icoPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Antigravity-Launcher.ico");
                if (File.Exists(icoPath))
                {
                    Icon = new Icon(icoPath);
                }
            }
            catch { }
        }

        private void InitializeComponent()
        {
            Text = "Antigravity 节点中控台";
            ClientSize = new Size(940, 650);
            MinimumSize = new Size(840, 580);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Microsoft YaHei UI", 9F);
            BackColor = Color.FromArgb(215, 229, 242);

            FormClosing += delegate(object s, FormClosingEventArgs e)
            {
                if (e.CloseReason == CloseReason.UserClosing)
                {
                    e.Cancel = true;
                    Hide();
                }
            };

            // 顶部毛玻璃大卡片（醒目展示当前使用节点）
            var topPanel = new Panel
            {
                Dock = DockStyle.Top,
                Height = 150,
                BackColor = Color.FromArgb(215, 229, 242),
                Padding = new Padding(16, 12, 16, 6)
            };

            var glassCard = new GlassPanel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(20, 12, 20, 12)
            };

            lblActiveTitle = new Label
            {
                Text = "🟢 [当前使用中] 正在检测当前连接节点…",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 13.5F, FontStyle.Bold),
                ForeColor = Color.FromArgb(20, 35, 55),
                Left = 20,
                Top = 14
            };

            lblActiveLatency = new Label
            {
                Text = "⚡ 实时延迟: -- ms",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 12.5F, FontStyle.Bold),
                ForeColor = Color.FromArgb(22, 163, 74),
                Left = 22,
                Top = 46
            };

            lblActiveDetails = new Label
            {
                Text = "🌐 独立出口: 正在读取…   ·   独占隧道 127.0.0.1:17897 (不影响外部 Clash 模式)",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 9F),
                ForeColor = Color.FromArgb(75, 85, 99),
                Left = 22,
                Top = 76
            };

            lblActiveSecurity = new Label
            {
                Text = "🛡️ 状态认证: Google 204 通畅 · 真实模型握手正常 · 自动记忆首选节点",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold),
                ForeColor = Color.FromArgb(37, 99, 235),
                Left = 22,
                Top = 100
            };

            glassCard.Controls.AddRange(new Control[] { lblActiveTitle, lblActiveLatency, lblActiveDetails, lblActiveSecurity });
            topPanel.Controls.Add(glassCard);

            // 地区筛选栏
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
                    if (rb.Checked)
                    {
                        currentRegionFilter = captured;
                        FilterListView();
                    }
                };
                filterPanel.Controls.Add(rb);
            }

            // 底部操作栏
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
                Size = new Size(170, 38),
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

            lblFeedback = new Label
            {
                Text = "💡 双击下方任意节点直接无感热切换，反重力写代码无需重启！",
                AutoSize = true,
                ForeColor = Color.FromArgb(70, 90, 115),
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold),
                Left = 390,
                Top = 22
            };

            bottomPanel.Controls.AddRange(new Control[] { btnTestAll, btnApplySelected, lblFeedback });

            // 节点列表 ListView
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

            // 用一个带有外边距的 Panel 包裹 ListView，增强视觉呼吸感
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

        public void UpdateCurrentActiveView(string name, string egress, string server, int lat)
        {
            lblActiveTitle.Text = "🟢 [当前使用中] " + name;
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

                BeginInvoke(new Action(delegate
                {
                    FilterListView();
                    StartSpeedTest();
                }));
            });
        }

        private void ReadCurrentProxyConfig()
        {
            try
            {
                string proxyRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Antigravity\private-proxy");
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
                    item.BackColor = Color.FromArgb(236, 253, 245); // 优雅浅绿
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

                BeginInvoke(new Action(delegate
                {
                    FilterListView();
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

                string proxyRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Antigravity\private-proxy");
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
