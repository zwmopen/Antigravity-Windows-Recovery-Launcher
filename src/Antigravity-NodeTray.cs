using System;
using System.Diagnostics;
using System.IO;

namespace AntigravityNodeTray
{
    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string launcherExe = Path.Combine(baseDir, "Antigravity-Recovery-Launcher.exe");
                if (File.Exists(launcherExe))
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = launcherExe,
                        Arguments = "--show-panel",
                        WorkingDirectory = baseDir,
                        UseShellExecute = true
                    });
                }
            }
            catch { }
        }
    }
}
