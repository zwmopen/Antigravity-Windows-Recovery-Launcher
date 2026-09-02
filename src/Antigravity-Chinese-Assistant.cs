using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("Antigravity 中文助手")]
[assembly: AssemblyDescription("外部无侵入 Antigravity 简体中文界面助手")]
[assembly: AssemblyCompany("Community")]
[assembly: AssemblyProduct("Antigravity 中文助手")]
[assembly: AssemblyVersion("0.4.0.0")]
[assembly: AssemblyFileVersion("0.4.0.0")]

internal static class AntigravityChineseAssistant
{
    private const string AssistantVersion = "0.4.0";
    private static readonly string AppDirectory = AppDomain.CurrentDomain.BaseDirectory;
    private static readonly string LoaderPath = Path.Combine(AppDirectory, "Antigravity-CdpLocalizationLoader.exe");
    private static readonly string ExtensionDirectory = Path.Combine(AppDirectory, "localization-extension");
    private static readonly string DevToolsPortPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "Antigravity", "DevToolsActivePort");

    private sealed class MainForm : Form
    {
        private readonly Label appPathLabel;
        private readonly Label statusLabel;
        private readonly ProgressBar progress;
        private readonly Button chineseButton;
        private readonly Button englishButton;
        private readonly Button shortcutButton;
        private string antigravityPath;

        internal MainForm()
        {
            Text = "Antigravity 中文助手 " + AssistantVersion;
            Width = 620;
            Height = 360;
            MinimumSize = new Size(620, 360);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Microsoft YaHei UI", 9F);
            BackColor = Color.FromArgb(236, 241, 247);
            ForeColor = Color.FromArgb(31, 42, 55);
            AutoScaleMode = AutoScaleMode.Dpi;

            try
            {
                string detected = FindAntigravity();
                if (!string.IsNullOrEmpty(detected)) Icon = Icon.ExtractAssociatedIcon(detected);
            }
            catch { }

            var title = new Label
            {
                Text = "Antigravity 中文助手",
                Left = 28,
                Top = 24,
                Width = 540,
                Height = 34,
                Font = new Font("Microsoft YaHei UI", 17F, FontStyle.Bold)
            };
            var subtitle = new Label
            {
                Text = "外部动态汉化，不修改 app.asar、登录信息、会话或项目文件。",
                Left = 30,
                Top = 66,
                Width = 540,
                Height = 24,
                ForeColor = Color.FromArgb(82, 96, 112)
            };

            appPathLabel = new Label
            {
                Left = 30,
                Top = 104,
                Width = 540,
                Height = 42,
                AutoEllipsis = true,
                ForeColor = Color.FromArgb(62, 76, 92)
            };

            chineseButton = CreateButton("启动中文版", 30, 160, Color.FromArgb(50, 104, 168), Color.White);
            englishButton = CreateButton("恢复英文原版", 220, 160, Color.FromArgb(218, 226, 235), Color.FromArgb(31, 42, 55));
            shortcutButton = CreateButton("创建桌面入口", 410, 160, Color.FromArgb(218, 226, 235), Color.FromArgb(31, 42, 55));
            chineseButton.Click += delegate { BeginMode("zh"); };
            englishButton.Click += delegate { BeginMode("en"); };
            shortcutButton.Click += delegate { CreateDesktopShortcut(); };

            progress = new ProgressBar
            {
                Left = 30,
                Top = 224,
                Width = 540,
                Height = 12,
                Style = ProgressBarStyle.Blocks
            };
            statusLabel = new Label
            {
                Text = "准备就绪。启动或切换语言会重新打开 Antigravity，请先保存正在编辑的内容。",
                Left = 30,
                Top = 250,
                Width = 540,
                Height = 44,
                ForeColor = Color.FromArgb(82, 96, 112)
            };

            Controls.Add(title);
            Controls.Add(subtitle);
            Controls.Add(appPathLabel);
            Controls.Add(chineseButton);
            Controls.Add(englishButton);
            Controls.Add(shortcutButton);
            Controls.Add(progress);
            Controls.Add(statusLabel);

            Shown += delegate { RefreshDetection(); };
        }

        private static Button CreateButton(string text, int left, int top, Color backColor, Color foreColor)
        {
            return new Button
            {
                Text = text,
                Left = left,
                Top = top,
                Width = 160,
                Height = 42,
                FlatStyle = FlatStyle.Flat,
                BackColor = backColor,
                ForeColor = foreColor,
                Cursor = Cursors.Hand,
                UseVisualStyleBackColor = false
            };
        }

        private void RefreshDetection()
        {
            antigravityPath = FindAntigravity();
            bool found = !string.IsNullOrEmpty(antigravityPath);
            appPathLabel.Text = found ? "已找到：" + antigravityPath : "未找到 Antigravity。请先安装官方桌面客户端。";
            chineseButton.Enabled = found;
            englishButton.Enabled = found;
        }

        private void SetBusy(bool busy, string status)
        {
            chineseButton.Enabled = !busy && !string.IsNullOrEmpty(antigravityPath);
            englishButton.Enabled = !busy && !string.IsNullOrEmpty(antigravityPath);
            shortcutButton.Enabled = !busy;
            progress.Style = busy ? ProgressBarStyle.Marquee : ProgressBarStyle.Blocks;
            progress.MarqueeAnimationSpeed = busy ? 22 : 0;
            if (!busy) progress.Value = status.StartsWith("完成") ? 100 : 0;
            statusLabel.Text = status;
        }

        private bool ConfirmRestart()
        {
            if (Process.GetProcessesByName("Antigravity").Length == 0) return true;
            return MessageBox.Show(
                "切换语言需要关闭并重新打开 Antigravity。\n\n请确认正在编辑的内容已经保存。",
                "确认重新启动",
                MessageBoxButtons.OKCancel,
                MessageBoxIcon.Warning) == DialogResult.OK;
        }

        private void BeginMode(string mode)
        {
            if (!ConfirmRestart()) return;
            SetBusy(true, mode == "zh" ? "正在启动中文版并加载汉化…" : "正在恢复官方英文界面…");
            var worker = new Thread(delegate()
            {
                string result;
                bool success;
                try
                {
                    StopAntigravity();
                    DeleteStaleDevToolsPort();
                    if (mode == "zh")
                    {
                        ValidateLocalizationFiles();
                        StartAntigravity(antigravityPath, true);
                        int loaderExitCode = RunLoader();
                        success = loaderExitCode == 0;
                        result = success
                            ? "完成：中文版已启动。关闭助手不会影响已打开的 Antigravity。"
                            : "汉化注入失败。请关闭 Antigravity 后重试，或使用“恢复英文原版”。";
                    }
                    else
                    {
                        StartAntigravity(antigravityPath, false);
                        success = true;
                        result = "完成：已按官方英文模式启动，不加载汉化脚本。";
                    }
                }
                catch (Exception exception)
                {
                    success = false;
                    result = "失败：" + exception.Message;
                }
                BeginInvoke((MethodInvoker)delegate
                {
                    SetBusy(false, result);
                    if (!success) MessageBox.Show(result, "Antigravity 中文助手", MessageBoxButtons.OK, MessageBoxIcon.Error);
                });
            });
            worker.IsBackground = true;
            worker.Start();
        }

        private void CreateDesktopShortcut()
        {
            try
            {
                string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                string shortcutPath = Path.Combine(desktop, "Antigravity 中文助手.lnk");
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                dynamic shell = Activator.CreateInstance(shellType);
                dynamic shortcut = shell.CreateShortcut(shortcutPath);
                shortcut.TargetPath = Application.ExecutablePath;
                shortcut.WorkingDirectory = AppDirectory;
                shortcut.IconLocation = (!string.IsNullOrEmpty(antigravityPath) ? antigravityPath : Application.ExecutablePath) + ",0";
                shortcut.Description = "启动 Antigravity 中文助手";
                shortcut.Save();
                statusLabel.Text = "完成：桌面已创建“Antigravity 中文助手”入口。";
            }
            catch (Exception exception)
            {
                MessageBox.Show("创建桌面入口失败：" + exception.Message, "Antigravity 中文助手", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }

    private static string FindAntigravity()
    {
        string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        string programFilesX86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
        string[] candidates =
        {
            Path.Combine(localAppData, "Programs", "antigravity", "Antigravity.exe"),
            Path.Combine(localAppData, "Programs", "Antigravity", "Antigravity.exe"),
            Path.Combine(programFiles, "Antigravity", "Antigravity.exe"),
            Path.Combine(programFilesX86, "Antigravity", "Antigravity.exe")
        };
        return candidates.FirstOrDefault(File.Exists) ?? "";
    }

    private static void ValidateLocalizationFiles()
    {
        if (!File.Exists(LoaderPath)) throw new FileNotFoundException("汉化加载器缺失，请重新解压完整安装包。", LoaderPath);
        if (!File.Exists(Path.Combine(ExtensionDirectory, "translation-core.js")) ||
            !File.Exists(Path.Combine(ExtensionDirectory, "content.js")))
        {
            throw new FileNotFoundException("汉化词库文件缺失，请重新解压完整安装包。");
        }
    }

    private static void StopAntigravity()
    {
        Process[] processes = Process.GetProcessesByName("Antigravity");
        foreach (Process process in processes)
        {
            try { process.CloseMainWindow(); }
            catch { }
        }
        DateTime deadline = DateTime.UtcNow.AddSeconds(6);
        foreach (Process process in processes)
        {
            try
            {
                int remaining = Math.Max(0, (int)(deadline - DateTime.UtcNow).TotalMilliseconds);
                if (remaining > 0) process.WaitForExit(remaining);
                if (!process.HasExited) process.Kill();
            }
            catch { }
            finally { process.Dispose(); }
        }
        Thread.Sleep(500);
    }

    private static void DeleteStaleDevToolsPort()
    {
        try { if (File.Exists(DevToolsPortPath)) File.Delete(DevToolsPortPath); }
        catch { }
    }

    private static void StartAntigravity(string executable, bool chineseMode)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = executable,
            WorkingDirectory = Path.GetDirectoryName(executable),
            UseShellExecute = true
        };
        if (chineseMode)
        {
            startInfo.Arguments = "--remote-debugging-port=0 --remote-allow-origins=* --antigravity-localization-loader";
        }
        Process.Start(startInfo);
    }

    private static int RunLoader()
    {
        using (Process loader = Process.Start(new ProcessStartInfo
        {
            FileName = LoaderPath,
            WorkingDirectory = AppDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden
        }))
        {
            if (loader == null) throw new InvalidOperationException("Windows 无法启动汉化加载器。");
            if (!loader.WaitForExit(45000))
            {
                try { loader.Kill(); }
                catch { }
                throw new TimeoutException("等待 Antigravity 页面就绪超时。");
            }
            return loader.ExitCode;
        }
    }

    [STAThread]
    private static int Main(string[] args)
    {
        bool createdNew;
        using (var mutex = new Mutex(true, @"Local\AntigravityChineseAssistant", out createdNew))
        {
            if (!createdNew)
            {
                MessageBox.Show("Antigravity 中文助手已经打开。", "Antigravity 中文助手", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return 0;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
            return 0;
        }
    }
}
