import importlib.util
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "antigravity_smart_switch.py"


def load_module():
    temp_root = tempfile.mkdtemp(prefix="antigravity-quota-test-")
    os.environ["LOCALAPPDATA"] = temp_root
    os.environ["APPDATA"] = temp_root
    spec = importlib.util.spec_from_file_location("antigravity_smart_switch_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.QUOTA_POOL_STATE_FILE = os.path.join(temp_root, "quota-pool-state.json")
    return module


def account(account_id, weekly, five_hour=100.0, *, current=False, disabled=False):
    return {
        "id": account_id,
        "email": f"{account_id}@example.test",
        "disabled": disabled,
        "is_current": current,
        "gemini_5h": five_hour,
        "gemini_weekly": weekly,
        "effective_quota": 0.0 if weekly <= 0.0 else five_hour,
        "reset_time_weekly": None,
    }


module = load_module()
notifications = []
incidents = []
module.send_windows_notification = lambda title, message, **kwargs: notifications.append((title, message)) or True
module.record_incident = lambda **kwargs: incidents.append(kwargs)

all_exhausted = [
    account("current", 0.0, current=True),
    account("backup-a", 0.0),
    account("backup-b", 0.0),
    account("disabled", 80.0, disabled=True),
]

assert module.guard_quota_pool_exhaustion(all_exhausted) is True
assert len(notifications) == 1
assert "全部" in notifications[0][1] and "停止自动切号" in notifications[0][1]
assert len(incidents) == 1

# 持续耗尽时不得每轮重复弹窗或重复写故障事件。
assert module.guard_quota_pool_exhaustion(all_exhausted) is True
assert len(notifications) == 1
assert len(incidents) == 1

# 任一启用账号周额度恢复后解除耗尽状态；下次再次耗尽可重新通知。
recovered = [account("current", 0.0, current=True), account("backup-a", 25.0)]
assert module.guard_quota_pool_exhaustion(recovered) is False
assert module.guard_quota_pool_exhaustion(all_exhausted) is True
assert len(notifications) == 2

# run_smart_switch 必须在选号、写凭据、关窗口之前短路退出。
module.get_all_accounts_and_quotas = lambda: ("current", all_exhausted)
module.get_subscription_summary = lambda: "test"
module.select_best_account = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("不得进入选号"))
result = module.run_smart_switch(threshold=5.0, force=True)
assert result == "quota_pool_exhausted"

print("quota_pool_exhaustion_ok")
