import importlib.util
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "antigravity_smart_switch.py"


def load_module():
    temp_root = tempfile.mkdtemp(prefix="antigravity-priority-test-")
    os.environ["LOCALAPPDATA"] = temp_root
    os.environ["APPDATA"] = temp_root
    spec = importlib.util.spec_from_file_location("antigravity_smart_switch_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


module = load_module()

# 构造测试账号
# Case 1: 比较 即将到期账号 (3.1天，23%周额度) vs 刚刷新账号 (6.9天，99%周额度)
# 预期：即将到期的账号必须胜出，避免即将到期额度被清零浪费！
acc_near_expiry = {
    "id": "acc-near",
    "email": "near@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 23.0,
    "days_to_w_reset": 3.1,
    "cockpit_score": 283.6,
}

acc_fresh_high_quota = {
    "id": "acc-fresh",
    "email": "fresh@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 98.0,
    "gemini_weekly": 99.0,
    "days_to_w_reset": 6.9,
    "cockpit_score": 153.2,
}

acc_current = {
    "id": "acc-curr",
    "email": "curr@example.com",
    "disabled": False,
    "is_current": True,
    "gemini_5h": 10.0,
    "gemini_weekly": 50.0,
    "days_to_w_reset": 6.0,
    "cockpit_score": 100.0,
}

test_pool_1 = [acc_current, acc_near_expiry, acc_fresh_high_quota]
best_1, reason_1 = module.select_best_account(test_pool_1, "acc-curr")
assert best_1["id"] == "acc-near", f"Expected acc-near to win, got {best_1['id']}"
assert "优先消化即将到期额度" in reason_1
print("Test 1 PASS: 即将到期账号 (3.1天) 成功战胜 刚刷新高额度账号 (6.9天)")

# Case 2: 同时间梯队内比较 额度更多 (3.2天，80%额度) vs (3.0天，20%额度)
# 预期：在重置时间窗口几乎一致时，额度充沛者胜出
acc_same_tier_low = {
    "id": "acc-low",
    "email": "low@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 20.0,
    "days_to_w_reset": 3.0,
    "cockpit_score": 286.0,
}
acc_same_tier_high = {
    "id": "acc-high",
    "email": "high@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 80.0,
    "days_to_w_reset": 3.2,
    "cockpit_score": 324.0,
}

test_pool_2 = [acc_current, acc_same_tier_low, acc_same_tier_high]
best_2, reason_2 = module.select_best_account(test_pool_2, "acc-curr")
assert best_2["id"] == "acc-high", f"Expected acc-high to win, got {best_2['id']}"
print("Test 2 PASS: 相同重置窗口内，额度更高账号 (80%) 成功战胜低额度账号 (20%)")

# Case 3: 濒死账号 (<5%) 与 5h枯竭账号 (<=5%) 严禁切换
acc_dying = {
    "id": "acc-dying",
    "email": "dying@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 4.0,
    "days_to_w_reset": 1.0,
    "cockpit_score": -200.0,
}
test_pool_3 = [acc_current, acc_dying, acc_fresh_high_quota]
best_3, reason_3 = module.select_best_account(test_pool_3, "acc-curr")
assert best_3["id"] == "acc-fresh", f"Expected acc-fresh, got {best_3['id']}"
print("Test 3 PASS: 濒死账号 (<5%) 触发硬隔离，安全跳过并选取合法高分账号")

print("\nALL SMART SWITCH PRIORITY TESTS PASSED SUCCESSFULLY!")
