"""Read the running editor language service identity; never read Cockpit credentials."""
import json
import os
import re
import ssl
import time
import urllib.request
from datetime import datetime, timezone

try:
    import psutil
except ImportError:
    psutil = None

EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+\Z")


def read_identity(budget=2.5):
    if psutil is None:
        return {"status": "unavailable", "reason": "process_reader_missing"}
    deadline = time.monotonic() + budget
    official = os.path.normcase(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "antigravity", "Antigravity.exe"))
    # Certificate verification is disabled only for a loopback listener owned
    # by the running editor's own language service, never a remote host.
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
    identities = []
    for process in psutil.process_iter(["pid", "name"]):
        if time.monotonic() >= deadline:
            break
        if "language_server" not in (process.info.get("name") or "").lower():
            continue
        try:
            parent = process.parent()
            if not parent or os.path.normcase(parent.exe()) != official:
                continue
            created = process.create_time()
            args = process.cmdline() or []
            csrf = ""
            for index, arg in enumerate(args):
                if arg == "--csrf_token" and index + 1 < len(args):
                    csrf = args[index + 1]
                elif arg.startswith("--csrf_token="):
                    csrf = arg.split("=", 1)[1]
            if not csrf:
                continue
            ports = sorted({connection.laddr.port for connection in process.net_connections(kind="tcp") if connection.status == "LISTEN"})
            for port in ports:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    request = urllib.request.Request(
                        f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/GetUserStatus",
                        data=b"{}", method="POST", headers={"Content-Type": "application/json", "Connect-Protocol-Version": "1", "X-Codeium-Csrf-Token": csrf})
                    with client.open(request, timeout=min(0.6, remaining)) as response:
                        payload = json.loads(response.read(1024 * 1024))
                    email = payload.get("userStatus", {}).get("email", "")
                    if not isinstance(email, str) or len(email) > 254 or not EMAIL.fullmatch(email):
                        continue
                    if not process.is_running() or process.create_time() != created:
                        continue
                    identities.append({"email": email, "editor_pid": parent.pid, "language_server_pid": process.pid})
                    break
                except Exception:
                    continue
        except Exception:
            continue
    if not identities:
        return {"status": "unavailable", "reason": "live_identity_not_readable"}
    if len({item["email"].lower() for item in identities}) > 1:
        return {"status": "unavailable", "reason": "multiple_runtime_identities"}
    return dict(identities[0], status="live", source="language_server.GetUserStatus", observed_at=datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    print(json.dumps(read_identity(), ensure_ascii=True))
