using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

internal static class AntigravityCdpLocalizationLoader
{
    private const int PollAttempts = 120;
    private static readonly string RuntimeRoot = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Antigravity");
    private static readonly string DevToolsPortPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "Antigravity", "DevToolsActivePort");
    private static readonly string ExtensionRoot = Path.Combine(
        AppDomain.CurrentDomain.BaseDirectory, "localization-extension");
    private static readonly string LoaderLogPath = Path.Combine(
        RuntimeRoot, "localization-loader.log");

    private static void Log(string eventName, string value)
    {
        try
        {
            Directory.CreateDirectory(RuntimeRoot);
            File.AppendAllText(
                LoaderLogPath,
                DateTime.Now.ToString("o") + " " + eventName + " " + value + Environment.NewLine);
        }
        catch { }
    }

    private static string LoadInjectionScript()
    {
        string corePath = Path.Combine(ExtensionRoot, "translation-core.js");
        string contentPath = Path.Combine(ExtensionRoot, "content.js");
        if (!File.Exists(corePath) || !File.Exists(contentPath))
        {
            throw new FileNotFoundException("localization_script_missing");
        }

        string script = File.ReadAllText(corePath, Encoding.UTF8) +
            Environment.NewLine + File.ReadAllText(contentPath, Encoding.UTF8);
        if (script.IndexOf("AntigravityZhCore", StringComparison.Ordinal) < 0 ||
            script.IndexOf("MutationObserver", StringComparison.Ordinal) < 0)
        {
            throw new InvalidDataException("localization_script_invalid");
        }
        return script;
    }

    private static string ReadDevToolsTarget()
    {
        if (!File.Exists(DevToolsPortPath)) return "";
        string[] lines = File.ReadAllLines(DevToolsPortPath);
        if (lines.Length == 0) return "";

        int port;
        if (!int.TryParse(lines[0].Trim(), out port) || port < 1 || port > 65535)
        {
            return "";
        }

        HttpWebRequest request = null;
        WebResponse response = null;
        StreamReader reader = null;
        try
        {
            request = (HttpWebRequest)WebRequest.Create(
                "http://127.0.0.1:" + port + "/json/list");
            request.Proxy = null;
            request.Timeout = 1500;
            request.ReadWriteTimeout = 1500;
            response = request.GetResponse();
            reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8);
            string json = reader.ReadToEnd();

            Match pageMatch = Regex.Match(
                json,
                "\\\"type\\\"\\s*:\\s*\\\"page\\\"[\\s\\S]*?\\\"webSocketDebuggerUrl\\\"\\s*:\\s*\\\"(ws:[^\\\"]+)\\\"",
                RegexOptions.IgnoreCase);
            if (!pageMatch.Success)
            {
                pageMatch = Regex.Match(
                    json,
                    "\\\"webSocketDebuggerUrl\\\"\\s*:\\s*\\\"(ws:[^\\\"]+)\\\"",
                    RegexOptions.IgnoreCase);
            }
            return pageMatch.Success ? pageMatch.Groups[1].Value : "";
        }
        finally
        {
            if (reader != null) reader.Dispose();
            if (response != null) response.Close();
        }
    }

    private static string WaitForDevToolsTarget()
    {
        for (int attempt = 0; attempt < PollAttempts; attempt++)
        {
            try
            {
                string target = ReadDevToolsTarget();
                if (!string.IsNullOrEmpty(target)) return target;
            }
            catch { }
            Thread.Sleep(250);
        }
        throw new InvalidOperationException("devtools_target_timeout");
    }

    private static string JsonQuote(string value)
    {
        StringBuilder builder = new StringBuilder(value.Length + 2);
        builder.Append('"');
        foreach (char character in value)
        {
            switch (character)
            {
                case '"': builder.Append("\\\""); break;
                case '\\': builder.Append("\\\\"); break;
                case '\b': builder.Append("\\b"); break;
                case '\f': builder.Append("\\f"); break;
                case '\n': builder.Append("\\n"); break;
                case '\r': builder.Append("\\r"); break;
                case '\t': builder.Append("\\t"); break;
                default:
                    if (character < 0x20)
                    {
                        builder.Append("\\u");
                        builder.Append(((int)character).ToString("x4"));
                    }
                    else
                    {
                        builder.Append(character);
                    }
                    break;
            }
        }
        builder.Append('"');
        return builder.ToString();
    }

    private sealed class CdpWebSocket : IDisposable
    {
        private readonly Uri endpoint;
        private TcpClient client;
        private NetworkStream stream;
        private int nextId = 1;

        public CdpWebSocket(string webSocketUrl)
        {
            endpoint = new Uri(webSocketUrl);
        }

        public void Connect()
        {
            client = new TcpClient();
            client.NoDelay = true;
            client.Connect(endpoint.Host, endpoint.Port);
            stream = client.GetStream();
            stream.ReadTimeout = 500;

            byte[] keyBytes = new byte[16];
            new Random().NextBytes(keyBytes);
            string key = Convert.ToBase64String(keyBytes);
            string request =
                "GET " + endpoint.PathAndQuery + " HTTP/1.1\r\n" +
                "Host: " + endpoint.Host + ":" + endpoint.Port + "\r\n" +
                "Upgrade: websocket\r\n" +
                "Connection: Upgrade\r\n" +
                "Sec-WebSocket-Key: " + key + "\r\n" +
                "Sec-WebSocket-Version: 13\r\n\r\n";
            byte[] requestBytes = Encoding.ASCII.GetBytes(request);
            stream.Write(requestBytes, 0, requestBytes.Length);

            string response = ReadHttpHeaders(DateTime.UtcNow.AddSeconds(5));
            if (response.IndexOf(" 101 ", StringComparison.OrdinalIgnoreCase) < 0)
            {
                throw new InvalidOperationException("websocket_handshake_failed");
            }
        }

        public void Call(string method, string parameters)
        {
            int id = nextId++;
            string command = "{\"id\":" + id +
                ",\"method\":" + JsonQuote(method) +
                ",\"params\":" + parameters + "}";
            SendText(command);

            DateTime deadline = DateTime.UtcNow.AddSeconds(10);
            while (DateTime.UtcNow < deadline)
            {
                string message = ReadTextMessage(deadline);
                if (string.IsNullOrEmpty(message)) continue;
                Match idMatch = Regex.Match(
                    message,
                    "\\\"id\\\"\\s*:\\s*" + id + "(?:\\s*,|\\s*})");
                if (!idMatch.Success) continue;
                if (Regex.IsMatch(message, "\\\"error\\\"\\s*:", RegexOptions.IgnoreCase))
                {
                    throw new InvalidOperationException("cdp_call_failed_" + method);
                }
                return;
            }
            throw new InvalidOperationException("cdp_call_timeout_" + method);
        }

        private string ReadHttpHeaders(DateTime deadline)
        {
            MemoryStream buffer = new MemoryStream();
            while (DateTime.UtcNow < deadline)
            {
                int value = ReadByte(deadline);
                if (value < 0) break;
                buffer.WriteByte((byte)value);
                byte[] bytes = buffer.ToArray();
                int length = bytes.Length;
                if (length >= 4 && bytes[length - 4] == 13 && bytes[length - 3] == 10 &&
                    bytes[length - 2] == 13 && bytes[length - 1] == 10)
                {
                    return Encoding.ASCII.GetString(bytes);
                }
            }
            throw new InvalidOperationException("websocket_headers_timeout");
        }

        private int ReadByte(DateTime deadline)
        {
            byte[] one = new byte[1];
            while (DateTime.UtcNow < deadline)
            {
                try
                {
                    int count = stream.Read(one, 0, 1);
                    if (count == 0) return -1;
                    return one[0];
                }
                catch (IOException) { }
            }
            return -1;
        }

        private byte[] ReadBytes(int length, DateTime deadline)
        {
            byte[] result = new byte[length];
            int offset = 0;
            while (offset < length && DateTime.UtcNow < deadline)
            {
                try
                {
                    int count = stream.Read(result, offset, length - offset);
                    if (count == 0) throw new EndOfStreamException();
                    offset += count;
                }
                catch (IOException) { }
            }
            if (offset != length) throw new InvalidOperationException("websocket_frame_timeout");
            return result;
        }

        private string ReadTextMessage(DateTime deadline)
        {
            MemoryStream message = new MemoryStream();
            bool started = false;
            while (DateTime.UtcNow < deadline)
            {
                int first = ReadByte(deadline);
                if (first < 0) return "";
                int second = ReadByte(deadline);
                if (second < 0) return "";
                bool final = (first & 0x80) != 0;
                int opcode = first & 0x0f;
                bool masked = (second & 0x80) != 0;
                ulong length = (ulong)(second & 0x7f);
                if (length == 126)
                {
                    byte[] size = ReadBytes(2, deadline);
                    length = (ulong)((size[0] << 8) | size[1]);
                }
                else if (length == 127)
                {
                    byte[] size = ReadBytes(8, deadline);
                    length = 0;
                    for (int i = 0; i < 8; i++) length = (length << 8) | size[i];
                }
                if (length > int.MaxValue) throw new InvalidOperationException("websocket_frame_too_large");

                byte[] mask = masked ? ReadBytes(4, deadline) : null;
                byte[] payload = ReadBytes((int)length, deadline);
                if (masked)
                {
                    for (int i = 0; i < payload.Length; i++) payload[i] = (byte)(payload[i] ^ mask[i % 4]);
                }

                if (opcode == 9)
                {
                    SendFrame(10, payload);
                    continue;
                }
                if (opcode == 8) return "";
                if (opcode == 1 || (opcode == 0 && started))
                {
                    started = true;
                    message.Write(payload, 0, payload.Length);
                    if (final) return Encoding.UTF8.GetString(message.ToArray());
                }
            }
            return "";
        }

        private void SendText(string text)
        {
            SendFrame(1, Encoding.UTF8.GetBytes(text));
        }

        private void SendFrame(int opcode, byte[] payload)
        {
            MemoryStream frame = new MemoryStream();
            frame.WriteByte((byte)(0x80 | (opcode & 0x0f)));
            if (payload.Length <= 125)
            {
                frame.WriteByte((byte)(0x80 | payload.Length));
            }
            else if (payload.Length <= 65535)
            {
                frame.WriteByte(0xFE);
                frame.WriteByte((byte)((payload.Length >> 8) & 0xFF));
                frame.WriteByte((byte)(payload.Length & 0xFF));
            }
            else
            {
                frame.WriteByte(0xFF);
                long length = payload.Length;
                for (int shift = 56; shift >= 0; shift -= 8) frame.WriteByte((byte)(length >> shift));
            }

            byte[] mask = new byte[4];
            new Random().NextBytes(mask);
            frame.Write(mask, 0, mask.Length);
            for (int i = 0; i < payload.Length; i++) frame.WriteByte((byte)(payload[i] ^ mask[i % 4]));
            byte[] bytes = frame.ToArray();
            stream.Write(bytes, 0, bytes.Length);
        }

        public void Dispose()
        {
            if (stream != null) stream.Close();
            if (client != null) client.Close();
        }
    }

    private static int Main()
    {
        try
        {
            string script = LoadInjectionScript();
            string target = WaitForDevToolsTarget();
            using (CdpWebSocket socket = new CdpWebSocket(target))
            {
                socket.Connect();
                socket.Call("Page.addScriptToEvaluateOnNewDocument", "{\"source\":" + JsonQuote(script) + "}");
                socket.Call("Runtime.evaluate", "{\"expression\":" + JsonQuote(script) + "}");
            }
            Log("injection_succeeded", "version=0.4.0");
            return 0;
        }
        catch (Exception exception)
        {
            Log("injection_failed", "type=" + exception.GetType().Name);
            return 1;
        }
    }
}
