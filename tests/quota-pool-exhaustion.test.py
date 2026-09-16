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
orig_select_best = module.select_best_account
module.select_best_account = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("不得进入选号"))
result = module.run_smart_switch(threshold=5.0, force=True)
assert result == "quota_pool_exhausted"
module.select_best_account = orig_select_best

# =========================================================================
# 新增测试：并行淘汰门禁（周额度 <= 1.0% 或 5h <= 5.0% 均一票否决淘汰）
# =========================================================================
# 场景 1：备选账号 A 周额度仅 0.2% (残血被拒)，备选账号 B 5h 仅 3.0% (低电被拒)
# 当前账号 5h 耗尽 (2.0%)，此时账号池无任何可用备选，坚决严禁切号与重启！
parallel_exhausted_pool = [
    account("current", 80.0, five_hour=2.0, current=True),
    account("backup-a", 0.2, five_hour=100.0),   # 周额度 <= 1.0% 淘汰
    account("backup-b", 80.0, five_hour=3.0),    # 5h 额度 <= 5.0% 淘汰
]

# 必须断言判定为账号池耗尽
assert module.guard_quota_pool_exhaustion(parallel_exhausted_pool) is True

# select_best_account 必须彻底抛出 RuntimeError，严禁 fallback 盲选残血账号！
try:
    module.select_best_account(parallel_exhausted_pool, current_id="current", threshold=5.0)
    assert False, "select_best_account 必须抛出 RuntimeError，严禁 fallback！"
except RuntimeError as re:
    assert (
        "当前所有备选账号的 5小时或周额度均已耗尽" in str(re)
        or "全池备选账号周额度均已低于 5.0%" in str(re)
    )

# 场景 2：存在真正合格满血备选账号 (周额度 50.0% > 1.0 且 5h 90.0% > 5.0)
healthy_pool = [
    account("current", 80.0, five_hour=2.0, current=True),
    account("backup-a", 0.2, five_hour=100.0),   # 淘汰
    account("backup-b", 50.0, five_hour=90.0),   # 合格优选！
]
assert module.guard_quota_pool_exhaustion(healthy_pool) is False
best, reason = module.select_best_account(healthy_pool, current_id="current", threshold=5.0)
assert best["id"] == "backup-b"
assert "智能优选" in reason

print("quota_pool_exhaustion_ok")
