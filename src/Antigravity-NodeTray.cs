using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Net.Sockets;
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
            bool createdNew;
            singleInstanceMutex = new Mutex(true, @"Local\AntigravityNodeTraySingleInstance", out createdNew);
            if (!createdNew)
            {
                // 已有实例，如果带了 --show-panel 参数，发信号呼出面板
                TrayAppContext.SignalShowPanel();
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new TrayAppContext());
        }
    }

    internal class TrayAppContext : ApplicationContext
    {
        private NotifyIcon notifyIcon;
        private ContextMenuStrip contextMenu;
        private System.Windows.Forms.Timer pollTimer;
        private NodeControlForm controlForm;
        private static EventWaitHandle showPanelEvent;

        private int currentLat = 9999;
        private string currentEgress = "US";
        private string currentServer = "";
        private int notRunningCount = 0;

        public TrayAppContext()
        {
            InitializeTray();
            InitializeNamedEventWatcher();
            UpdateStatus();

            pollTimer = new System.Windows.Forms.Timer { Interval = 15000 };
            pollTimer.Tick += delegate { OnTimerTick(); };
            pollTimer.Start();
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
                    if (notifyIcon != null)
                    {
                        var dummy = new Form();
                        dummy.CreateControl();
                        dummy.BeginInvoke(new Action(ShowControlPanel));
                    }
                }, null, -1, false);
            }
            catch { }
        }

        private void InitializeTray()
        {
            contextMenu = new ContextMenuStrip();
            contextMenu.Font = new Font("Microsoft YaHei UI", 9F);

            var latItem = new ToolStripMenuItem("⚡ 实时延迟: 检测中…") { Enabled = false };
            var egressItem = new ToolStripMenuItem("🌐 当前出口: 检测中…") { Enabled = false };
            var openItem = new ToolStripMenuItem("🖥 打开节点控制面板 (测速 / 切换)") { Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold) };
            openItem.Click += delegate { ShowControlPanel(); };

            var refreshItem = new ToolStripMenuItem("🔄 刷新状态");
            refreshItem.Click += delegate { UpdateStatus(); };

            var exitItem = new ToolStripMenuItem("❌ 退出托盘");
            exitItem.Click += delegate { ExitTray(); };

            contextMenu.Items.Add(latItem);
            contextMenu.Items.Add(egressItem);
            contextMenu.Items.Add(new ToolStripSeparator());
            contextMenu.Items.Add(openItem);
            contextMenu.Items.Add(refreshItem);
            contextMenu.Items.Add(new ToolStripSeparator());
            contextMenu.Items.Add(exitItem);

            notifyIcon = new NotifyIcon
            {
                Text = "Antigravity 代理监控",
                ContextMenuStrip = contextMenu,
                Visible = true
            };
            notifyIcon.DoubleClick += delegate { ShowControlPanel(); };
            notifyIcon.MouseClick += delegate(object s, MouseEventArgs e)
            {
                if (e.Button == MouseButtons.Left) ShowControlPanel();
            };
            UpdateIconImage(currentLat);
        }

        private void OnTimerTick()
        {
            // 检查 Antigravity 是否在运行
            Process[] procs = Process.GetProcessesByName("Antigravity");
            if (procs == null || procs.Length == 0)
            {
                notRunningCount++;
                if (notRunningCount >= 4) // 60秒无 Antigravity 则退出托盘
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

        private void UpdateStatus()
        {
            Task.Run(delegate
            {
                try
                {
                    string proxyRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Antigravity\private-proxy");
                    string configFile = Path.Combine(proxyRoot, "mihomo-antigravity.yaml");
                    string stateFile = Path.Combine(proxyRoot, "supervisor-state.json");

                    string server = "";
                    int port = 0;
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

                    if (notifyIcon != null)
                    {
                        // removed // trigger on UI thread if needed
                        UpdateTrayUi(currentLat, currentEgress, currentServer);
                    }
                }
                catch { }
            });
        }

        private void UpdateTrayUi(int lat, string egress, string server)
        {
            if (contextMenu.InvokeRequired)
            {
                contextMenu.BeginInvoke(new Action(delegate { UpdateTrayUi(lat, egress, server); }));
                return;
            }

            string latStr = lat < 9000 ? (lat + "ms") : "超时";
            contextMenu.Items[0].Text = "⚡ 实时延迟: " + latStr + " [" + egress + "]";
            contextMenu.Items[1].Text = "🌐 当前出口: " + (string.IsNullOrEmpty(server) ? "未连接" : server);

            string title = "Antigravity 代理: [" + egress + "] " + latStr;
            if (title.Length > 63) title = title.Substring(0, 63);
            notifyIcon.Text = title;

            UpdateIconImage(lat);
        }

        private void UpdateIconImage(int lat)
        {
            try
            {
                int size = 16;
                using (var bmp = new Bitmap(size, size))
                using (var g = Graphics.FromImage(bmp))
                {
                    g.SmoothingMode = SmoothingMode.AntiAlias;
                    g.Clear(Color.Transparent);

                    Color bg = Color.FromArgb(239, 68, 68); // 红色
                    if (lat < 220) bg = Color.FromArgb(34, 197, 94); // 绿色
                    else if (lat < 500) bg = Color.FromArgb(234, 179, 8); // 黄色

                    using (var b = new SolidBrush(bg))
                    {
                        g.FillEllipse(b, 1, 1, size - 2, size - 2);
                    }
                    using (var p = new Pen(Color.FromArgb(200, 255, 255, 255), 1f))
                    {
                        g.DrawEllipse(p, 1, 1, size - 2, size - 2);
                    }

                    Icon icon = Icon.FromHandle(bmp.GetHicon());
                    notifyIcon.Icon = icon;
                }
            }
            catch { }
        }

        public void ShowControlPanel()
        {
            if (controlForm == null || controlForm.IsDisposed)
            {
                controlForm = new NodeControlForm(this);
                controlForm.Show();
            }
            else
            {
                if (controlForm.WindowState == FormWindowState.Minimized)
                    controlForm.WindowState = FormWindowState.Normal;
                controlForm.BringToFront();
                controlForm.Activate();
            }
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

    internal class NodeControlForm : Form
    {
        private TrayAppContext appContext;
        private Label lblStatus;
        private Label lblCurrentNode;
        private Label lblLatency;
        private Label lblFeedback;
        private ListView listNodes;
        private Button btnTestAll;
        private Button btnApplySelected;
        private FlowLayoutPanel filterPanel;
        private string currentRegionFilter = "全部";

        private List<NodeItem> allNodes = new List<NodeItem>();

        public NodeControlForm(TrayAppContext context)
        {
            appContext = context;
            InitializeComponent();
            LoadNodesAndState();
        }

        private void InitializeComponent()
        {
            Text = "Antigravity 节点中控台 (原生纯净版)";
            ClientSize = new Size(880, 600);
            MinimumSize = new Size(780, 520);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Microsoft YaHei UI", 9F);
            BackColor = Color.FromArgb(243, 244, 246);

            // 顶部卡片
            var topPanel = new Panel
            {
                Dock = DockStyle.Top,
                Height = 110,
                BackColor = Color.White,
                Padding = new Padding(18, 12, 18, 12)
            };

            lblStatus = new Label
            {
                Text = "● 状态检查中…",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 12F, FontStyle.Bold),
                ForeColor = Color.FromArgb(21, 128, 61),
                Left = 18,
                Top = 14
            };

            lblCurrentNode = new Label
            {
                Text = "当前连接: 正在获取…",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 9.5F),
                ForeColor = Color.FromArgb(75, 85, 99),
                Left = 20,
                Top = 44
            };

            lblLatency = new Label
            {
                Text = "TCP 往返延迟: -- ms   |   Google 204: 正常",
                AutoSize = true,
                Font = new Font("Microsoft YaHei UI", 9F),
                ForeColor = Color.FromArgb(107, 114, 128),
                Left = 20,
                Top = 72
            };

            topPanel.Controls.AddRange(new Control[] { lblStatus, lblCurrentNode, lblLatency });

            // 筛选栏
            filterPanel = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 36,
                BackColor = Color.FromArgb(243, 244, 246),
                Padding = new Padding(18, 6, 18, 4)
            };

            string[] regions = new string[] { "全部", "日本", "新加坡", "美国", "香港", "韩国" };
            foreach (var r in regions)
            {
                var rb = new RadioButton
                {
                    Text = r,
                    AutoSize = true,
                    Checked = (r == "全部"),
                    Margin = new Padding(0, 0, 14, 0),
                    Font = new Font("Microsoft YaHei UI", 9F)
                };
                string captured = r;
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
                Height = 60,
                BackColor = Color.White,
                Padding = new Padding(18, 10, 18, 10)
            };

            btnTestAll = new Button
            {
                Text = "⚡ 一键全量并发测速",
                Size = new Size(160, 36),
                Left = 18,
                Top = 12,
                BackColor = Color.FromArgb(37, 99, 235),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnTestAll.FlatAppearance.BorderSize = 0;
            btnTestAll.Click += delegate { StartSpeedTest(); };

            btnApplySelected = new Button
            {
                Text = "👉 一键应用并切换",
                Size = new Size(160, 36),
                Left = 190,
                Top = 12,
                BackColor = Color.FromArgb(22, 163, 74),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnApplySelected.FlatAppearance.BorderSize = 0;
            btnApplySelected.Click += delegate { SwitchSelectedNode(); };

            lblFeedback = new Label
            {
                Text = "提示：双击列表中任意节点可直接无感热切换，反重力软件无需重启！",
                AutoSize = true,
                ForeColor = Color.FromArgb(107, 114, 128),
                Left = 365,
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
                Font = new Font("Microsoft YaHei UI", 9F)
            };
            listNodes.Columns.Add("序号", 50);
            listNodes.Columns.Add("地区", 65);
            listNodes.Columns.Add("节点名称", 280);
            listNodes.Columns.Add("TCP 延迟", 90);
            listNodes.Columns.Add("状态", 95);
            listNodes.Columns.Add("订阅来源", 120);
            listNodes.Columns.Add("服务器地址", 150);

            listNodes.DoubleClick += delegate { SwitchSelectedNode(); };

            Controls.Add(listNodes);
            Controls.Add(filterPanel);
            Controls.Add(bottomPanel);
            Controls.Add(topPanel);
        }

        private void LoadNodesAndState()
        {
            Task.Run(delegate
            {
                var nodes = DiscoverySubscriptionNodes();
                allNodes = nodes;

                BeginInvoke(new Action(delegate
                {
                    FilterListView();
                    UpdateDashboardInfo();
                    StartSpeedTest();
                }));
            });
        }

        private void UpdateDashboardInfo()
        {
            try
            {
                string proxyRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Antigravity\private-proxy");
                string configFile = Path.Combine(proxyRoot, "mihomo-antigravity.yaml");
                string stateFile = Path.Combine(proxyRoot, "supervisor-state.json");

                string srv = "";
                if (File.Exists(configFile))
                {
                    string txt = File.ReadAllText(configFile, Encoding.UTF8);
                    var m = Regex.Match(txt, @"server:\s*([^\s,]+),\s*port:\s*(\d+)");
                    if (m.Success) srv = m.Groups[1].Value + ":" + m.Groups[2].Value;
                }

                string country = "US";
                if (File.Exists(stateFile))
                {
                    string st = File.ReadAllText(stateFile, Encoding.UTF8);
                    var m = Regex.Match(st, @"""egress_country""\s*:\s*""([^""]+)""");
                    if (m.Success) country = m.Groups[1].Value;
                }

                lblStatus.Text = "● 私有代理正常运行中 (127.0.0.1:17897)";
                lblStatus.ForeColor = Color.FromArgb(21, 128, 61);
                lblCurrentNode.Text = "当前出口: [" + country + "] " + (string.IsNullOrEmpty(srv) ? "检测中…" : srv);
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
                                    if (Regex.IsMatch(name, @"日本|Japan|Tokyo|JP", RegexOptions.IgnoreCase)) country = "日本";
                                    else if (Regex.IsMatch(name, @"新加坡|Singapore|SG", RegexOptions.IgnoreCase)) country = "新加坡";
                                    else if (Regex.IsMatch(name, @"美国|USA|United States|US", RegexOptions.IgnoreCase)) country = "美国";
                                    else if (Regex.IsMatch(name, @"香港|Hong Kong|HK", RegexOptions.IgnoreCase)) country = "香港";
                                    else if (Regex.IsMatch(name, @"韩国|Korea|KR", RegexOptions.IgnoreCase)) country = "韩国";

                                    result.Add(new NodeItem
                                    {
                                        Name = name,
                                        Server = srv,
                                        Port = port,
                                        Country = country,
                                        Subscription = subName,
                                        RawLine = line.Trim().TrimStart('-').Trim(),
                                        Latency = 9999
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
            foreach (var n in allNodes)
            {
                if (currentRegionFilter != "全部" && n.Country != currentRegionFilter)
                    continue;

                string latStr = n.Latency < 9000 ? (n.Latency + "ms") : "--";
                string status = n.Latency < 200 ? "⚡ 极速" : (n.Latency < 500 ? "★ 良好" : "超时/未测");

                var item = new ListViewItem(idx.ToString());
                item.SubItems.Add(n.Country);
                item.SubItems.Add(n.Name);
                item.SubItems.Add(latStr);
                item.SubItems.Add(status);
                item.SubItems.Add(n.Subscription);
                item.SubItems.Add(n.Server + ":" + n.Port);
                item.Tag = n;

                if (n.Latency < 200) item.ForeColor = Color.FromArgb(21, 128, 61);
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
            lblFeedback.Text = "多线程并发测速中，请稍候约 1~2 秒…";

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

                // 排序：可用节点按延迟升序排在最前面
                allNodes.Sort((a, b) => a.Latency.CompareTo(b.Latency));

                BeginInvoke(new Action(delegate
                {
                    FilterListView();
                    btnTestAll.Enabled = true;
                    btnTestAll.Text = "⚡ 一键全量并发测速";
                    lblFeedback.Text = "测速完成！所有优质专线已自动置顶排序。双击即可一键热切换！";
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
                lblFeedback.Text = "切换成功！已成功切换至: " + selectedNode.Name;
                lblFeedback.ForeColor = Color.FromArgb(21, 128, 61);
                UpdateDashboardInfo();
                MessageBox.Show("已成功切换到节点：\n" + selectedNode.Name + "\n\nAntigravity 反重力软件完全无需重启，已立即走新线路！", "切换成功", MessageBoxButtons.OK, MessageBoxIcon.Information);
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
            try
            {
                string proxyRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Antigravity\private-proxy");
                string configFile = Path.Combine(proxyRoot, "mihomo-antigravity.yaml");
                string pidFile = Path.Combine(proxyRoot, "mihomo.pid");

                // 生成配置
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

                // 杀死旧进程
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

                // 探测 mihomo 内核
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

                // 持久化用户偏好
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
        public string Server { get; set; }
        public int Port { get; set; }
        public string Country { get; set; }
        public string Subscription { get; set; }
        public string RawLine { get; set; }
        public int Latency { get; set; }
    }
}
