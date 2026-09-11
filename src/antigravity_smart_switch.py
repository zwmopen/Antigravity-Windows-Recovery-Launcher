# -*- coding: utf-8 -*-
"""
Antigravity Smart Account Switcher & Smooth Launcher
=====================================================
Cockpit Tools 智能切号规则 (Cockpit Rules):
1. 触发条件：
   当前账号有效额度 <= 5.0% 立即触发切号。
2. 优先级排序：
   (a) 优先 5 小时满血活动：5小时额度越充沛越优先，满血 (>=95%) 账号具有最高基础优先级；
   (b) 优先周恢复时间：周重置时间越短越优先（如 1~2 天优先于 5~6 天），优先消耗即将过期的周存量；
   (c) 综合判定：在“5小时满额”前提下，优先选择“周重置即将到来”且“周额度有足够冗余”的账号。
3. 严格门禁：
   - 排除当前在用账号、已禁用账号；
   - 若周额度耗尽 (<=5%)，5小时额度必然不可用，直接一票否决淘汰；
   - 若 5 小时额度耗尽 (<=5%)，直接一票否决淘汰。
4. 全流程闭环：
   优雅退出 Antigravity -> 挑选最优账号 -> Cockpit 静默写凭据 -> 专线启动器恢复置顶。
"""

import os
import sys
import re
import time
import json
import asyncio
import logging
import argparse
import subprocess
import base64
import ctypes
import urllib.request
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import psutil
except ImportError:
    psutil = None

try:
    import websockets
except ImportError:
    websockets = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("AntigravitySmartSwitch")

USER_PROFILE = os.environ.get("USERPROFILE", os.path.expanduser("~"))
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.join(USER_PROFILE, "AppData", "Local"))
ROAMING_APPDATA = os.environ.get("APPDATA", os.path.join(USER_PROFILE, "AppData", "Roaming"))
COCKPIT_DIR = os.path.join(USER_PROFILE, ".antigravity_cockpit")
ACCOUNTS_FILE = os.path.join(COCKPIT_DIR, "accounts.json")
SERVER_FILE = os.path.join(COCKPIT_DIR, "server.json")
QUOTA_CACHE_DIR = os.path.join(COCKPIT_DIR, "cache", "quota_api_v1_desktop", "authorized")
DAEMON_LOG_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "smart-quota-watcher.log")
PENDING_SWITCH_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "pending-switch.json")
PENDING_AUTO_RESUME_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "pending-auto-resume.json")
SUBSCRIPTION_REPORT_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "subscription-report.json")
DEVTOOLS_PORT_FILE = os.path.join(ROAMING_APPDATA, "Antigravity", "DevToolsActivePort")
LANGUAGE_SERVER_LOG = os.path.join(ROAMING_APPDATA, "Antigravity", "logs", "language_server.log")
WATCHER_CURRENT_ACCOUNT_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "watcher-current-account.txt")
INCIDENT_REPORT_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "incident-report.json")
INCIDENT_HISTORY_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "incident-history.json")
AUTO_RESUME_LOCK_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "auto-resume.lock")
QUARANTINE_ACCOUNTS_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "quarantined-accounts.json")
QUOTA_POOL_STATE_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "quota-pool-state.json")
SHARED_NOTIFY_SCRIPT = r"D:\AICode\AI\skills\技能包\技能\shared-notification\scripts\shared_notify.py"
FEISHU_CONFIG_FILE = r"D:\AICode\AI\secrets\平台服务\飞书\feishu_config.json"


class AutoResumeLock:
    """跨进程排他互斥锁，确保任何时刻全局只有一个 CDP 自动续接进程在运行，杜绝并发踩踏"""
    def __init__(self, lock_file=AUTO_RESUME_LOCK_FILE):
        self.lock_file = lock_file
        self.handle = None

    def acquire(self):
        try:
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
            self.handle = open(self.lock_file, "a+")
            if sys.platform == "win32":
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except (IOError, OSError):
            if self.handle:
                try:
                    self.handle.close()
                except Exception:
                    pass
                self.handle = None
            return False

    def release(self):
        if self.handle:
            try:
                if sys.platform == "win32":
                    import msvcrt
                    self.handle.seek(0)
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
            try:
                self.handle.close()
            except Exception:
                pass
            self.handle = None


