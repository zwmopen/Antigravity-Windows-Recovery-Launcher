"""Execute quota-log identity routing without live credentials or network."""
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TMP = tempfile.TemporaryDirectory(prefix="quota-identity-test-")
for name in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
    os.environ[name] = TMP.name
spec = importlib.util.spec_from_file_location("switch_identity_test", ROOT / "src" / "antigravity_smart_switch.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class QuotaLogIdentityTests(unittest.TestCase):
    def setUp(self):
        stamp = datetime.now().replace(microsecond=0)
        target = stamp.astimezone(timezone.utc) + timedelta(hours=1)
        self.current = {"id":"current", "email":"current@example.com", "is_current":True,
                        "gemini_5h":100.0, "gemini_weekly":80.0,
                        "reset_time_5h":target + timedelta(hours=3), "reset_time_weekly":None}
        self.old = {"id":"old", "email":"old@example.com", "is_current":False,
                    "gemini_5h":0.0, "gemini_weekly":0.0,
                    "reset_time_5h":target, "reset_time_weekly":None}
        m.LANGUAGE_SERVER_LOG = str(Path(TMP.name) / "language_server.log")
        Path(m.LANGUAGE_SERVER_LOG).write_text("prefix\n" + stamp.strftime("E%m%d %H:%M:%S") + " RESOURCE_EXHAUSTED HTTP 429 Resets in 1h0m0s.\n")
        m._last_language_log_pos = len("prefix\n")
        m._last_switch_time = 0
        self.patches = [
            patch.object(m, "get_all_accounts_and_quotas", return_value=("current", [self.current, self.old])),
            patch.object(m, "decrypt_cockpit_account", side_effect=lambda aid: {"token":{"refresh_token":aid+"-test-token"}}),
            patch.object(m, "get_current_windows_credential_token", return_value={"refresh_token":"current-test-token"}),
            patch.object(m, "record_quarantine_account"), patch.object(m, "record_incident"),
            patch.object(m, "notify_frontend_auth_state_update", return_value={"success":True}),
            patch.object(m, "hot_restart_language_server"),
        ]
        self.mocks = [p.start() for p in self.patches]
    def tearDown(self):
        for p in reversed(self.patches): p.stop()
    def test_old_error_with_confirmed_current_credentials_does_not_force_switch(self):
        self.assertFalse(m.check_language_server_quota_error())
        self.mocks[-2].assert_called_once()
        self.mocks[-1].assert_not_called()
    def test_old_error_failed_notification_does_not_restart_editor_or_rotate_healthy_pool(self):
        self.mocks[-2].return_value = {"success":False,"reason":"test"}
        self.assertFalse(m.check_language_server_quota_error())
        self.mocks[-1].assert_not_called()
    def test_old_credential_still_installed_requires_real_recovery(self):
        self.mocks[2].return_value = {"refresh_token":"old-test-token"}
        self.assertTrue(m.check_language_server_quota_error())
    def test_unknown_windows_identity_is_not_silently_ignored(self):
        self.mocks[2].return_value = None
        self.assertTrue(m.check_language_server_quota_error())
    def test_shared_reset_window_does_not_misattribute_current_quota_to_old_identity(self):
        self.current["reset_time_5h"] = self.old["reset_time_5h"]
        self.assertTrue(m.check_language_server_quota_error())
        self.mocks[-2].assert_not_called()
    def test_no_error_does_not_switch(self):
        Path(m.LANGUAGE_SERVER_LOG).write_text("prefix\nno errors\n")
        self.assertFalse(m.check_language_server_quota_error())

if __name__ == "__main__":
    result = unittest.main(exit=False).result
    for handler in list(m.logger.handlers):
        handler.close()
        m.logger.removeHandler(handler)
    TMP.cleanup()
    sys.exit(not result.wasSuccessful())
