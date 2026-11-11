import importlib.util
import io
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("identity", Path(__file__).parents[1] / "src/antigravity_runtime_identity.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
OFFICIAL = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "antigravity", "Antigravity.exe")

class Process:
    pid = 42
    info = {"name": "language_server.exe"}
    def __init__(self, parent_path=OFFICIAL, alive=True):
        self.parent_path, self.alive = parent_path, alive
    def parent(self): return SimpleNamespace(exe=lambda: self.parent_path, pid=7)
    def create_time(self): return 100
    def cmdline(self): return ["language_server.exe", "--csrf_token", "test-only"]
    def net_connections(self, kind): return [SimpleNamespace(status="LISTEN", laddr=SimpleNamespace(port=12345))]
    def is_running(self): return self.alive

class IdentityTests(unittest.TestCase):
    def read(self, processes, payloads):
        client = SimpleNamespace(open=lambda req, timeout: io.BytesIO(json.dumps(next(payloads)).encode()))
        with patch.object(m, "STATUS_FILE", str(Path(__file__).parent / "__nonexistent_launch_account_status__.json")), patch.object(m, "psutil", SimpleNamespace(process_iter=lambda attrs: processes)), patch.object(m.urllib.request, "build_opener", return_value=client):
            return m.read_identity()
    def test_reads_live_service_not_cockpit(self):
        result=self.read([Process()], iter([{"userStatus":{"email":"live@example.com","accessToken":"never-output"}}]))
        self.assertEqual(result["email"],"live@example.com")
        self.assertEqual(result["source"],"language_server.GetUserStatus")
        self.assertNotIn("never-output",json.dumps(result))
    def test_foreign_parent_is_rejected(self):
        self.assertEqual(self.read([Process("other.exe")],iter([]))["status"],"unavailable")
    def test_conflicting_sessions_are_not_guessed(self):
        self.assertEqual(self.read([Process(),Process()],iter([{"userStatus":{"email":"a@example.com"}},{"userStatus":{"email":"b@example.com"}}]))["reason"],"multiple_runtime_identities")
    def test_dead_service_is_not_current(self):
        self.assertEqual(self.read([Process(alive=False)],iter([{"userStatus":{"email":"a@example.com"}}]))["status"],"unavailable")
    def test_missing_identity_does_not_fall_back_to_cockpit(self):
        self.assertEqual(self.read([Process()],iter([{"userStatus":{}}]))["status"],"unavailable")

if __name__ == "__main__": unittest.main()