def load_quarantined_accounts():
    """读取因 429 被临时关押的账号列表 { account_id: expire_timestamp }"""
    if not os.path.exists(QUARANTINE_ACCOUNTS_FILE):
        return {}
    try:
        with open(QUARANTINE_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        # 清理已过期的关押记录
        active_q = {k: v for k, v in data.items() if v > now}
        return active_q
    except Exception:
        return {}


def record_quarantine_account(account_id, duration_seconds=9000):
    """将触发 429 报错的账号加入临时关押名单，避免短时间内再次被优选"""
    try:
        data = load_quarantined_accounts()
        expire_at = time.time() + duration_seconds
        data[account_id] = expire_at
        os.makedirs(os.path.dirname(QUARANTINE_ACCOUNTS_FILE), exist_ok=True)
        with open(QUARANTINE_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"🚫 已将账号 {account_id} 加入 429 临时关押名单，持续 {int(duration_seconds // 60)} 分钟 (至 {datetime.fromtimestamp(expire_at).strftime('%H:%M:%S')})")
    except Exception as e:
        logger.debug(f"记录关押账号异常: {e}")


def remove_quarantined_account(account_id):
    """当用户在 Cockpit 手动选择或人工介入时，解除对应账号的关押状态"""
    try:
        data = load_quarantined_accounts()
        if account_id in data:
            del data[account_id]
            with open(QUARANTINE_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"🔓 已解除账号 {account_id} 的 429 临时关押状态")
    except Exception as e:
        logger.debug(f"解除关押账号异常: {e}")


# 全局文件日志：确保无论 CLI 测试、脚本调用还是后台守护，日志均可落盘
try:
    os.makedirs(os.path.dirname(DAEMON_LOG_FILE), exist_ok=True)
    _shared_file_handler = RotatingFileHandler(DAEMON_LOG_FILE, maxBytes=1024 * 1024, backupCount=2, encoding="utf-8")
    _shared_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(_shared_file_handler)
except Exception:
    pass

LAUNCHER_EXE = os.path.join(LOCAL_APPDATA, "Antigravity", "launcher", "Antigravity-Recovery-Launcher.exe")
ACCOUNT_WATCHER_EXE = os.path.join(LOCAL_APPDATA, "Antigravity", "launcher", "Antigravity-AccountWatcher.exe")
DESKTOP_LNK = os.path.join(USER_PROFILE, "Desktop", "Antigravity 启动器.lnk")


def record_incident(incident_type, severity, summary, root_cause, action_taken, evidence=None, recommended_action="系统正在/已完成自动自愈，无需手动干预。"):
    """记录极其详细的结构化故障现场快照 (Incident Report)，实现毫秒级全链路自诊与高透明度"""
    try:
        os.makedirs(os.path.dirname(INCIDENT_REPORT_FILE), exist_ok=True)
        now_dt = datetime.now()
        now_iso = now_dt.astimezone().isoformat()
        incident_id = f"INC-{now_dt.strftime('%Y%m%d-%H%M%S')}"
        record = {
            "incident_id": incident_id,
            "timestamp": now_iso,
            "incident_type": incident_type,
            "severity": severity,
            "source": "AntigravitySmartSwitch",
            "summary": summary,
            "root_cause": root_cause,
            "evidence": evidence or {},
            "action_taken": action_taken,
            "recommended_action": recommended_action
        }
        
        # 1. 历史故障列表 (最多保留 30 条)
        history = []
        if os.path.exists(INCIDENT_HISTORY_FILE):
            try:
                with open(INCIDENT_HISTORY_FILE, "r", encoding="utf-8-sig") as hf:
                    history = json.load(hf)
                if not isinstance(history, list):
                    history = []
            except Exception:
                history = []
        history.insert(0, record)
        history = history[:30]
        try:
            with open(INCIDENT_HISTORY_FILE, "w", encoding="utf-8") as hf:
                json.dump(history, hf, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # 2. 当前最新故障现场快照 (原子写入)
        temp_file = INCIDENT_REPORT_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        if os.path.exists(INCIDENT_REPORT_FILE):
            try:
                os.remove(INCIDENT_REPORT_FILE)
            except Exception:
                pass
        os.rename(temp_file, INCIDENT_REPORT_FILE)
        
        logger.warning(f"📋 【现场故障诊断快照已生成】 [{severity}] {summary} (ID: {incident_id})")
        logger.warning(f"   * 根因诊断: {root_cause}")
        logger.warning(f"   * 已执行动作: {action_taken}")
        logger.warning(f"   * 后续指引: {recommended_action}")
    except Exception as e:
        logger.debug(f"记录故障快照异常: {e}")


def print_incident_report():
    """打印最近一次系统故障现场诊断报告"""
    if not os.path.exists(INCIDENT_REPORT_FILE):
        print("\n✅ 系统当前无任何已归档的故障快照 (未发生异常崩溃或配额熔断)。\n")
        return
    try:
        with open(INCIDENT_REPORT_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        print("\n" + "=" * 80)
        print("【Antigravity 故障现场智能自诊快照 (Incident Report)】")
        print("=" * 80)
        print(f"事件 ID   : {data.get('incident_id')}")
        print(f"发生时间  : {data.get('timestamp')}")
        print(f"严重级别  : [{data.get('severity')}] - {data.get('incident_type')}")
        print(f"事件摘要  : {data.get('summary')}")
        print(f"根因诊断  : {data.get('root_cause')}")
        print(f"已执行动作: {data.get('action_taken')}")
        print(f"后续指引  : {data.get('recommended_action')}")
        evidence = data.get('evidence')
        if evidence:
            print("现场证据  :")
            for k, v in evidence.items():
                print(f"   - {k}: {v}")
        print("=" * 80 + "\n")
    except Exception as e:
        print(f"读取故障报告异常: {e}")


def parse_iso_datetime(ts_str):
    if not ts_str:
        return None
    try:
        if ts_str.endswith("Z"):
            return datetime.fromisoformat(ts_str[:-1]).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def get_subscription_summary():
    """读取本地订阅与专线候选节点健康状态摘要"""
    if not os.path.exists(SUBSCRIPTION_REPORT_FILE):
        return "本地订阅已就绪 (首次启动将自动校验节点健康度)"
    try:
        with open(SUBSCRIPTION_REPORT_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        total_cnt = data.get("candidate_count", 0)
        jp_cnt = data.get("japan_candidate_count", 0)
        us_cnt = data.get("united_states_candidate_count", 0)
        sources = data.get("sources", [])
        src_parts = []
        for s in sources:
            name = s.get("source", "")
            cnt = s.get("candidate_count", 0)
            src_parts.append(f"{name}({cnt}线)")
        details = ", ".join(src_parts) if src_parts else "就绪"
        return f"已加载 {total_cnt} 条专线候选 (美:{us_cnt}线, 日:{jp_cnt}线) | 订阅源: {details}"
    except Exception:
        return "本地订阅节点已就绪"


def write_pending_switch(target_account):
    """记录切号待办事务，确保断电或重启后可自愈闭环"""
    try:
        os.makedirs(os.path.dirname(PENDING_SWITCH_FILE), exist_ok=True)
        with open(PENDING_SWITCH_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "target_account_id": target_account["id"],
                "target_email": target_account["email"],
                "status": "switching",
                "timestamp": time.time(),
                "created_at": datetime.now().isoformat()
            }, f, indent=2)
    except Exception as e:
        logger.warning(f"写入待切换事务文件异常: {e}")


def clear_pending_switch():
    """清除切号待办事务"""
    try:
        if os.path.exists(PENDING_SWITCH_FILE):
            os.remove(PENDING_SWITCH_FILE)
    except Exception:
        pass


def read_pending_switch():
    """读取待办切换事务"""
    if not os.path.exists(PENDING_SWITCH_FILE):
        return None
    try:
        with open(PENDING_SWITCH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_pending_auto_resume(max_windows=3, text="1", target_href=None, target_title=None):
    """写入自动续接待办事务凭据 (5分钟 TTL 单次令牌，支持活动会话精准锚定)"""
    try:
        os.makedirs(os.path.dirname(PENDING_AUTO_RESUME_FILE), exist_ok=True)
        with open(PENDING_AUTO_RESUME_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "action": "auto_resume",
                "text": text,
                "max_windows": max_windows,
                "target_href": target_href,
                "target_title": target_title,
                "timestamp": time.time(),
                "created_at": datetime.now().isoformat(),
                "ttl_seconds": 300,
                "status": "pending"
            }, f, indent=2)
        hint = f" (优先锚定会话: '{target_title or target_href}')" if (target_title or target_href) else ""
        logger.info(f"已写入大任务断点自动续接凭据{hint} (前排 {max_windows} 个窗口，扣 '{text}')")
    except Exception as e:
        logger.warning(f"写入自动续接事务文件异常: {e}")


def clear_pending_auto_resume():
    """清除自动续接事务凭据"""
    try:
        if os.path.exists(PENDING_AUTO_RESUME_FILE):
            os.remove(PENDING_AUTO_RESUME_FILE)
    except Exception:
        pass


def read_pending_auto_resume():
    """读取自动续接事务凭据 (逾期自动作废)"""
    if not os.path.exists(PENDING_AUTO_RESUME_FILE):
        return None
    try:
        with open(PENDING_AUTO_RESUME_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts = data.get("timestamp", 0)
        ttl = data.get("ttl_seconds", 300)
        if time.time() - ts > ttl:
            logger.info("自动续接事务凭据已超过 5 分钟 TTL，自动作废。")
            clear_pending_auto_resume()
            return None
        return data
    except Exception:
        return None


def get_devtools_active_port(wait_timeout=0):
    """读取 DevToolsActivePort，支持可选的超时轮询等待"""
    start_time = time.time()
    while True:
        if os.path.exists(DEVTOOLS_PORT_FILE):
            try:
                with open(DEVTOOLS_PORT_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if lines:
                    port = int(lines[0].strip())
                    if 1 <= port <= 65535:
                        return port
            except Exception:
                pass
        if time.time() - start_time >= wait_timeout:
            break
    return None


def get_current_active_conversation():
    """在退出旧实例前通过 CDP 抓取当前处于前台活跃状态的会话，用于切号后优先精准续接"""
    port = get_devtools_active_port(wait_timeout=1)
    if not port or not websockets:
        return None
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2)
        pages = json.loads(req.read().decode("utf-8"))
        page = next((p for p in pages if p.get("type") == "page" and p.get("webSocketDebuggerUrl")), None)
        if not page:
            return None
        ws_url = page["webSocketDebuggerUrl"]

        async def _query():
            async with websockets.connect(ws_url, ping_interval=None, close_timeout=2) as ws:
                js = """(() => {
                    const url = window.location.href;
                    const rows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
                    const activeRow = rows.find(r => {
                        const a = r.querySelector('a');
                        return a && url.includes(a.getAttribute('href'));
                    }) || rows.find(r => r.classList.contains('bg-sidebar-secondary'));
                    const a = activeRow ? activeRow.querySelector('a') : null;
                    const t = activeRow ? activeRow.querySelector('.truncate') : null;
                    return {
                        url: url,
                        href: a ? a.getAttribute('href') : '',
                        title: t ? t.textContent.trim() : (document.title || '')
                    };
                })()"""
                payload = {"id": 1, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True}}
                await ws.send(json.dumps(payload))
                resp = json.loads(await ws.recv())
                return resp.get("result", {}).get("result", {}).get("value", {})

        return asyncio.run(_query())
    except Exception as e:
        logger.debug(f"抓取当前活动会话异常: {e}")
        return None


def update_clash_subscriptions(timeout_seconds=12):
    """主动从机场订阅 URL 获取最新节点并刷新本地 Clash Verge 订阅配置"""
    try:
        import ssl
        import yaml
    except ImportError:
        yaml = None

    clash_dir = os.path.join(ROAMING_APPDATA, "io.github.clash-verge-rev.clash-verge-rev")
    profiles_yaml_path = os.path.join(clash_dir, "profiles.yaml")
    if not os.path.exists(profiles_yaml_path):
        logger.warning(f"未找到 Clash Verge profiles.yaml: {profiles_yaml_path}")
        return False

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    logger.info("正在主动从机场订阅源刷新全部 Clash 订阅...")
    try:
        with open(profiles_yaml_path, "r", encoding="utf-8") as f:
            if yaml:
                config = yaml.safe_load(f)
            else:
                logger.warning("未检测到 yaml 模块，跳过解析 profiles.yaml")
                return False
    except Exception as e:
        logger.warning(f"读取 profiles.yaml 异常: {e}")
        return False

    items = config.get("items", [])
    updated_count = 0
    for item in items:
        if item.get("type") == "remote" and item.get("url") and item.get("file"):
            name = item.get("name") or item.get("uid")
            url = item.get("url")
            target_file = os.path.join(clash_dir, "profiles", item.get("file"))
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ClashVerge/v1.7.7"})
                res = urllib.request.urlopen(req, context=ctx, timeout=timeout_seconds)
                content = res.read()
                if len(content) > 500:
                    with open(target_file, "wb") as out_f:
                        out_f.write(content)
                    item["updated"] = int(time.time())
                    updated_count += 1
                    logger.info(f"✅ 成功刷新订阅 [{name}]: 更新了 {len(content)} 字节最新节点数据")
            except Exception as e:
                logger.warning(f"⚠️ 刷新订阅 [{name}] 失败: {e}")

    if updated_count > 0:
        try:
            with open(profiles_yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True)
            logger.info(f"🎉 全部机场订阅刷新完毕！共更新 {updated_count} 个订阅配置。")
            return True
        except Exception as e:
            logger.warning(f"保存更新后的 profiles.yaml 异常: {e}")
    return False


async def _cdp_execute_auto_resume(ws_url, max_windows=3, text="1", target_href=None):
    """通过 CDP WebSocket 连接向 Antigravity 发送前排打标并扣 1 续接脚本 (支持活动会话精准锚定与草稿自愈提交)"""
    import websockets
    try:
        async with websockets.connect(ws_url, ping_interval=None, close_timeout=3) as ws:
            seq = 100
            async def cdp_call(method, params=None):
                nonlocal seq
                seq += 1
                cur_id = seq
                payload = {"id": cur_id, "method": method}
                if params:
                    payload["params"] = params
                await ws.send(json.dumps(payload))
                while True:
                    resp = json.loads(await ws.recv())
                    if resp.get("id") == cur_id:
                        return resp.get("result", {})

            fetch_rows_js = """
            (async () => {
                let rows = [];
                let toggleFound = false;
                let toggleAria = null;
                for (let retry = 0; retry < 120; retry++) {
                    rows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
                    if (rows.length > 0) break;
                    // 仅当侧边栏确实处于折叠状态 (aria-expanded === "false") 时，才点击展开
                    const toggleBtn = document.querySelector('[data-testid="sidebar-toggle"], button[aria-label*="sidebar" i], button[aria-label*="Sidebar" i], button[aria-label*="侧边栏" i]');
                    if (toggleBtn) {
                        toggleFound = true;
                        toggleAria = toggleBtn.getAttribute('aria-expanded');
                        if (toggleAria === 'false') {
                            toggleBtn.click();
                            await new Promise(r => setTimeout(r, 600));
                            rows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
                            if (rows.length > 0) break;
                        }
                    }
                    await new Promise(r => setTimeout(r, 500));
                }
                const convs = rows.map((r, i) => {
                    const titleDiv = r.querySelector('.truncate');
                    const a = r.querySelector('a');
                    return {
                        index: i,
                        title: titleDiv ? titleDiv.textContent.trim() : '未知会话',
                        href: a ? a.getAttribute('href') : '',
                        isSelected: r.classList.contains('bg-sidebar-secondary')
                    };
                });
                return {
                    convs: convs,
                    currentUrl: window.location.href,
                    diagnostics: {
                        rows_found: rows.length,
                        toggle_found: toggleFound,
                        toggle_aria: toggleAria,
                        title: document.title,
                        url: window.location.href
                    }
                };
            })()
            """
            r = await cdp_call("Runtime.evaluate", {"expression": fetch_rows_js, "awaitPromise": True, "returnByValue": True})
            eval_val = r.get("result", {}).get("result", {}).get("value", {}) or r.get("result", {}).get("value", {})
            all_convs = eval_val.get("convs", [])
            current_url = eval_val.get("currentUrl", "")
            diag = eval_val.get("diagnostics", {})
            if not all_convs:
                logger.warning(f"CDP 侧边栏会话列表检索结束 (发现 0 个会话)，DOM 现场: {diag}")
                record_incident(
                    incident_type="CDP_RESUME_NO_CONVERSATIONS",
                    severity="INFO",
                    summary="CDP 自动续接未检索到前排历史会话",
                    root_cause="轮询 60 秒后未在 DOM 中发现 conversation-row-sidebar 元素。侧边栏可能为空或未展开。",
                    evidence=diag,
                    action_taken="跳过自动发送，保持当前新窗口正常在前台使用",
                    recommended_action="若需自动续接前排任务，请确认 Antigravity 侧边栏存在历史对话记录。"
                )
                return {"success": False, "reason": "no_conversations_found", "diagnostics": diag}

            logger.info(f"CDP 成功检索到 {len(all_convs)} 个侧边栏会话，准备智能优先续接 (最多 {max_windows} 个)...")

            # 优先级重组：优先精准锚定切号前的活跃任务会话
            prioritized = []
            if target_href:
                matched = next((c for c in all_convs if c.get("href") and (c["href"] in target_href or target_href in c["href"])), None)
                if not matched:
                    m_uuid = re.search(r'[0-9a-fA-F-]{36}', target_href)
                    if m_uuid:
                        matched = next((c for c in all_convs if m_uuid.group(0) in c.get("href", "")), None)
                if matched:
                    prioritized.append(matched)
                    logger.info(f"🎯 [切号前活跃任务精准定位] 优先续接: '{matched['title']}' ({matched['href']})")

            if not prioritized:
                active_c = next((c for c in all_convs if c.get("href") and (c["href"] in current_url or c.get("isSelected"))), None)
                if active_c:
                    prioritized.append(active_c)
                    logger.info(f"🎯 [当前聚焦窗口命中] 优先续接: '{active_c['title']}' ({active_c['href']})")

            for c in all_convs:
                if len(prioritized) >= int(max_windows):
                    break
                if c not in prioritized:
                    prioritized.append(c)

            target_convs = prioritized
            results = []

            for c in target_convs:
                idx = c["index"]
                title = c["title"]
                href = c["href"]

                # a. 切换至对应会话窗口并等待路由与 DOM 彻底挂载沉降
                switch_and_prep_js = f"""
                (async () => {{
                    const rows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
                    const row = rows[{idx}];
                    if (!row) return {{ status: "no_row" }};
                    const a = row.querySelector('a');
                    if (!a) return {{ status: "no_anchor" }};
                    
                    const targetHref = a.getAttribute('href') || '';
                    if (targetHref && !location.href.includes(targetHref)) {{
                        a.click();
                        // 显式等待路由地址切换完成 (最多 1.5 秒)
                        for (let i = 0; i < 15; i++) {{
                            if (location.href.includes(targetHref)) break;
                            await new Promise(r => setTimeout(r, 100));
                        }}
                        // 给 React 充足的组件重新挂载与状态重置时间
                        await new Promise(r => setTimeout(r, 350));
                    }}

                    // 等待编辑器输入区挂载 (最多等待 3 秒)
                    let editable = null;
                    for (let retry = 0; retry < 15; retry++) {{
                        editable = document.querySelector('[data-lexical-editor="true"]');
                        if (editable) break;
                        await new Promise(r => setTimeout(r, 200));
                    }}

                    if (!editable) return {{ status: "editor_not_found" }};

                    // 检查是否正在生成中 (Stop/Cancel 按钮存在即视为生成中，支持 Agent 模式下的 Stop execution)
                    const isGenerating = !!document.querySelector('button[aria-label*="Stop generation" i], button[aria-label*="Stop execution" i], button[aria-label*="停止生成" i], button[aria-label*="停止执行" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]');
                    if (isGenerating) return {{ status: "generating" }};

                    const currentText = (editable.innerText || '').trim();
                    editable.focus();

                    if (currentText === {json.dumps(str(text))}) {{
                        return {{ status: "ready_has_text" }};
                    }} else if (currentText.length > 0) {{
                        // 输入框已有残留内容或草稿：直接就绪发送现有内容，绝不因 draft_exists 轻易跳过！
                        return {{ status: "ready_custom_draft", text: currentText }};
                    }} else {{
                        document.execCommand('selectAll', false, null);
                        document.execCommand('delete', false, null);
                        return {{ status: "ready" }};
                    }}
                }})()
                """
                prep_res = await cdp_call("Runtime.evaluate", {"expression": switch_and_prep_js, "awaitPromise": True, "returnByValue": True})
                prep_val = prep_res.get("result", {}).get("result", {}).get("value", {}) or prep_res.get("result", {}).get("value", {})
                prep_status = prep_val.get("status")

                if prep_status == "generating":
                    logger.info(f"会话 [{title}] 正在模型生成中，无需打标，保持继续。")
                    results.append({"index": idx + 1, "title": title, "href": href, "success": True, "reason": "already_generating"})
                    continue
                elif prep_status not in ("ready", "ready_has_text", "ready_custom_draft"):
                    results.append({"index": idx + 1, "title": title, "href": href, "success": False, "reason": prep_status})
                    continue

                if prep_status == "ready":
                    # b. 采用原生 CDP Input.insertText 模拟真实按键输入 (触发 Lexical 状态模型绑定)
                    await cdp_call("Input.insertText", {"text": str(text)})
                    await asyncio.sleep(0.3)

                # c. 检测发送按钮并触发点击 (双重提交机制：按钮点击 + 原生 Enter 保底)
                send_js = """
                (async () => {
                    const editable = document.querySelector('[data-lexical-editor="true"]');
                    if (editable) {
                        try { editable.dispatchEvent(new Event('input', { bubbles: true })); } catch(e) {}
                    }
                    const isGen = !!document.querySelector('button[aria-label*="Stop generation" i], button[aria-label*="Stop execution" i], button[aria-label*="停止生成" i], button[aria-label*="停止执行" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]');
                    if (isGen) return { success: true, method: "already_generating" };

                    let container = editable ? editable.parentElement : null;
                    for (let step = 0; step < 6; step++) {
                        if (container && container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button[aria-label*="提交" i]')) break;
                        if (container && container.parentElement) container = container.parentElement;
                    }
                    let sendBtn = null;
                    for (let retry = 0; retry < 15; retry++) {
                        sendBtn = container ? container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button[aria-label*="提交" i]') : document.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button[aria-label*="提交" i]');
                        if (sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true') break;
                        await new Promise(r => setTimeout(r, 100));
                    }
                    if (sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true') {
                        sendBtn.click();
                        return { success: true, method: "button_click" };
                    }
                    return { success: false, reason: "button_not_clickable" };
                })()
                """
                send_res = await cdp_call("Runtime.evaluate", {"expression": send_js, "awaitPromise": True, "returnByValue": True})
                send_val = send_res.get("result", {}).get("result", {}).get("value", {}) or send_res.get("result", {}).get("value", {})
                is_sent = send_val.get("success", False)

                if not is_sent:
                    # 保底双重提交机制：若按钮点击未触发，派发原生键盘 Enter 键 (KeyCode: 13) 提交
                    await cdp_call("Input.dispatchKeyEvent", {
                        "type": "keyDown",
                        "windowsVirtualKeyCode": 13,
                        "unmodifiedText": "\r",
                        "text": "\r"
                    })
                    await cdp_call("Input.dispatchKeyEvent", {
                        "type": "keyUp",
                        "windowsVirtualKeyCode": 13,
                        "unmodifiedText": "\r",
                        "text": "\r"
                    })
                    await asyncio.sleep(0.35)

                # d. 最终验证发送状态 (输入框清空或出现停止生成按钮)
                verify_js = """
                (() => {
                    const editable = document.querySelector('[data-lexical-editor="true"]');
                    const currentText = editable ? (editable.innerText || '').trim() : '';
                    const isGen = !!document.querySelector('button[aria-label*="Stop generation" i], button[aria-label*="Stop execution" i], button[aria-label*="停止生成" i], button[aria-label*="停止执行" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]');
                    return { cleared: currentText.length === 0, generating: isGen };
                })()
                """
                verify_res = await cdp_call("Runtime.evaluate", {"expression": verify_js, "returnByValue": True})
                verify_val = verify_res.get("result", {}).get("result", {}).get("value", {}) or verify_res.get("result", {}).get("value", {})

                if is_sent or verify_val.get("cleared") or verify_val.get("generating"):
                    sent_content = prep_val.get("text") if prep_status == "ready_custom_draft" else text
                    logger.info(f"✅ CDP 窗口 [{idx+1}] 发送成功: 会话='{title}' 成功触发发送 (内容: '{sent_content}')")
                    results.append({"index": idx + 1, "title": title, "href": href, "success": True, "text": sent_content})
                else:
                    fail_reason = send_val.get("reason", "unknown")
                    logger.warning(f"⚠️ CDP 窗口 [{idx+1}] 发送未触发: 会话='{title}' (原因: {fail_reason})")
                    results.append({"index": idx + 1, "title": title, "href": href, "success": False, "reason": fail_reason})

                await asyncio.sleep(1.0)

            # 3. 切回首选窗口聚焦 (带流式生成与防闪退安全保护)
            # 优先保持在成功续接且正在生成的窗口，杜绝在 SSE 生成握手期强行 unmount 导致的渲染进程崩溃与请求中断
            await asyncio.sleep(1.2)
            if target_convs:
                preferred_conv = next((item for item in results if item.get("success")), target_convs[0])
                pref_idx = preferred_conv["index"] - 1 if "index" in preferred_conv and preferred_conv.get("index", 0) > 0 else preferred_conv.get("index", 0)
                switch_back_js = f"""
                (async () => {{
                    // 若当前窗口处于流式生成中，保持聚焦，绝不切换路由
                    const isGen = !!document.querySelector('button[aria-label*="Stop generation" i], button[aria-label*="Stop execution" i], button[aria-label*="停止生成" i], button[aria-label*="停止执行" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]');
                    if (isGen) return {{ status: "stay_generating" }};

                    const rows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
                    if (rows.length > {pref_idx}) {{
                        const link = rows[{pref_idx}].querySelector('a');
                        const targetHref = link ? link.getAttribute('href') : '';
                        if (link && targetHref && !location.href.includes(targetHref)) {{
                            link.click();
                            await new Promise(r => setTimeout(r, 400));
                        }}
                    }}
                    return {{ status: "ok" }};
                }})()
                """
                try:
                    await cdp_call("Runtime.evaluate", {"expression": switch_back_js, "awaitPromise": True})
                except Exception as e:
                    logger.debug(f"切回聚焦窗口静默忽略: {e}")

            succ_cnt = sum(1 for item in results if item.get("success"))
            logger.info(f"CDP 自动续接处理完毕: 总共处理 {len(results)} 个会话窗口，成功续接发送: {succ_cnt} 个")

            return {
                "success": True,
                "processed": len(results),
                "success_count": succ_cnt,
                "results": results
            }
    except (websockets.exceptions.ConnectionClosedOK, websockets.exceptions.ConnectionClosed) as e:
        logger.debug(f"CDP WebSocket 连接关闭: {e}")
        return {"success": True, "note": "connection_closed_normally"}


def get_antigravity_main_pid():
    """获取 Antigravity 主进程 PID (排除 --type=xxx 渲染或工具子进程)"""
    if not psutil:
        return 0
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["name"] and p.info["name"].lower() == "antigravity.exe":
                cmd = " ".join(p.info.get("cmdline") or [])
                if "--type=" not in cmd:
                    return p.info["pid"]
        except Exception:
            pass
    return 0


def execute_auto_resume(max_windows=3, text="1", wait_timeout=180, exclude_pids=None, target_href=None):
    """执行前排任务窗口打标与自动续接 (单飞互斥保护，支持活动会话精准锚定)"""
    if websockets is None:
        logger.warning("未检测到 websockets 模块，无法通过 CDP 执行自动续接。")
        return False

    lock = AutoResumeLock()
    if not lock.acquire():
        logger.info("⚡ 检测到另一个自动续接任务正在执行中，本实例自动安全退出，彻底避免双进程并发踩踏。")
        return False

    try:
        token = read_pending_auto_resume()
        if token:
            max_windows = token.get("max_windows", max_windows)
            text = token.get("text", text)
            if not target_href:
                target_href = token.get("target_href")
            # 立即消费令牌，防止后续重复调用
            clear_pending_auto_resume()

        # 1. 优先等待 Launcher 彻底完成并退出，确保 Antigravity 窗口稳定在前台且互斥锁已释放
        launcher_wait_start = time.time()
        while time.time() - launcher_wait_start < 150:
            launcher_active = False
            if psutil:
                for p in psutil.process_iter(["name"]):
                    try:
                        if p.info["name"] and "antigravity-recovery-launcher" in p.info["name"].lower():
                            launcher_active = True
                            break
                    except Exception:
                        pass
            if not launcher_active:
                break
            time.sleep(0.5)

        # 稍微等待 1.5 秒让 Electron 渲染进程完全挂载 DOM
        time.sleep(1.5)

        logger.info(f"正在等待 Antigravity 实例与 DevTools 端口就绪 (最长等待 {wait_timeout} 秒)...")
        import urllib.request
        ws_url = None
        start_t = time.time()
        while time.time() - start_t < wait_timeout:
            curr_pid = get_antigravity_main_pid()
            if curr_pid and (not exclude_pids or curr_pid not in exclude_pids):
                port = get_devtools_active_port(wait_timeout=2)
                if port:
                    try:
                        req = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2)
                        pages = json.loads(req.read().decode("utf-8"))
                        page = next((p for p in pages if p.get("type") == "page" and p.get("webSocketDebuggerUrl")), None)
                        if page:
                            ws_url = page["webSocketDebuggerUrl"]
                            break
                    except Exception:
                        pass
            time.sleep(1.0)

        if not ws_url:
            logger.warning("未能获取到新 Antigravity 页面的 WebSocket 调试地址，跳过自动续接。")
            return False

        logger.info(f"已连接 Antigravity CDP ({ws_url})，正在执行前排窗口打标与扣 '{text}' 续接...")
        for retry in range(2):
            try:
                result = asyncio.run(_cdp_execute_auto_resume(ws_url, max_windows=max_windows, text=text, target_href=target_href))
                logger.info(f"自动续接执行结果: {json.dumps(result, ensure_ascii=False)}")

                clear_pending_auto_resume()

                success_items = [r for r in result.get("results", []) if r.get("success")]
                count_sent = len(success_items)
                if count_sent > 0:
                    logger.info(f"✅ 已成功唤醒 {count_sent} 个任务窗口（优先续接活跃会话）")
                return True
            except Exception as e:
                logger.warning(f"执行自动续接尝试 {retry + 1} 发生异常: {e}")
                if retry == 0:
                    time.sleep(2.0)
                    port = get_devtools_active_port(wait_timeout=2)
                    if port:
                        try:
                            req = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2)
                            pages = json.loads(req.read().decode("utf-8"))
                            page = next((p for p in pages if p.get("type") == "page" and p.get("webSocketDebuggerUrl")), None)
                            if page:
                                ws_url = page["webSocketDebuggerUrl"]
                        except Exception:
                            pass

        return False
    finally:
        lock.release()


def load_cockpit_server_info():
    if not os.path.exists(SERVER_FILE):
        raise FileNotFoundError(f"Cockpit server.json 未找到: {SERVER_FILE} (Cockpit Tools 是否已运行?)")
    with open(SERVER_FILE, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return {
        "ws_port": data.get("ws_port", 19528),
        "auth_token": data.get("auth_token", ""),
        "pid": data.get("pid", 0)
    }


def get_all_accounts_and_quotas():
    if not os.path.exists(ACCOUNTS_FILE):
        raise FileNotFoundError(f"Cockpit accounts.json 未找到: {ACCOUNTS_FILE}")
    
    with open(ACCOUNTS_FILE, "r", encoding="utf-8-sig") as f:
        acc_data = json.load(f)
    
    current_id = acc_data.get("current_account_id", "")
    accounts = acc_data.get("accounts", [])
    now = datetime.now(timezone.utc)
    
    cache_map = {}
    if os.path.exists(QUOTA_CACHE_DIR):
        for fname in os.listdir(QUOTA_CACHE_DIR):
            if fname.endswith(".json"):
                p = os.path.join(QUOTA_CACHE_DIR, fname)
                try:
                    with open(p, "r", encoding="utf-8-sig") as cf:
                        cd = json.load(cf)
                    email = cd.get("email", "").strip().lower()
                    if email:
                        cache_map[email] = cd
                except Exception:
                    pass
    
    results = []
    for acc in accounts:
        acc_id = acc.get("id")
        email = acc.get("email", "").strip()
        name = acc.get("name", "")
        disabled = acc.get("disabled", False)
        is_current = (acc_id == current_id)
        
        cd = cache_map.get(email.lower(), {})
        groups = cd.get("payload", {}).get("quota_summary", {}).get("groups", [])
        
        q_5h = None
        q_weekly = None
        rt_weekly = None
        rt_5h = None
        
        for g in groups:
            if g.get("displayName") == "Gemini Models":
                for b in g.get("buckets", []):
                    bid = b.get("bucketId", "")
                    rf = b.get("remainingFraction", 0.0)
                    pct = round(rf * 100.0, 1)
                    rt = parse_iso_datetime(b.get("resetTime"))
                    if bid == "gemini-5h":
                        q_5h = pct
                        rt_5h = rt
                    elif bid == "gemini-weekly":
                        q_weekly = pct
                        rt_weekly = rt
        
        # 默认安全兜底
        q_5h_val = q_5h if q_5h is not None else 0.0
        q_w_val = q_weekly if q_weekly is not None else 0.0
        
        # 有效额度：以 5 小时滚动额度与周额度作为并行门禁！
        # 铁律：只要周额度 <= 1.0% (见底) 或 5小时额度 <= 5.0%，该账号有效额度即为 0.0%
        # 只有在 5小时 > 5% 且 周额度 > 1.0% 时，才具备实际可用生产力
        effective = 0.0 if (q_w_val <= 1.0 or q_5h_val <= 5.0) else q_5h_val
        
        # 周恢复重置时间计算（剩余天数与秒数）
        if rt_weekly:
            sec_to_w_reset = max(0.0, (rt_weekly - now).total_seconds())
            days_to_w_reset = round(sec_to_w_reset / 86400.0, 1)
        else:
            sec_to_w_reset = 7.0 * 86400.0
            days_to_w_reset = 7.0
        
        # Cockpit Tools 综合评分机制 (Cockpit Score)：
        # 1. 5小时满血度（0~150分）：越高越好，>=95% 满血加 50 分
        score_5h = q_5h_val + (50.0 if q_5h_val >= 95.0 else 0.0)
        
        # 2. 周恢复紧迫度（0~100分）：越快恢复重置，紧迫度越高，越优先消化存量
        if days_to_w_reset <= 1.0:
            score_urgency = 100.0
        elif days_to_w_reset <= 2.0:
            score_urgency = 80.0
        elif days_to_w_reset <= 3.0:
            score_urgency = 60.0
        elif days_to_w_reset <= 4.0:
            score_urgency = 40.0
        elif days_to_w_reset <= 5.0:
            score_urgency = 20.0
        else:
            score_urgency = 0.0
        
        # 3. 周剩余额度安全分（0~50分）：周额度越充沛越能持续支撑对话
        score_weekly = min(50.0, q_w_val * 0.5)
        
        cockpit_score = round(score_5h + score_urgency + score_weekly, 1)
        tiger_score = cockpit_score
        
        results.append({
            "id": acc_id,
            "email": email,
            "name": name,
            "disabled": disabled,
            "is_current": is_current,
            "gemini_5h": q_5h_val,
            "gemini_weekly": q_w_val,
            "reset_time_5h": rt_5h,
            "reset_time_weekly": rt_weekly,
            "days_to_w_reset": days_to_w_reset,
            "sec_to_w_reset": sec_to_w_reset,
            "effective_quota": effective,
            "score_5h": score_5h,
            "score_urgency": score_urgency,
            "score_weekly": score_weekly,
            "cockpit_score": cockpit_score,
            "tiger_score": tiger_score
        })
    
    return current_id, results


def select_best_account(accounts, current_id, threshold=5.0, target_email_or_id=None):
    if target_email_or_id:
        target_norm = target_email_or_id.strip().lower()
        for acc in accounts:
            if acc["id"] == target_email_or_id or acc["email"].lower() == target_norm:
                return acc, "用户指定目标账号"
        raise ValueError(f"未找到指定的账号: {target_email_or_id}")
    
    # 门禁过滤（并行条件）：
    # 1. 排除当前在用与已禁用账号；
    # 2. 排除处于 429 临时关押冷却期的账号；
    # 3. 周额度 <= 1.0% 必须一票否决淘汰（周额度耗尽在 Google 端会直接 429）；
    # 4. 5小时额度 <= threshold (5%) 必须一票否决淘汰；
    # 铁律：候选账号必须同时满足 [周额度 > 1.0%] 且 [5小时额度 > threshold]！
    quarantined = load_quarantined_accounts()
    candidates = [
        acc for acc in accounts
        if not acc.get("disabled", False)
        and not acc.get("is_current", False)
        and acc.get("id") != current_id
        and acc.get("id") not in quarantined
        and float(acc.get("gemini_weekly", 0.0)) > 1.0
        and float(acc.get("gemini_5h", 0.0)) > threshold
    ]
    
    if candidates:
        # 按 Cockpit Tools 综合评分降序排列
        candidates.sort(key=lambda x: x.get("cockpit_score", 0.0), reverse=True)
        best = candidates[0]
        reason = (
            f"Cockpit Tools 智能优选 [得分: {best.get('cockpit_score', 0.0)}]：5小时满血({best.get('gemini_5h', 0.0)}%)，"
            f"周恢复时间仅剩 {best.get('days_to_w_reset', 7.0)}天 (优先消化即将到期额度)，周额度剩余 {best.get('gemini_weekly', 0.0)}%"
        )
        return best, reason
    
    # 彻底废除旧代码的盲目 fallback 兜底！
    # 严格遵从用户铁律：若没有真正可用账号，坚决不切号、不重启、不杀窗口！
    raise RuntimeError("当前所有备选账号的 5小时或周额度均已耗尽 (周额度 <= 1% 或 5h <= 5%)，无法自动切换！")


def is_antigravity_running():
    if psutil:
        for p in psutil.process_iter(["name"]):
            try:
                name = p.info.get("name")
                if name and name.lower() == "antigravity.exe":
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    try:
        res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Antigravity.exe"], capture_output=True, text=True)
        return "Antigravity.exe" in res.stdout
    except Exception:
        return False


_LAST_FEISHU_NOTIFY_TIME = {}


def send_feishu_notification(title, message, chat_names=None, debounce_seconds=90):
    """通过飞书 OpenAPI 向指定群组和私聊推送通知（含 90s 防抖保护）"""
    global _LAST_FEISHU_NOTIFY_TIME
    now = time.time()
    last_sent = _LAST_FEISHU_NOTIFY_TIME.get(title, 0)
    if now - last_sent < debounce_seconds:
        logger.info(f"💡 [飞书通知防抖保护] 距离上一条通知仅过去 {now - last_sent:.1f} 秒 (< {debounce_seconds}s)，已安全抑制避免刷屏。")
        return False

    if not os.path.exists(FEISHU_CONFIG_FILE):
        return False
    try:
        with open(FEISHU_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        
        app_id = cfg.get("app_id")
        app_secret = (cfg.get("app_secret"))
        if not app_id or not app_secret:
            return False

        # 换取 tenant_access_token
        auth_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        auth_data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
        req = urllib.request.Request(auth_url, data=auth_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_info = json.loads(resp.read().decode("utf-8"))
        token = token_info.get("tenant_access_token")
        if not token:
            return False

        group_map = cfg.get("群列表", {})
        # 默认发送给：通用通知群 和 飞书牛马 CLI 私聊
        targets = []
        if chat_names:
            for name in chat_names:
                cid = group_map.get(name) or name
                if cid and cid not in targets:
                    targets.append(cid)
        else:
            infra_chat = cfg.get("infra_ops_chat", "AI 额度与系统运维群")
            default_targets = [infra_chat]
            for dt in default_targets:
                cid = group_map.get(dt) or dt
                if cid and cid not in targets:
                    targets.append(cid)

        content_text = f"🔔 【{title}】\n{message}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        success_count = 0
        for cid in targets:
            try:
                send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
                payload = {
                    "receive_id": cid,
                    "msg_type": "text",
                    "content": json.dumps({"text": content_text}, ensure_ascii=False)
                }
                send_req = urllib.request.Request(send_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(send_req, timeout=8) as s_resp:
                    if s_resp.status == 200:
                        success_count += 1
            except Exception as e:
                logger.debug(f"向飞书目标 {cid} 发送消息异常: {e}")
        
        if success_count > 0:
            _LAST_FEISHU_NOTIFY_TIME[title] = now
            logger.info(f"✅ 飞书通知推送成功 ({success_count}/{len(targets)} 目标)")
            return True
    except Exception as e:
        logger.warning(f"飞书通知发送异常: {e}")
    return False


def send_windows_notification(title, message, status="warning", duration_ms=8000):
    """发送桌面通知：优先使用 shared-notification 技能，失败降级为系统气泡"""
    # 1. 优先调用本地 shared-notification 技能
    if os.path.exists(SHARED_NOTIFY_SCRIPT):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("shared_notify", SHARED_NOTIFY_SCRIPT)
            if spec and spec.loader:
                shared_notify = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(shared_notify)
                res = shared_notify.notify(
                    message=message,
                    title=title,
                    status=status,
                    duration_ms=duration_ms,
                    source="AntigravitySmartSwitch"
                )
                if res:
                    return True
        except Exception as e:
            logger.debug(f"shared_notify 技能调用异常，降级到系统气泡: {e}")

    # 2. 降级为 PowerShell NotifyIcon
    if sys.platform != "win32":
        return False
    try:
        clean_msg = message.replace('"', '\"').replace('\n', ' `n ')
        clean_title = title.replace('"', '\"')
        ps_cmd = (
            f'[void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); '
            f'$ni = New-Object System.Windows.Forms.NotifyIcon; '
            f'$ni.Icon = [System.Drawing.SystemIcons]::Information; '
            f'$ni.BalloonTipTitle = "{clean_title}"; '
            f'$ni.BalloonTipText = "{clean_msg}"; '
            f'$ni.Visible = $True; '
            f'$ni.ShowBalloonTip(4000); '
            f'Start-Sleep -Milliseconds 800; '
            f'$ni.Dispose()'
        )
        flags = 0x08000000 if sys.platform == "win32" else 0
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd], creationflags=flags)
        return True
    except Exception:
        return False


def send_dual_notification(title, message, status="warning"):
    """同时发送桌面通知技能与飞书群/私聊通知"""
    send_windows_notification(title, message, status=status)
    send_feishu_notification(title, message)


def _load_quota_pool_state():
    try:
        if os.path.exists(QUOTA_POOL_STATE_FILE):
            with open(QUOTA_POOL_STATE_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        logger.debug(f"读取账号池额度状态异常: {e}")
    return {}


def _save_quota_pool_state(state):
    try:
        os.makedirs(os.path.dirname(QUOTA_POOL_STATE_FILE), exist_ok=True)
        temp_path = QUOTA_POOL_STATE_FILE + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, QUOTA_POOL_STATE_FILE)
    except Exception as e:
        logger.debug(f"保存账号池额度状态异常: {e}")


def guard_quota_pool_exhaustion(accounts, current_id=None, threshold=5.0, force_exhausted=False):
    """全池无可用备选账号 (周额度 <= 1.0% 或 5h <= 5.0%) 时停止自动切号，并仅在状态变化时通知一次。"""
    enabled_accounts = [a for a in accounts if not a.get("disabled", False)]
    if not enabled_accounts:
        return False

    if not current_id:
        curr = next((a for a in enabled_accounts if a.get("is_current")), None)
        if curr:
            current_id = curr.get("id")

    # 1. 全池所有启用账号周额度均见底 (<= 1.0%)
    all_weekly_exhausted = all(float(a.get("gemini_weekly", 0.0)) <= 1.0 for a in enabled_accounts)

    # 2. 检查除当前账号外是否存在合资格候选账号 (周额度 > 1.0% 且 5h > threshold)
    quarantined = load_quarantined_accounts()
    candidates = [
        a for a in enabled_accounts
        if a.get("id") != current_id
        and not a.get("is_current", False)
        and a.get("id") not in quarantined
        and float(a.get("gemini_weekly", 0.0)) > 1.0
        and float(a.get("gemini_5h", 0.0)) > threshold
    ]

    curr_acc = next((a for a in enabled_accounts if a.get("id") == current_id or a.get("is_current")), None)
    curr_is_exhausted = (
        curr_acc is None
        or float(curr_acc.get("gemini_weekly", 0.0)) <= 1.0
        or float(curr_acc.get("gemini_5h", 0.0)) <= threshold
    )

    is_pool_exhausted = (
        force_exhausted
        or all_weekly_exhausted
        or (curr_is_exhausted and len(candidates) == 0)
    )

    previous = _load_quota_pool_state()

    if not is_pool_exhausted:
        if previous.get("status") in ("weekly_exhausted", "exhausted"):
            logger.info("✅ [账号池额度恢复] 检测到备选账号周额度与5h额度已恢复，解除停止切号状态。")
            _save_quota_pool_state({
                "status": "available",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "enabled_account_count": len(enabled_accounts),
            })
        return False

    reset_times = [
        a.get("reset_time_weekly") for a in enabled_accounts
        if isinstance(a.get("reset_time_weekly"), datetime) and a.get("reset_time_weekly") > datetime.now(timezone.utc)
    ]
    next_reset = min(reset_times).astimezone().strftime("%m-%d %H:%M") if reset_times else "等待 Cockpit 更新周额度"
    is_new_exhaustion = previous.get("status") not in ("weekly_exhausted", "exhausted")
    should_notify = is_new_exhaustion or not previous.get("notified", False)

    if is_new_exhaustion:
        logger.warning(
            f"🛑 [账号池额度耗尽] {len(enabled_accounts)} 个启用账号已无可用备选额度 (周额度 <= 1% 或 5h <= {threshold}%)，"
            "已停止自动切号、凭据写入、订阅刷新、窗口退出和启动器重启。"
        )
        record_incident(
            incident_type="ACCOUNT_POOL_WEEKLY_QUOTA_EXHAUSTED",
            severity="WARNING",
            summary="所有启用账号/备选账号额度均已耗尽",
            root_cause=f"账号池中所有备选账号均满足淘汰条件 (周额度 <= 1.0% 或 5h <= {threshold}%)，无可用候选账号。",
            evidence={"enabled_account_count": len(enabled_accounts), "next_weekly_reset": next_reset},
            action_taken="已停止自动切号和重启，保持当前客户端与网络状态不变",
            recommended_action=f"无需继续切号；请在 Antigravity 界面切换至其他模型。最近预计恢复时间：{next_reset}。",
        )
    else:
        logger.debug("账号池仍无可用备选账号，继续静默等待，不重复切号或弹窗。")

    notified = bool(previous.get("notified", False))
    if should_notify:
        notified = send_windows_notification(
            "Antigravity 账号池额度已耗尽",
            f"全部 {len(enabled_accounts)} 个可用账号已无可用备选额度 (周额度 <= 1% 或 5h <= {threshold}%)。\n"
            "系统已停止自动切号和重启，保持当前窗口完好运行。\n"
            f"请在当前界面手动切换至其他模型。预计周额度恢复时间：{next_reset}。",
            status="warning",
            duration_ms=12000,
        )

    _save_quota_pool_state({
        "status": "weekly_exhausted",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "enabled_account_count": len(enabled_accounts),
        "next_weekly_reset": next_reset,
        "notified": bool(notified),
    })
    return True


def gracefully_exit_antigravity(timeout_seconds=5.0):
    logger.info("正在检测运行中的 Antigravity 实例...")
    if not psutil:
        logger.warning("未检测到 psutil，采用 taskkill 兜底")
        subprocess.run(["taskkill", "/IM", "Antigravity.exe"], capture_output=True)
        time.sleep(2)
        return
    
    target_procs = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if p.info["name"] and p.info["name"].lower() == "antigravity.exe":
                target_procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if not target_procs:
        logger.info("未发现运行中的 Antigravity 进程，无需退出。")
        return
    
    logger.info(f"发现 {len(target_procs)} 个 Antigravity 进程，正在发送优雅退出信号 (WM_CLOSE)...")
    close_cmd = "Get-Process Antigravity -ErrorAction SilentlyContinue | ForEach-Object { if ($_.MainWindowHandle -ne 0) { $_.CloseMainWindow() } }"
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", close_cmd], capture_output=True, timeout=5)
    except Exception as e:
        logger.warning(f"发送 CloseMainWindow 异常: {e}")
    
    start_wait = time.time()
    while time.time() - start_wait < timeout_seconds:
        alive = [p for p in target_procs if p.is_running()]
        if not alive:
            logger.info("Antigravity 进程已优雅退出并释放凭据锁。")
            return
        time.sleep(0.3)
    
    remaining = [p for p in target_procs if p.is_running()]
    if remaining:
        logger.warning(f"超过 {timeout_seconds}s 仍有 {len(remaining)} 个进程残留，执行强制终止...")
        for p in remaining:
            try:
                p.terminate()
            except Exception:
                pass
        time.sleep(0.5)
        for p in remaining:
            try:
                if p.is_running():
                    p.kill()
            except Exception:
                pass
    
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if p.info["name"] and "language_server" in p.info["name"].lower():
                exe_path = (p.info.get("exe") or "").lower()
                if "antigravity" in exe_path:
                    p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def decrypt_cockpit_account(account_id):
    """从 Cockpit Tools 本地安全加密存储中无损解密指定账号的完整数据 (含 access_token, refresh_token)"""
    key_path = os.path.join(COCKPIT_DIR, "secure-account-storage.key")
    acc_path = os.path.join(COCKPIT_DIR, "accounts", f"{account_id}.json")
    if not os.path.exists(key_path) or not os.path.exists(acc_path):
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        with open(key_path, "r", encoding="utf-8") as f:
            key = base64.b64decode(f.read().strip())
        with open(acc_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        aesgcm = AESGCM(key)
        dec = aesgcm.decrypt(base64.b64decode(doc["nonce"]), base64.b64decode(doc["ciphertext"]), None)
        return json.loads(dec)
    except Exception as e:
        logger.warning(f"解密 Cockpit 账号 {account_id} 凭据异常: {e}")
        return None


def get_current_windows_credential_token():
    """读取当前 Windows Credential Manager (gemini:antigravity) 中实际生效的 token"""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        advapi32 = ctypes.windll.advapi32
        class CREDENTIAL(ctypes.Structure):
            _fields_ = [
                ('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_byte)), ('Persist', wintypes.DWORD),
                ('AttributeCount', wintypes.DWORD), ('Attributes', ctypes.c_void_p),
                ('TargetAlias', wintypes.LPWSTR), ('UserName', wintypes.LPWSTR),
            ]
        pcred = ctypes.POINTER(CREDENTIAL)()
        if advapi32.CredReadW('gemini:antigravity', 1, 0, ctypes.byref(pcred)):
            raw = ctypes.string_at(pcred.contents.CredentialBlob, pcred.contents.CredentialBlobSize).decode('utf-8')
            advapi32.CredFree(pcred)
            d = json.loads(raw)
            return d.get('token', {})
    except Exception:
        pass
    return None


def write_antigravity_windows_credential(account_id):
    """
    【核心突破】直接将目标账号 Token 写入 Windows Credential Manager (系统凭据管理器: gemini:antigravity)
    Antigravity 2.0 (v2.12.2+) 完全依赖 Windows 系统凭据进行模型认证，绕过 state.vscdb 与 Cockpit 协议脱节
    """
    if sys.platform != "win32":
        return False

    acc_data = decrypt_cockpit_account(account_id)
    if not acc_data:
        logger.error(f"无法解密账号 {account_id}，无法写入 Windows 系统凭据！")
        return False

    token = acc_data.get("token", {})
    access_token = token.get("access_token", "")
    refresh_token = (token.get("refresh_token", ""))
    expiry_ts = token.get("expiry_timestamp")
    if expiry_ts:
        expiry_str = datetime.fromtimestamp(expiry_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
    else:
        expiry_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000Z")

    cred_payload = {
        "token": {
            "access_token": access_token,
            "token_type": "Bearer",
            "refresh_token": refresh_token,
            "expiry": expiry_str
        },
        "auth_method": "consumer"
    }
    raw_bytes = json.dumps(cred_payload, separators=(",", ":")).encode("utf-8")

    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.windll.advapi32

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.c_char_p),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    cred = CREDENTIAL()
    cred.Flags = 0
    cred.Type = 1  # CRED_TYPE_GENERIC
    cred.TargetName = "gemini:antigravity"
    cred.Comment = None
    cred.CredentialBlob = raw_bytes
    cred.CredentialBlobSize = len(raw_bytes)
    cred.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
    cred.AttributeCount = 0
    cred.Attributes = None
    cred.TargetAlias = None
    cred.UserName = "antigravity"

    ok = advapi32.CredWriteW(ctypes.byref(cred), 0)
    if ok:
        logger.info(f"🔑 [系统凭据直写成功] 已直接将账号 [{acc_data.get('email')}] 真实写入 Windows 凭据管理器 (gemini:antigravity)")
        # 同步更新 current_account.json 与 accounts.json
        try:
            curr_acc_file = os.path.join(COCKPIT_DIR, "current_account.json")
            with open(curr_acc_file, "w", encoding="utf-8") as cf:
                json.dump({"email": acc_data.get("email"), "updated_at": int(time.time())}, cf, indent=2)
        except Exception:
            pass
        return True
    else:
        err = ctypes.GetLastError()
        logger.error(f"写入 Windows 系统凭据失败，错误码: {err}")
        return False


async def switch_account_via_websocket(server_info, target_account_id, timeout=25.0):
    if not websockets:
        raise ImportError("未安装 websockets 库")
    
    ws_port = server_info["ws_port"]
    auth_token = server_info["auth_token"]
    ws_url = f"ws://127.0.0.1:{ws_port}?token={auth_token}"
    
    logger.info(f"正在连接 Cockpit WebSocket 接口: ws://127.0.0.1:{ws_port} ...")
    async with websockets.connect(ws_url) as ws:
        ready_msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
        ready_data = json.loads(ready_msg)
        if ready_data.get("type") != "event.ready":
            logger.warning(f"收到非预期的握手消息: {ready_msg}")
        
        req_id = f"smart_switch_{int(time.time() * 1000)}"
        payload = {
            "type": "request.switch_account",
            "payload": {
                "request_id": req_id,
                "account_id": target_account_id
            }
        }
        
        logger.info(f"正在发送切号指令 (target_id={target_account_id}) ...")
        await ws.send(json.dumps(payload))
        
        start_t = time.time()
        while time.time() - start_t < timeout:
            # 1. 优先瞬时核验 accounts.json (Cockpit 通常在 1.5~2.5 秒内完成落盘)
            try:
                if os.path.exists(ACCOUNTS_FILE):
                    with open(ACCOUNTS_FILE, "r", encoding="utf-8-sig") as f:
                        curr = json.load(f).get("current_account_id")
                        if curr == target_account_id:
                            logger.info("校验 accounts.json 确认当前账号已更新成功！")
                            return True
            except Exception:
                pass

            # 2. 接收 WebSocket 广播消息
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.5)
                data = json.loads(raw)
                msg_type = data.get("type", "")
                if msg_type in ("event.account_switched", "response.plugin_switch_account", "response.success"):
                    logger.info("Cockpit 已确认凭据写入完成！")
                    return True
                elif msg_type in ("event.switch_error", "response.error"):
                    err = data.get("payload", {}).get("error", "未知错误")
                    logger.error(f"Cockpit 切号报错: {err}")
                    return False
            except asyncio.TimeoutError:
                pass
    
    # 超时后最终兜底核验
    try:
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r", encoding="utf-8-sig") as f:
                curr = json.load(f).get("current_account_id")
                if curr == target_account_id:
                    logger.info("最终校验 accounts.json 确认当前账号已更新成功。")
                    return True
    except Exception:
        pass
    
    return False


def sync_all_cockpit_account_files(target_account_id, target_email):
    """四合一物理原子对齐：确保 Cockpit 所有配置文件的当前账号物理一致"""
    results = {}
    now_ts = int(time.time())

    # 1. accounts.json
    acc_path = os.path.join(COCKPIT_DIR, "accounts.json")
    if os.path.exists(acc_path):
        try:
            with open(acc_path, "r", encoding="utf-8-sig") as f:
                d = json.load(f)
            d["current_account_id"] = target_account_id
            for a in d.get("accounts", []):
                if a.get("id") == target_account_id:
                    a["last_used"] = now_ts
            with open(acc_path, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
            results["accounts.json"] = "OK"
        except Exception as e:
            results["accounts.json"] = f"ERROR: {e}"

    # 2. current_account.json
    curr_path = os.path.join(COCKPIT_DIR, "current_account.json")
    try:
        data = {"email": target_email, "updated_at": now_ts}
        with open(curr_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        results["current_account.json"] = "OK"
    except Exception as e:
        results["current_account.json"] = f"ERROR: {e}"

    # 3. instances.json
    inst_path = os.path.join(COCKPIT_DIR, "instances.json")
    if os.path.exists(inst_path):
        try:
            with open(inst_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if "defaultSettings" in d:
                d["defaultSettings"]["bindAccountId"] = target_account_id
            with open(inst_path, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=2)
            results["instances.json"] = "OK"
        except Exception as e:
            results["instances.json"] = f"ERROR: {e}"

    # 4. antigravity_legacy_instances.json
    legacy_path = os.path.join(COCKPIT_DIR, "antigravity_legacy_instances.json")
    if os.path.exists(legacy_path):
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            if "defaultSettings" in d:
                d["defaultSettings"]["bindAccountId"] = target_account_id
            with open(legacy_path, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=2)
            results["antigravity_legacy_instances.json"] = "OK"
        except Exception as e:
            results["antigravity_legacy_instances.json"] = f"ERROR: {e}"

    return results


def refresh_cockpit_tools_ui():
    """向处于运行中的 Cockpit Tools 窗口发送安全静默刷新，促使 WebView2 立即重新加载最新账号列表并标绿高亮"""
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
        if not hdesk:
            return False, "无法打开 Default 桌面"
        user32.SetThreadDesktop(hdesk)

        cockpit_hwnds = []
        def enum_cb(hwnd, extra):
            title_buff = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title_buff, 256)
            cls_buff = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buff, 256)
            if "Cockpit Tools" in title_buff.value or cls_buff.value == "Tauri Window":
                cockpit_hwnds.append(hwnd)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumDesktopWindows(hdesk, WNDENUMPROC(enum_cb), 0)

        if not cockpit_hwnds:
            return False, "未发现运行中的 Cockpit Tools 窗口"

        refreshed_count = 0
        WM_KEYDOWN = 0x0100
        WM_KEYUP = 0x0101
        VK_F5 = 0x74

        for top_hwnd in cockpit_hwnds:
            child_hwnds = []
            def child_cb(chwnd, extra):
                ccls_buff = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(chwnd, ccls_buff, 256)
                if any(k in ccls_buff.value for k in ["RenderWidgetHostHWND", "Chrome_WidgetWin", "WRY_WEBVIEW"]):
                    child_hwnds.append(chwnd)
                return True

            user32.EnumChildWindows(top_hwnd, WNDENUMPROC(child_cb), 0)
            target_list = child_hwnds if child_hwnds else [top_hwnd]
            for target_h in target_list:
                user32.PostMessageW(target_h, WM_KEYDOWN, VK_F5, 0x003F0001)
                time.sleep(0.03)
                user32.PostMessageW(target_h, WM_KEYUP, VK_F5, 0xC03F0001)
                refreshed_count += 1

        return True, f"成功向 {refreshed_count} 个 Cockpit 窗口组件派发热刷新通知"
    except Exception as e:
        return False, f"刷新 Cockpit UI 异常: {e}"


def launch_antigravity_via_launcher(recovery_reason="cockpit_account_changed", background=False):
    target = None
    if os.path.exists(LAUNCHER_EXE):
        target = LAUNCHER_EXE
    elif os.path.exists(DESKTOP_LNK):
        target = DESKTOP_LNK
    
    if not target:
        raise FileNotFoundError(f"未找到启动器文件: {LAUNCHER_EXE}")
    
    logger.info(f"正在以脱壳独立进程拉起桌面智能启动器: {target} (reason={recovery_reason}, background={background}) ...")
    flags = 0
    if sys.platform == "win32":
        # 彻底脱壳：脱离当前控制台、父进程 Job Object 与进程树
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        CREATE_BREAKAWAY_FROM_JOB = 0x01000000
        flags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS | CREATE_BREAKAWAY_FROM_JOB
    
    try:
        if target.endswith(".exe"):
            args = [target]
            if background:
                args.append("--background")
            else:
                args.append("--force-launch")
            args.append(f"--recovery-reason={recovery_reason}")
            subprocess.Popen(
                args,
                creationflags=flags,
                close_fds=True
            )
        else:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "", target],
                creationflags=flags,
                close_fds=True
            )
        logger.info("✅ 脱壳启动器已拉起，将展示状态胶囊并挂载 17897 专线代理 + 模型自愈 + 汉化扩展！")
    except Exception as e:
        logger.warning(f"脱壳拉起启动器异常，执行备用方式: {e}")
        subprocess.Popen([target], shell=True)


def run_smart_switch(threshold=5.0, target=None, dry_run=False, force=False):
    current_id, accounts = get_all_accounts_and_quotas()
    curr_acc = next((a for a in accounts if a["is_current"]), None)
    curr_email = curr_acc["email"] if curr_acc else "未知"
    curr_5h = curr_acc["gemini_5h"] if curr_acc else 0.0
    curr_weekly = curr_acc["gemini_weekly"] if curr_acc else 0.0
    curr_effective = curr_acc["effective_quota"] if curr_acc else 0.0
    sub_summary = get_subscription_summary()
    
    logger.info("=" * 65)

    # 自动切换的最高优先级门禁：若所有启用账号周额度均归零或无可用候选账号，继续切号没有任何收益。
    # 必须在选号、写凭据、刷新订阅、关窗口和启动器重启之前短路。
    if not target and guard_quota_pool_exhaustion(accounts, current_id=current_id, threshold=threshold):
        return "quota_pool_exhausted"
    logger.info(f"当前反重力账号: {curr_email} (5h: {curr_5h:.1f}%, 周额度: {curr_weekly:.1f}%, 有效: {curr_effective:.1f}%)")
    logger.info(f"专线网络订阅状态: {sub_summary}")
    logger.info("账号池实时 Cockpit Tools 智能健康度看板:")
    for acc in accounts:
        marker = " <== [当前在用]" if acc["is_current"] else ""
        print(f"  * {acc['email']:28} | 有效: {acc['effective_quota']:5.1f}% | 5h: {acc['gemini_5h']:5.1f}% | 周额: {acc['gemini_weekly']:5.1f}% (剩{acc['days_to_w_reset']:3.1f}天) | Cockpit分: {acc['cockpit_score']:5.1f}{marker}")
    logger.info("=" * 65)
    
    if not force and not target:
        is_exhausted = (curr_5h <= threshold) or (curr_weekly <= 1.0)
        if not is_exhausted:
            logger.info(f"当前账号配额充沛 (5h: {curr_5h:.1f}%, 周: {curr_weekly:.1f}%)，高于门禁阈值，无需切号。使用 --force 可强制切换。")
            return "not_needed"
    
    try:
        best_acc, reason = select_best_account(accounts, current_id, threshold=threshold, target_email_or_id=target)
    except RuntimeError as e:
        logger.warning(f"🛑 选号门禁阻断: {e}。保持当前反重力窗口运行，严禁杀窗口与重启！")
        return "quota_pool_exhausted"
    logger.info(f"🎯 【优选目标】: {best_acc['email']} (ID: {best_acc['id']})")
    logger.info(f"📋 【决策理由】: {reason}")
    
    if dry_run:
        logger.info("[DryRun 演练模式] 未执行实际退出与切号操作。")
        return "dry_run"
    
    # 0. 优先探测抓取切号前当前处于活跃前台的会话窗口，用于精准续接
    active_conv = get_current_active_conversation()
    target_href = active_conv.get("href") if active_conv else None
    target_title = active_conv.get("title") if active_conv else None

    # 1. 记录切号待办事务与断点自动续接凭据，同时【提前】落盘 watcher-current-account.txt 封死 Watcher 二段竞争
    write_pending_switch(best_acc)
    write_pending_auto_resume(max_windows=3, text="1", target_href=target_href, target_title=target_title)
    try:
        os.makedirs(os.path.dirname(WATCHER_CURRENT_ACCOUNT_FILE), exist_ok=True)
        with open(WATCHER_CURRENT_ACCOUNT_FILE, "w", encoding="utf-8") as f:
            f.write(best_acc["id"].strip())
    except Exception as e:
        logger.debug(f"提前同步 watcher-current-account.txt 异常: {e}")
    
    # 2. 剩余 5% 触发切号：按规则【只发桌面通知，不发飞书】
    notif_title = "Antigravity 额度预警 (剩余 <= 5%)"
    active_info = f"\n📌 保护中活动任务: {target_title}" if target_title else ""
    notif_msg = (
        f"当前在用账号 [{curr_email}] 额度剩余 <= 5% (5h: {curr_5h:.1f}%, 周: {curr_weekly:.1f}%)\n"
        f"🎯 优选满血接力: {best_acc['email']} (5h: {best_acc['gemini_5h']}%, 周: {best_acc['gemini_weekly']}%){active_info}\n"
        f"📋 决策理由: {reason}\n"
        f"⚡ 正在后台先行切号 (反重力正常运行中，切号成功后执行订阅更新与接力重启)..."
    )
    send_windows_notification(notif_title, notif_msg, status="warning")
    
    old_pid = get_antigravity_main_pid()

    # =========================================================================
    # 【核心顺序 1】：先切号，切成功后再操作其他的必须
    # （反重力保持运行！绝不提前杀窗口。若切号失败，反重力完好无损）
    # =========================================================================
    logger.info(f"⚡ [步骤 1/5] 先切号：向 Cockpit Tools 发送切号指令至目标账号 [{best_acc['email']}] (反重力保持运行中)...")
    server_info = load_cockpit_server_info()
    ok = asyncio.run(switch_account_via_websocket(server_info, best_acc["id"]))
    if not ok:
        logger.warning("Cockpit Tools WebSocket 未返回确认，正在执行 Windows 原生系统凭据原子直写兜底...")

    # 【核心注入】：直接原子写入 Windows Credential Manager (gemini:antigravity)
    # Antigravity 2.0 (v2.12.2+) 完全依赖 Windows 系统凭据进行模型认证！
    cred_ok = write_antigravity_windows_credential(best_acc["id"])
    if not ok and not cred_ok:
        logger.error("向 Cockpit Tools 发送切号指令且系统凭据直写均失败，取消本次切换！反重力未被终止，当前窗口保持完好。")
        send_windows_notification(
            "Antigravity 切号未完成",
            f"尝试切换至账号 [{best_acc['email']}] 失败，本次切号已取消，当前反重力保持运行。",
            status="error"
        )
        clear_pending_switch()
        clear_pending_auto_resume()
        return "switch_failed"

    # 【四合一状态同步与 UI 刷新对账】：确保 Cockpit 前端界面、实例配置与底层文件 100% 物理一致
    cockpit_sync_res = sync_all_cockpit_account_files(best_acc["id"], best_acc["email"])
    logger.info(f"📊 Cockpit 关联状态文件原子对齐完成: {cockpit_sync_res}")
    ui_refreshed, ui_msg = refresh_cockpit_tools_ui()
    logger.info(f"🖥️ Cockpit Tools 界面高亮实时热跟随: {ui_msg}")

    logger.info(f"✅ [步骤 1/5 完成] 目标账号 [{best_acc['email']}] 已成功注入 Windows 系统凭据 (gemini:antigravity) 与 Cockpit！")

    # =========================================================================
    # 【核心顺序 2】：订阅更新 (专线网络/Clash 机场节点刷新)
    # =========================================================================
    logger.info("🌐 [步骤 2/5] 订阅更新：正在更新并刷新专线网络与 Clash 机场节点...")
    try:
        update_clash_subscriptions(timeout_seconds=15)
    except Exception as e:
        logger.warning(f"刷新订阅异常 (继续执行后续流程): {e}")

    # =========================================================================
    # 【核心顺序 3】：退出反重力 (此时新账号凭据与订阅已全部就绪，优雅退出释放句柄与锁)
    # =========================================================================
    logger.info(f"🚪 [步骤 3/5] 退出反重力：切号与订阅已就绪，正在优雅退出旧 Antigravity 实例 (PID: {old_pid})...")
    gracefully_exit_antigravity(timeout_seconds=5.0)

    # =========================================================================
    # 【核心顺序 4】：启动启动器 (派发桌面智能启动器拉起新实例，挂载 17897 专线代理)
    # =========================================================================
    logger.info("🚀 [步骤 4/5] 启动启动器：正在派发桌面智能启动器拉起全新实例并挂载专线代理...")
    launch_antigravity_via_launcher(recovery_reason="AccountChange", background=False)

    # =========================================================================
    # 【核心顺序 5】：启动后在前 3 对话窗口扣 1 (优先切号前活跃任务)
    # =========================================================================
    logger.info("🎯 [步骤 5/5] 自动续接：正在等待新实例就绪，并在前 3 个对话窗口扣 1 (优先切号前活跃任务)...")
    execute_auto_resume(
        max_windows=3,
        text="1",
        wait_timeout=180,
        exclude_pids=[old_pid] if old_pid else None,
        target_href=target_href
    )
    clear_pending_switch()
    reset_language_server_log_pos()

    # 6. 切换并重启成功：按规则【发桌面也发飞书】
    succ_title = "Antigravity 切换并重启成功"
    succ_msg = (
        f"✅ 账号已成功切换至: {best_acc['email']}\n"
        f"🚀 17897 专线网络已重新挂载，前 3 个对话窗口已自动扣 1 续接完成！"
    )
    send_dual_notification(succ_title, succ_msg, status="info")
    return "switched"


def print_status_table():
    current_id, accounts = get_all_accounts_and_quotas()
    curr_acc = next((a for a in accounts if a["is_current"]), None)
    sub_summary = get_subscription_summary()
    print("\n" + "=" * 80)
    print(f"【Cockpit Tools 智能账号池配额与恢复排期看板】")
    print(f"当前在用: {curr_acc['email'] if curr_acc else '无'} | 专线网络订阅: {sub_summary}")
    print("=" * 80)
    print(f"{'序号':<3} {'账号邮箱':<28} {'有效额度':<9} {'5小时限额':<10} {'周限额':<8} {'周恢复倒计时':<12} {'Cockpit分':<8} {'状态'}")
    print("-" * 80)
    for i, acc in enumerate(accounts, 1):
        if acc["is_current"]:
            status = "★ 当前在用"
        elif acc["gemini_5h"] <= 5.0:
            status = "✕ 5h额度耗尽"
        elif acc["gemini_weekly"] <= 0.0:
            status = "✕ 周额度见底"
        else:
            status = "✔ 健康待命"
        print(f"{i:<3} {acc['email']:<28} {acc['effective_quota']:>5.1f}%   {acc['gemini_5h']:>6.1f}%    {acc['gemini_weekly']:>5.1f}%     剩 {acc['days_to_w_reset']:>4.1f} 天    {acc['cockpit_score']:>6.1f}   {status}")
    print("=" * 80 + "\n")


def stop_watch_daemon():
    stopped = 0
    if psutil:
        cur_pid = os.getpid()
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if p.info["pid"] == cur_pid:
                    continue
                cmd = " ".join(p.info.get("cmdline") or [])
                if "antigravity_smart_switch.py" in cmd and "--watch" in cmd:
                    p.terminate()
                    stopped += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    logger.info(f"已停止 {stopped} 个运行中的自动续航守护进程。")


_global_mutex_handle = None
_last_language_log_pos = 0
_last_switch_time = 0.0


def reset_language_server_log_pos():
    """切号完成后将日志指针同步到当前文件末尾，并记录切号时间戳，彻底消除旧账号残留报错引起的幽灵连环二次切号"""
    global _last_language_log_pos, _last_switch_time
    _last_switch_time = time.time()
    try:
        if os.path.exists(LANGUAGE_SERVER_LOG):
            _last_language_log_pos = os.path.getsize(LANGUAGE_SERVER_LOG)
        else:
            _last_language_log_pos = 0
        logger.debug(f"已重置 language_server 日志指针至最新末尾: {_last_language_log_pos}，并进入 90 秒保护静默期")
    except Exception as e:
        logger.debug(f"重置 language_server 日志指针异常: {e}")


def ensure_account_watcher_running():
    """双星互保：检查并自愈拉起 Antigravity-AccountWatcher 系统级守卫"""
    if sys.platform != "win32" or not psutil:
        return
    
    target_exe = ACCOUNT_WATCHER_EXE
    if not os.path.exists(target_exe):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_exe = os.path.join(script_dir, "Antigravity-AccountWatcher.exe")
    if not os.path.exists(target_exe):
        return
    
    # 扫描当前运行进程
    for p in psutil.process_iter(["name"]):
        try:
            if p.info["name"] and p.info["name"].lower() == "antigravity-accountwatcher.exe":
                return # 正常常驻运行中
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    logger.info("⚠️ 检测到系统级守卫 Antigravity-AccountWatcher 掉线，正在自愈脱壳拉起...")
    try:
        cmd = f'powershell -NoProfile -Command "Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{ CommandLine = \'{target_exe}\'; CurrentDirectory = \'{os.path.dirname(target_exe)}\' }}"'
        subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
        logger.info("✅ 系统级守卫 Antigravity-AccountWatcher 已通过脱壳服务成功自愈重启！")
    except Exception as e:
        logger.warning(f"自愈拉起 Antigravity-AccountWatcher 异常: {e}")


def check_language_server_quota_error():
    """穿透监听 language_server.log，毫秒级感知 429 / RESOURCE_EXHAUSTED / quota 耗尽报错，并进行账号重置时刻指纹归属识别"""
    global _last_language_log_pos, _last_switch_time

    # 保护冷却期：刚切号的 90 秒内不响应 429 报错，防止读取到旧会话未断开或旧进程的残余日志
    if time.time() - _last_switch_time < 90:
        return False

    if not os.path.exists(LANGUAGE_SERVER_LOG):
        _last_language_log_pos = 0
        return False

    try:
        size = os.path.getsize(LANGUAGE_SERVER_LOG)
        if _last_language_log_pos == 0:
            # 首次启动：定位到当前文件末尾，避免历史旧错误造成误切
            _last_language_log_pos = size
            return False
            
        if size < _last_language_log_pos:
            # 文件被重建或轮转：直接对齐到当前文件末尾，避免重新扫描整个文件
            _last_language_log_pos = size
            return False
            
        if size == _last_language_log_pos:
            return False
            
        with open(LANGUAGE_SERVER_LOG, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(_last_language_log_pos)
            new_content = f.read()
            _last_language_log_pos = f.tell()
            
        quota_err_patterns = [
            "RESOURCE_EXHAUSTED",
            "quota exceeded",
            "quotaExceeded",
            "hit your 5-hour limit",
            "Too Many Requests",
            "status:429",
            "code: 429",
            "HTTP 429"
        ]
        for pat in quota_err_patterns:
            if pat.lower() in new_content.lower():
                matched_lines = [line.strip() for line in new_content.splitlines() if pat.lower() in line.lower()]
                matched_snippet = matched_lines[0] if matched_lines else new_content[:200].strip()

                # 1. 提取重置倒计时与报错发生时间戳
                duration = 9000
                m_dur = re.search(r'Resets in (?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', matched_snippet)
                if m_dur:
                    h = int(m_dur.group(1) or 0)
                    mi = int(m_dur.group(2) or 0)
                    s = int(m_dur.group(3) or 0)
                    calc_dur = h * 3600 + mi * 60 + s
                    if calc_dur > 0:
                        duration = calc_dur

                # 从报错日志行中解析原始时间（例如 I0907 22:23:34）以获得精确的秒级基准
                m_time = re.search(r'[IEW](\d{2})(\d{2})\s+(\d{2}):(\d{2}):(\d{2})', matched_snippet)
                if m_time:
                    try:
                        now_loc = datetime.now()
                        log_dt = now_loc.replace(
                            month=int(m_time.group(1)),
                            day=int(m_time.group(2)),
                            hour=int(m_time.group(3)),
                            minute=int(m_time.group(4)),
                            second=int(m_time.group(5)),
                            microsecond=0
                        )
                        log_utc = log_dt.astimezone(timezone.utc)
                    except Exception:
                        log_utc = datetime.now(timezone.utc)
                else:
                    log_utc = datetime.now(timezone.utc)

                target_reset_utc = log_utc + timedelta(seconds=duration)

                # 2. 读取当前所有账号信息与配额重置时刻指纹
                current_id = None
                accounts = []
                try:
                    current_id, accounts = get_all_accounts_and_quotas()
                except Exception as e:
                    logger.debug(f"读取账号配额指纹异常: {e}")

                curr_acc = next((a for a in accounts if a["is_current"]), None)
                curr_email = curr_acc["email"] if curr_acc else "未知账号"
                curr_5h = curr_acc["gemini_5h"] if curr_acc else 0.0

                # 3. 核心指纹比对：检查 target_reset_utc 是否与非当前账号的重置时刻吻合
                matched_non_current = None
                if accounts:
                    for acc in accounts:
                        if acc.get("is_current"):
                            continue
                        for rt_key in ("reset_time_5h", "reset_time_weekly"):
                            rt = acc.get(rt_key)
                            if rt and isinstance(rt, datetime):
                                if abs((target_reset_utc - rt).total_seconds()) <= 180:
                                    matched_non_current = (acc, rt_key, rt)
                                    break
                        if matched_non_current:
                            break

                # 4. 若报错指纹明确指向历史离线账号：安全降噪过滤并强化隔离
                if matched_non_current:
                    old_acc, rt_key, rt_val = matched_non_current

                    # 【核心纠偏】：核验 Windows Credential Manager 中当前实际生效的 Token！
                    # 如果 Windows 凭据实际就是这个 old_acc，说明底层根本没切过去，确认为凭据脱节裸奔，必须立即自愈切号！
                    win_tok = get_current_windows_credential_token()
                    win_rt = (win_tok.get("refresh_token") or "").strip() if win_tok else ""
                    old_dec = decrypt_cockpit_account(old_acc["id"])
                    old_rt = (old_dec.get("token", {}).get("refresh_token") or "").strip() if old_dec else ""

                    if win_rt and old_rt and win_rt == old_rt:
                        logger.warning(f"🚨 [凭据脱节确诊] 捕获到 429 报错指向 {old_acc['email']}，且核验发现 Windows 系统凭据实际仍为该账号！")
                        logger.warning("   确认为底层未能完成真实切号，立即强制触发自愈切号与系统凭据注入！")
                        record_quarantine_account(old_acc["id"], duration)
                        return True

                    logger.info(f"💡 [日志穿透降噪] 捕获到 429 报错重置时刻 ({target_reset_utc.strftime('%H:%M:%S UTC')}) 指向历史账号 {old_acc['email']} ({rt_key}: {rt_val.strftime('%H:%M:%S UTC')})")
                    logger.info(f"   当前在用账号 ({curr_email}) 状态健康 (5h: {curr_5h}%)，判定为历史会话残留重试，已安全过滤忽略。")
                    # 顺便关押该历史账号，确保关押期内绝不误切回该账号
                    record_quarantine_account(old_acc["id"], duration)
                    return False

                # 5. 若未匹配到离线旧账号，确认为当前在用账号真实 429 耗尽
                logger.warning(f"🚨 [实时日志穿透感知] 核心语言服务检测到当前账号真实 429 额度耗尽！")
                logger.warning(f"   * 当前在用账号: {curr_email} (5h: {curr_5h}%)")
                logger.warning(f"   * 原始报错文本: {matched_snippet[:240]}")

                if current_id:
                    record_quarantine_account(current_id, duration)

                record_incident(
                    incident_type="MODEL_QUOTA_EXHAUSTED",
                    severity="WARNING",
                    summary=f"检测到当前账号模型配额耗尽: '{pat}'",
                    root_cause=f"Language Server 捕获到 Gemini API 返回 429/RESOURCE_EXHAUSTED 错误: {matched_snippet[:240]}",
                    evidence={"pattern": pat, "snippet": matched_snippet[:300], "target_reset_utc": target_reset_utc.isoformat()},
                    action_taken="已触发账号池额度门禁；仅在存在可用账号时执行切换",
                    recommended_action="系统会先核对全池周额度；若全部为 0，将停止切号并弹出明确通知。"
                )
                return True
    except Exception as e:
        logger.debug(f"检查 language_server 日志异常: {e}")
        
    return False


def run_watch_daemon(threshold=5.0, interval=30):
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        os.makedirs(os.path.dirname(DAEMON_LOG_FILE), exist_ok=True)
        file_handler = RotatingFileHandler(DAEMON_LOG_FILE, maxBytes=1024 * 1024, backupCount=2, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(file_handler)
    
    # 互斥锁防止多个 Watcher 重复运行 (显式指定 64 位指针类型并持久化持有句柄)
    if sys.platform == "win32":
        global _global_mutex_handle
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        mutex_name = "Local\\AntigravitySmartQuotaWatcher"
        handle = kernel32.CreateMutexW(None, False, mutex_name)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            logger.info("已存在运行中的【Cockpit Tools 无人值守自动续航守护神】实例，静默退出当前多余实例。")
            return
        _global_mutex_handle = handle
            
    sub_summary = get_subscription_summary()
    logger.info("=" * 65)
    logger.info("🚀 【Cockpit Tools 无人值守自动续航守护神】已就绪！(双星互保脱壳常驻模式)")
    logger.info(f"   * 自动切号阈值: <= {threshold}%")
    logger.info(f"   * 巡检轮询周期: {interval} 秒")
    logger.info(f"   * 专线网络订阅: {sub_summary}")
    logger.info(f"   * 守护日志路径: {DAEMON_LOG_FILE}")
    logger.info("=" * 65)
    
    # 开机或守护启动自愈：检查是否存在未闭环的待切事务
    pending = read_pending_switch()
    if pending and (time.time() - pending.get("timestamp", 0) > 10):
        logger.info(f"发现未闭环的切号待办事务 (目标: {pending.get('target_email')})，正在自动补发自愈拉起...")
        launch_antigravity_via_launcher(recovery_reason="AccountChange")
        clear_pending_switch()

    # 检查是否存在待自动续接的事务凭据
    pending_resume = read_pending_auto_resume()
    if pending_resume and is_antigravity_running():
        logger.info("发现切号后待自动续接的事务凭据，正在执行前排窗口自动扣 1 续接...")
        execute_auto_resume(
            max_windows=pending_resume.get("max_windows", 3),
            text=pending_resume.get("text", "1"),
            wait_timeout=15
        )
    
    loop_count = 0
    _last_antigravity_running = is_antigravity_running()
    while True:
        try:
            # 1. 双星互保：每 2 轮 (约 60 秒) 检查一次 C# 守卫存活状态
            if loop_count % 2 == 0:
                ensure_account_watcher_running()

            # 2. 穿透监听：只要 language_server 出现配额耗尽/429 报错，无需等待磁盘缓存，立刻触发无感切号与续接！
            log_quota_hit = check_language_server_quota_error()
            if log_quota_hit and is_antigravity_running():
                current_id_tmp, accounts_tmp = get_all_accounts_and_quotas()
                if guard_quota_pool_exhaustion(accounts_tmp, current_id=current_id_tmp, threshold=threshold, force_exhausted=True):
                    logger.warning("🛑 [429 触发但账号池耗尽] 检测到当前账号 429 报错，但全池已无可用备选账号 (周额度 <= 1% 或 5h <= 5%)！")
                    logger.warning("   严格执行 No-Kill 铁律：保持当前反重力窗口打开，严禁关窗口或重启！等待用户手动切换模型。")
                else:
                    logger.warning("!" * 65)
                    logger.warning("🚀 【实时日志报错触发】捕获到模型 429/配额耗尽异常！立刻启动全自动无感自愈续航闭环！")
                    logger.warning("!" * 65)
                    switch_result = run_smart_switch(threshold=threshold, force=True)
                    if switch_result == "switched":
                        logger.info("自愈切换指令已下发，休眠 35 秒等待新实例完全就绪...")
                        time.sleep(35)
                    elif switch_result == "quota_pool_exhausted":
                        logger.warning("账号池周额度全部耗尽，本轮已停止，不执行切号、关窗口或重启。")
                loop_count = 0
                continue

            # 2.5 人工手动切号感知与锚点对齐 (解决机制缺失2：避免二段误杀)
            try:
                current_id, accounts = get_all_accounts_and_quotas()
                curr_acc = next((a for a in accounts if a["is_current"]), None)
                if curr_acc:
                    curr_email = curr_acc["email"]
                    handled_acc_id = ""
                    if os.path.exists(WATCHER_CURRENT_ACCOUNT_FILE):
                        with open(WATCHER_CURRENT_ACCOUNT_FILE, "r", encoding="utf-8") as f:
                            handled_acc_id = f.read().strip()
                    pending = read_pending_switch()
                    if handled_acc_id and current_id != handled_acc_id and not pending:
                        logger.info(f"💡 [人工切号感知] 检测到用户在 Cockpit 手动切号至: {curr_email} (ID: {current_id})")
                        logger.info("   正在平滑同步本地锚点 watcher-current-account.txt，彻底抑制二段误杀！")
                        with open(WATCHER_CURRENT_ACCOUNT_FILE, "w", encoding="utf-8") as f:
                            f.write(current_id.strip())
                        reset_language_server_log_pos()
                        remove_quarantined_account(current_id)
            except Exception as e:
                logger.debug(f"人工切号感知异常: {e}")

            # 3. 常规磁盘配额轮询
            now_running = is_antigravity_running()
            if not _last_antigravity_running and now_running:
                logger.info(f"✨ [实例启动感知] 检测到 Antigravity 实例已恢复运行 (PID: {get_antigravity_main_pid()})，专线保护正常挂载。")
            elif _last_antigravity_running and not now_running:
                pending = read_pending_switch()
                if not pending:
                    logger.warning("🚨 [窗口关闭感知] 检测到 Antigravity 窗口已退出 (用户手动退出或异常终止)")
                    record_incident(
                        incident_type="ANTIGRAVITY_PROCESS_CRASHED",
                        severity="CRITICAL",
                        summary="Antigravity 编辑器主进程意外退出或崩溃",
                        root_cause="前台 Antigravity 进程在运行过程中突然消失，且未处于计划内的凭据切换事务中。",
                        evidence={"timestamp": time.time(), "watcher_pid": os.getpid()},
                        action_taken="已生成故障现场快照，处于待命状态",
                        recommended_action="若窗口意外消失，可双击桌面启动器恢复，系统将保留会话并重新挂载专线。"
                    )
            _last_antigravity_running = now_running

            if now_running:
                current_id, accounts = get_all_accounts_and_quotas()
                curr_acc = next((a for a in accounts if a["is_current"]), None)
                if curr_acc:
                    curr_effective = curr_acc["effective_quota"]
                    curr_email = curr_acc["email"]
                    curr_5h = curr_acc["gemini_5h"]
                    curr_weekly = curr_acc["gemini_weekly"]
                    
                    if loop_count % 10 == 0:
                        logger.info(
                            f"[巡检心跳] Antigravity 运行中 | 当前在用: {curr_email} | "
                            f"有效额度: {curr_effective:.1f}% (5h: {curr_5h:.1f}%, 周: {curr_weekly:.1f}%)"
                        )
                        # 【主动自检 1：系统凭据与账号池一致性主动对账】
                        # 每 5 分钟主动核验 Windows Credential Manager 中生效的 Token 是否与当前在用账号完全一致
                        # 若发生脱节（比如外部切号异常），无需等 429 报错，守护神主动发现并毫秒级自愈直写！
                        try:
                            win_tok = get_current_windows_credential_token()
                            win_rt = (win_tok.get("refresh_token") or "").strip() if win_tok else ""
                            curr_dec = decrypt_cockpit_account(curr_acc["id"])
                            curr_rt = (curr_dec.get("token", {}).get("refresh_token") or "").strip() if curr_dec else ""
                            if win_rt and curr_rt and win_rt != curr_rt:
                                logger.warning(f"🔍 [主动对账发现脱节] 检测到 Windows 系统凭据与 Cockpit 当前账号 ({curr_email}) 不一致！")
                                logger.info(f"   无需等待 429 报错，正在主动无感自愈注入 Windows 系统凭据...")
                                if write_antigravity_windows_credential(curr_acc["id"]):
                                    logger.info(f"   ✅ [主动自愈成功] Windows 系统凭据已自动对齐注入为 {curr_email}")
                        except Exception as cred_err:
                            logger.debug(f"主动凭据一致性自检跳过: {cred_err}")

                        # 【主动自检 2：账号池健康存量预警】
                        healthy_accounts = [
                            a for a in accounts
                            if float(a.get("gemini_5h", 0.0)) > threshold and float(a.get("gemini_weekly", 0.0)) > 1.0 and a.get("id") != current_id
                        ]
                        if len(healthy_accounts) == 0:
                            logger.warning("⚠️ [主动健康预警] 账号池中除当前在用账号外，已无其他 5h 配额充足且周额度 > 1% 的备用账号！")
                        elif len(healthy_accounts) == 1:
                            logger.info(f"💡 [账号池余量感知] 备用健康账号仅存 1 个 ({healthy_accounts[0]['email']})，请注意关注。")
                    
                    # 门禁触发条件：5小时额度耗尽 (<= threshold) 或 周额度见底 (<= 1.0%)
                    is_exhausted = (curr_5h <= threshold) or (curr_weekly <= 1.0)
                    if is_exhausted:
                        # 检查账号池是否已无可用候选账号
                        if guard_quota_pool_exhaustion(accounts, current_id=current_id, threshold=threshold):
                            if loop_count % 10 == 0:
                                logger.warning(
                                    f"🛑 [账号池耗尽待命] 当前账号 {curr_email} 额度不足 (5h: {curr_5h:.1f}%, 周: {curr_weekly:.1f}%)，"
                                    "且池中已无其他可用备选账号。已停止切号和重启，保持当前窗口运行。"
                                )
                            continue

                        reason_str = f"5小时配额耗尽 ({curr_5h:.1f}% <= {threshold}%)" if curr_5h <= threshold else f"周配额见底 ({curr_weekly:.1f}% <= 1.0%)"
                        logger.warning("!" * 65)
                        logger.warning(
                            f"⚠️ 【门禁触发】当前账号 {curr_email} {reason_str}！"
                        )
                        logger.warning("🚀 正在启动 Cockpit Tools 全自动无感自愈续航闭环：先切号 -> 订阅更新 -> 退出反重力 -> 启动启动器 -> 前3窗口扣1")
                        logger.warning("!" * 65)
                        
                        switch_result = run_smart_switch(threshold=threshold, force=True)
                        if switch_result == "switched":
                            logger.info("自愈切换指令已下发，休眠 35 秒等待新实例完全就绪...")
                            time.sleep(35)
                        elif switch_result == "quota_pool_exhausted":
                            logger.warning("账号池周额度全部耗尽，本轮已停止，不执行切号、关窗口或重启。")
                        loop_count = 0
                        continue

            if not now_running and loop_count % 20 == 0:
                logger.debug("[巡检挂起] 未检测到 Antigravity 运行实例，处于低耗待命模式...")
        except Exception as e:
            logger.warning(f"巡检发生异常 (将在下一周期自动重试): {e}")
        
        loop_count += 1
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Antigravity 智能切号与平滑重启工具 (Cockpit Tools 智能版)")
    parser.add_argument("--threshold", type=float, default=5.0, help="自动切号配额百分比阈值 (默认: 5.0)")
    parser.add_argument("--target", type=str, default=None, help="指定切换的目标账号 (邮箱或 ID)")
    parser.add_argument("--dry-run", action="store_true", help="演练模式，仅计算选号不实际执行")
    parser.add_argument("--force", action="store_true", help="忽略当前额度强制触发切号")
    parser.add_argument("--status", action="store_true", help="仅打印所有账号的当前配额状态与排期看板")
    parser.add_argument("--incident", action="store_true", help="打印最近一次系统故障现场智能自诊快照")
    parser.add_argument("--watch", action="store_true", help="启动无人值守看门狗守护进程模式")
    parser.add_argument("--interval", type=int, default=30, help="守护巡检轮询间隔秒数 (默认: 30)")
    parser.add_argument("--stop-watch", action="store_true", help="停止正在运行的看门狗守护进程")
    parser.add_argument("--auto-resume", action="store_true", help="立即执行前排窗口打标与扣1自动续接")
    parser.add_argument("--resume-text", type=str, default="1", help="自动续接发送的内容 (默认: 1)")
    parser.add_argument("--resume-count", type=int, default=3, help="自动续接前排窗口数 (默认: 3)")
    parser.add_argument("--update-subscriptions", action="store_true", help="主动从机场提供商更新全部 Clash 订阅配置")
    
    args = parser.parse_args()
    
    if args.stop_watch:
        stop_watch_daemon()
    elif args.watch:
        run_watch_daemon(threshold=args.threshold, interval=args.interval)
    elif args.status:
        print_status_table()
    elif args.incident:
        print_incident_report()
    elif args.auto_resume:
        execute_auto_resume(max_windows=args.resume_count, text=args.resume_text, wait_timeout=5)
    elif args.update_subscriptions:
        update_clash_subscriptions()
    else:
        run_smart_switch(
            threshold=args.threshold,
            target=args.target,
            dry_run=args.dry_run,
            force=args.force
        )


if __name__ == "__main__":
    main()
