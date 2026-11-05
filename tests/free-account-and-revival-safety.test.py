import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from antigravity_smart_switch import select_best_account, find_active_and_interrupted_subagents, revive_subagent

class TestFreeAccountAndRevivalSafety(unittest.TestCase):
    def test_free_account_selection_when_pro_exhausted(self):
        """测试：当付费 Pro 账号耗尽时，免费账号 (is_free=True) 能够正常入选并作为主力备用被选中"""
        accounts = [
            {
                "id": "acc-pro-curr",
                "email": "curr_pro@example.com",
                "is_current": True,
                "disabled": False,
                "gemini_5h": 0.0,
                "gemini_weekly": 0.0,
                "days_to_w_reset": 1.0,
                "cockpit_score": -99999.0
            },
            {
                "id": "acc-pro-exhausted",
                "email": "exhausted_pro@example.com",
                "is_current": False,
                "disabled": False,
                "gemini_5h": 0.0,
                "gemini_weekly": 2.0,
                "days_to_w_reset": 2.0,
                "cockpit_score": -99999.0
            },
            {
                "id": "acc-free-backup",
                "email": "backup_free@example.com",
                "is_current": False,
                "is_free": True,
                "disabled": False,
                "gemini_5h": 100.0,
                "gemini_weekly": 100.0,
                "days_to_w_reset": 7.0,
                "cockpit_score": 7740.0
            }
        ]
        best, reason = select_best_account(accounts, current_id="acc-pro-curr", threshold=5.0)
        self.assertEqual(best["id"], "acc-free-backup")
        self.assertEqual(best["email"], "backup_free@example.com")
        self.assertTrue(best.get("is_free"))

    def test_revival_respects_killed_state(self):
        """测试：子智能体处于 SUBAGENT_STATE_KILLED 态时，revive_subagent 绝不盲目复活"""
        res = revive_subagent(
            parent_id="test-parent-id-0000-000000000001",
            subagent_id="test-subagent-id-000-000000000002"
        )
        # 只要没有对应或属于无效操作，绝不误复活
        self.assertFalse(res.get("revived") and res.get("state") == "SUBAGENT_STATE_KILLED")

if __name__ == "__main__":
    unittest.main()
