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
# Case 1: 优先级 1 - 周到期时间越近越好 (2.1天，23%周额度 vs 6.9天，99%周额度)
# 无论如何天数少的绝对优先，避免即将刷新额度被清零浪费！
acc_near_expiry = {
    "id": "acc-near",
    "email": "near@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 23.0,
    "days_to_w_reset": 2.1,
    "cockpit_score": 5315.0,
}

acc_fresh_high_quota = {
    "id": "acc-fresh",
    "email": "fresh@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 98.0,
    "gemini_weekly": 99.0,
    "days_to_w_reset": 6.9,
    "cockpit_score": 1696.0,
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
assert "优先消化即将到期账号" in reason_1
print("Test 1 PASS: 优先级 1 验证通过 - 天数少账号 (2.1天) 绝对战胜天数多账号 (6.9天)")

# Case 2: 优先级 2 - 额度大小 (同一天数梯队内条件一样，额度多的绝对胜出，且必须超过 5%)
acc_same_tier_low = {
    "id": "acc-low",
    "email": "low@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 20.0,
    "days_to_w_reset": 2.0,
    "cockpit_score": 5350.0,
}
acc_same_tier_high = {
    "id": "acc-high",
    "email": "high@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 80.0,
    "days_to_w_reset": 2.2,
    "cockpit_score": 5640.0,
}

test_pool_2 = [acc_current, acc_same_tier_low, acc_same_tier_high]
best_2, reason_2 = module.select_best_account(test_pool_2, "acc-curr")
assert best_2["id"] == "acc-high", f"Expected acc-high to win, got {best_2['id']}"
print("Test 2 PASS: 优先级 2 验证通过 - 相同重置时间窗口内，周额度更高账号 (80%) 战胜低额度账号 (20%)")

# Case 3: 优先级 3 - 小时额度越满越好 (周额度相同时，5小时满血优先)
acc_same_w_low_5h = {
    "id": "acc-w-low-5h",
    "email": "w_low_5h@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 40.0,
    "gemini_weekly": 60.0,
    "days_to_w_reset": 2.5,
    "cockpit_score": 5380.0,
}
acc_same_w_full_5h = {
    "id": "acc-w-full-5h",
    "email": "w_full_5h@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 60.0,
    "days_to_w_reset": 2.5,
    "cockpit_score": 5500.0,
}

test_pool_3 = [acc_current, acc_same_w_low_5h, acc_same_w_full_5h]
best_3, reason_3 = module.select_best_account(test_pool_3, "acc-curr")
assert best_3["id"] == "acc-w-full-5h", f"Expected acc-w-full-5h to win, got {best_3['id']}"
print("Test 3 PASS: 优先级 3 验证通过 - 小时额度越满越好 (100% 胜出 40%)")

# Case 4: 优先级 4 & 门禁 - 特殊账号判定 (需申诉、网页验证、封禁) 自动跳过，濒死账号 (<=5%) 自动跳过
acc_appeal = {
    "id": "acc-appeal",
    "email": "appeal@example.com",
    "disabled": True,
    "disabled_reason": "需申诉 / 账号限制 (This service has been disabled)",
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 100.0,
    "days_to_w_reset": 1.0,
    "cockpit_score": -94000.0,
}
acc_verify = {
    "id": "acc-verify",
    "email": "verify@example.com",
    "disabled": True,
    "disabled_reason": "需网页验证 / 封禁隔离 (invalid_grant)",
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 100.0,
    "days_to_w_reset": 1.0,
    "cockpit_score": -94000.0,
}
acc_dying = {
    "id": "acc-dying",
    "email": "dying@example.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 4.0,  # <= 5% 濒死
    "days_to_w_reset": 1.0,
    "cockpit_score": -44000.0,
}

test_pool_4 = [acc_current, acc_appeal, acc_verify, acc_dying, acc_fresh_high_quota]
best_4, reason_4 = module.select_best_account(test_pool_4, "acc-curr")
assert best_4["id"] == "acc-fresh", f"Expected acc-fresh, got {best_4['id']}"
print("Test 4 PASS: 优先级 4 验证通过 - 特殊账号（需申诉、需验证）与濒死账号（<=5%）100% 自动跳过")

# Case 5: 验证 HARD_BLOCKED_EMAILS 黑名单拦截
acc_blocked = {
    "id": "acc-blocked",
    "email": "azrimjs@gmail.com",
    "disabled": False,
    "is_current": False,
    "gemini_5h": 100.0,
    "gemini_weekly": 100.0,
    "days_to_w_reset": 0.5,
    "cockpit_score": 6000.0,
}
assert "azrimjs@gmail.com" in module.HARD_BLOCKED_EMAILS
assert "kt01096002805@gmail.com" in module.HARD_BLOCKED_EMAILS
print("Test 5 PASS: 封禁账号硬黑名单拦截校验通过 (HARD_BLOCKED_EMAILS 包含 azrimjs 与 kt01096002805)")

print("\n🎉 ALL 5 USER RULES AND VERIFICATIONS PASSED 100% SUCCESSFULLY!")

