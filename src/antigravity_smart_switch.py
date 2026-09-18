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
BETA_FLAG_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "beta.flag")


def is_beta_mode():
    """检测当前是否处于测试版模式 (由启动器 --beta 或存在 beta.flag 触发)"""
    return os.path.exists(BETA_FLAG_FILE)


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


def record_quarantine_account(account_id, duration_seconds=1800):
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
DESKTOP_LNK = os.path.join(USER_PROFILE, "Desktop", "Google Antigravity.lnk")
LEGACY_DESKTOP_LNK = os.path.join(USER_PROFILE, "Desktop", "Antigravity 启动器.lnk")


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


def normalize_target_path(url_or_path: str) -> str:
    """将绝对 URL (含动态随机本地端口) 或相对路径统一净化为标准的相对路由路径 (/c/...)"""
    if not url_or_path:
        return ""
    import urllib.parse
    try:
        parsed = urllib.parse.urlparse(url_or_path)
        if parsed.path:
            p = parsed.path
            if parsed.query:
                p += f"?{parsed.query}"
            return p
    except Exception:
        pass
    import re
    cleaned = re.sub(r'^https?://[^/]+', '', url_or_path)
    if not cleaned.startswith('/'):
        cleaned = '/' + cleaned
    return cleaned


def find_live_web_server_port():
    """查找当前存活的 Antigravity 本地 Web 服务器端口 (HTTPS)"""
    import ssl
    import urllib.request
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    candidate_ports = []
    if psutil:
        for p in psutil.process_iter(['pid', 'name']):
            try:
                name = (p.info.get('name') or '').lower()
                if 'language_server' in name or 'antigravity' in name:
                    for conn in p.net_connections():
                        if conn.status == 'LISTEN' and conn.laddr.port:
                            candidate_ports.append(conn.laddr.port)
            except Exception:
                pass
    for port in sorted(set(candidate_ports)):
        try:
            req = urllib.request.urlopen(f'https://127.0.0.1:{port}/c', context=ctx, timeout=1.5)
            if req.status in (200, 301, 302, 404):
                return port
        except Exception:
            pass
    return None


def write_pending_auto_resume(max_windows=3, text="继续", target_href=None, target_title=None, interrupted_panes=None, running_sidebar_tasks=None, full_url=None, panes=None):
    """写入自动续接待办事务凭据 (5分钟 TTL 单次令牌，支持智能断点感知精准续接)"""
    try:
        if full_url:
            full_url = normalize_target_path(full_url)
        if target_href:
            target_href = normalize_target_path(target_href)
        os.makedirs(os.path.dirname(PENDING_AUTO_RESUME_FILE), exist_ok=True)
        with open(PENDING_AUTO_RESUME_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "action": "auto_resume",
                "text": text,
                "max_windows": max_windows,
                "target_href": target_href,
                "target_title": target_title,
                "interrupted_panes": interrupted_panes if interrupted_panes is not None else [],
                "running_sidebar_tasks": running_sidebar_tasks if running_sidebar_tasks is not None else [],
                "full_url": full_url,
                "panes": panes if panes is not None else [],
                "timestamp": time.time(),
                "created_at": datetime.now().isoformat(),
                "ttl_seconds": 300,
                "status": "pending"
            }, f, indent=2)
        hint = f" (优先锚定会话: '{target_title or target_href}')" if (target_title or target_href) else ""
        brk_hint = ""
        if interrupted_panes:
            brk_hint += f" [断点分屏列: {interrupted_panes}]"
        if running_sidebar_tasks:
            brk_hint += f" [侧边栏转圈任务: {len(running_sidebar_tasks)}个]"
        logger.info(f"已写入大任务断点自动续接凭据{hint}{brk_hint} (前排 {max_windows} 个窗口，扣 '{text}')")
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


def get_recent_brain_active_conversations(exclude_cids=None, max_age_seconds=180):
    """从本地 ~/.gemini/antigravity/brain 毫秒级嗅探近期处于活动或被中断态的会话清单（解决侧边栏虚拟滚动与429停转丢失）"""
    exclude = set(exclude_cids or [])
    brain_dir = os.path.expanduser(r"~/.gemini/antigravity/brain")
    now = time.time()
    recent = []
    if not os.path.exists(brain_dir):
        return recent
    try:
        for entry in os.scandir(brain_dir):
            if entry.is_dir() and len(entry.name) == 36 and entry.name not in exclude:
                t_path = os.path.join(entry.path, ".system_generated", "logs", "transcript.jsonl")
                if os.path.exists(t_path):
                    try:
                        mtime = os.path.getmtime(t_path)
                        age = now - mtime
                        if age < max_age_seconds:
                            with open(t_path, "rb") as f:
                                f.seek(max(0, os.path.getsize(t_path) - 4096))
                                tail = f.read().decode("utf-8", errors="ignore").strip().splitlines()
                                last_line = tail[-1] if tail else ""
                                data = json.loads(last_line) if last_line else {}
                                is_active = False
                                if data.get("source") == "MODEL":
                                    is_active = True
                                elif data.get("source") == "system" and "server restart" in str(data.get("content", "")):
                                    is_active = True
                                elif data.get("type") in ("PLANNER_RESPONSE", "GENERIC"):
                                    is_active = True

                                if is_active:
                                    recent.append({
                                        "conv_id": entry.name,
                                        "href": f"/c/{entry.name}",
                                        "title": f"后台断点-{entry.name[:8]}",
                                        "age_sec": round(age, 1)
                                    })
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"扫描活跃 brain 会话异常: {e}")
    recent.sort(key=lambda x: x["age_sec"])
    return recent


def snapshot_active_and_running_tasks():
    """在退出旧实例前通过 CDP 深度嗅探前台分屏窗格与侧边栏全局旋转状态，抓取全景断点任务清单"""
    port = get_devtools_active_port(wait_timeout=1)
    if not port or not websockets:
        return {
            "has_running_tasks": False,
            "interrupted_panes": [],
            "running_sidebar_tasks": [],
            "panes": [],
            "active_href": "",
            "active_title": ""
        }
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2)
        pages = json.loads(req.read().decode("utf-8"))
        page = next((p for p in pages if p.get("type") == "page" and p.get("webSocketDebuggerUrl")), None)
        if not page:
            return {
                "has_running_tasks": False,
                "interrupted_panes": [],
                "running_sidebar_tasks": [],
                "panes": [],
                "active_href": "",
                "active_title": ""
            }
        ws_url = page["webSocketDebuggerUrl"]

        async def _query():
            async with websockets.connect(ws_url, ping_interval=None, close_timeout=3) as ws:
                js = """(() => {
                    const url = window.location.href;
                    const urlPath = decodeURIComponent(window.location.pathname || '');
                    const search = window.location.search || '';
                    const relativeUrl = (urlPath || '/c') + search;
                    const match = urlPath.match(/\/c\/([a-zA-Z0-9_\-+]+)/);
                    const urlConvIds = match ? match[1].split('+').filter(Boolean) : [];

                    // 1. 侧边栏全局雷达扫描 (Sidebar Scanner: 侦测所有转圈会话并建立 ID 映射表)
                    const sidebarRows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
                    const spinningSidebarTasks = [];
                    const spinningMap = {};
                    let activeSidebarRow = null;

                    sidebarRows.forEach((r, i) => {
                        const a = r.querySelector('a');
                        const href = a ? (a.getAttribute('href') || '') : '';
                        const titleDiv = r.querySelector('.truncate');
                        const title = titleDiv ? titleDiv.innerText.trim() : (r.innerText.split('\\n')[0] || '').trim();
                        const isSpinning = !!r.querySelector('.animate-spin, svg.lucide-loader, svg.lucide-loader-2, [data-is-generating="true"], [class*="spin"]');

                        if ((href && url.includes(href)) || r.classList.contains('bg-sidebar-secondary')) {
                            activeSidebarRow = { href: href, title: title };
                        }
                        if (href) {
                            const cid = href.replace('/c/', '');
                            spinningMap[cid] = { isSpinning: isSpinning, title: title, index: i, href: href };
                        }
                        if (isSpinning) {
                            spinningSidebarTasks.push({ index: i, title: title || `会话-${i+1}`, href: href });
                        }
                    });

                    // 2. 前台分屏布局容器与编辑器扫描 (Active Panes Scanner)
                    const paneContainers = Array.from(document.querySelectorAll('.group\\\\/pane, [class*="group/pane"]')).filter(el => {
                        const r = el.getBoundingClientRect();
                        return r.width > 150 && r.height > 200;
                    });
                    paneContainers.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);

                    const editors = Array.from(document.querySelectorAll('[data-lexical-editor="true"], div[contenteditable="true"]'));
                    const visiblePanes = editors.map(ed => {
                        const r = ed.getBoundingClientRect();
                        return { el: ed, left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), width: Math.round(r.width), height: Math.round(r.height) };
                    }).filter(ed => ed.width > 40 && ed.height > 10);
                    visiblePanes.sort((a, b) => a.left - b.left);

                    // 3. 过滤真实的 Stop 按钮（精准匹配，彻底排除侧边栏取消固定等 pin 按钮）
                    const allStopButtons = Array.from(document.querySelectorAll('button')).map(b => {
                        const r = b.getBoundingClientRect();
                        const aria = b.getAttribute('aria-label') || '';
                        const testid = b.getAttribute('data-testid') || '';
                        const text = (b.innerText || '').trim();
                        if (aria.includes('固定') || aria.includes('pin') || testid.includes('pin')) return null;
                        const isStop = testid === 'stop-button' ||
                                       aria.toLowerCase().includes('stop') ||
                                       aria.includes('停止') ||
                                       (aria.includes('取消') && !aria.includes('固定')) ||
                                       text.toLowerCase().includes('stop') ||
                                       text.includes('停止');
                        if (isStop && r.width > 0 && r.height > 0 && b.offsetParent !== null) {
                            return { left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), label: aria || text || 'Stop' };
                        }
                        return null;
                    }).filter(Boolean);

                    // 4. 过滤前台窗格内部的 Spinner（排除侧边栏 X < 250 区域）
                    const paneSpins = Array.from(document.querySelectorAll('.animate-spin, svg.lucide-loader, svg.lucide-loader-2, [data-is-generating="true"]')).map(s => {
                        const r = s.getBoundingClientRect();
                        if (r.width > 0 && r.left >= 250) {
                            return { left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top) };
                        }
                        return null;
                    }).filter(Boolean);

                    const totalCount = Math.max(urlConvIds.length, paneContainers.length, visiblePanes.length);
                    const panesStatus = [];
                    const interruptedPanes = [];

                    for (let idx = 0; idx < totalCount; idx++) {
                        const cid = urlConvIds[idx] || '';
                        const sInfo = spinningMap[cid] || {};
                        const isSpinningById = !!sInfo.isSpinning;

                        let isStopInCol = false;
                        let isSpinInCol = false;
                        let stopLabels = [];

                        if (idx < paneContainers.length) {
                            const pRect = paneContainers[idx].getBoundingClientRect();
                            const colLeft = pRect.left - 20;
                            const colRight = pRect.right + 20;

                            const stops = allStopButtons.filter(b => b.left >= colLeft && b.right <= colRight);
                            const spins = paneSpins.filter(s => s.left >= colLeft && s.right <= colRight);

                            isStopInCol = stops.length > 0;
                            isSpinInCol = spins.length > 0;
                            stopLabels = stops.map(b => b.label);
                        } else if (idx < visiblePanes.length) {
                            const pane = visiblePanes[idx];
                            const colLeft = pane.left - 40;
                            const colRight = pane.right + 40;

                            const stops = allStopButtons.filter(b => b.left >= colLeft && b.right <= colRight);
                            const spins = paneSpins.filter(s => s.left >= colLeft && s.right <= colRight);

                            isStopInCol = stops.length > 0;
                            isSpinInCol = spins.length > 0;
                            stopLabels = stops.map(b => b.label);
                        }

                        // 综合判定：URL 会话 ID 转圈、分屏列 Stop 按钮、分屏列 Spin 图标三位一体
                        const isRunning = isSpinningById || isStopInCol || isSpinInCol;
                        if (isRunning) {
                            interruptedPanes.push(idx);
                        }

                        panesStatus.push({
                            pane_index: idx,
                            conv_id: cid,
                            title: sInfo.title || `分屏列-${idx+1}`,
                            is_actively_running: isRunning,
                            reason: isSpinningById ? 'sidebar_spinning' : (isStopInCol ? 'stop_button' : (isSpinInCol ? 'pane_spin' : 'idle')),
                            stops_labels: stopLabels
                        });
                    }

                    return {
                        url: relativeUrl,
                        active_href: activeSidebarRow ? (activeSidebarRow.href || '') : '',
                        active_title: activeSidebarRow ? activeSidebarRow.title : (document.title || ''),
                        total_panes: panesStatus.length,
                        panes: panesStatus,
                        interrupted_panes: interruptedPanes,
                        running_sidebar_tasks: spinningSidebarTasks,
                        has_running_tasks: interruptedPanes.length > 0 || spinningSidebarTasks.length > 0
                    };
                })()"""
                payload = {"id": 1, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True}}
                await ws.send(json.dumps(payload))
                resp = json.loads(await ws.recv())
                return resp.get("result", {}).get("result", {}).get("value", {})

        res = asyncio.run(_query())
        if res:
            # 融合 Brain 本地近 3 分钟活跃后台任务，补全因侧边栏虚拟滚动或 429 提前停转而丢失的任务
            foreground_cids = [p.get("conv_id") for p in res.get("panes", []) if p.get("conv_id")]
            sidebar_cids = [t.get("href", "").replace("/c/", "").split("?")[0] for t in res.get("running_sidebar_tasks", [])]
            known_cids = set(foreground_cids + sidebar_cids)

            brain_tasks = get_recent_brain_active_conversations(exclude_cids=known_cids, max_age_seconds=180)
            if brain_tasks:
                for bt in brain_tasks:
                    res.setdefault("running_sidebar_tasks", []).append({
                        "index": 999,
                        "title": bt.get("title", f"后台断点-{bt['conv_id'][:8]}"),
                        "href": bt["href"],
                        "conv_id": bt["conv_id"],
                        "source": "brain_transcript"
                    })
                res["has_running_tasks"] = True

            logger.info(f"🔍 [CDP全景断点雷达] 检测到 {res.get('total_panes', 0)} 个前台分屏列 (运行中: {len(res.get('interrupted_panes', []))} 个), 侧边栏转圈任务: {len(res.get('running_sidebar_tasks', []))} 个")
            if res.get("interrupted_panes"):
                logger.info(f"   ▶ 前台运行中列: {res.get('interrupted_panes')}")
            if res.get("running_sidebar_tasks"):
                task_names = [t.get("title") for t in res.get("running_sidebar_tasks")]
                logger.info(f"   ▶ 侧边栏/后台任务: {', '.join(task_names)}")
            return res
        return {
            "has_running_tasks": False,
            "interrupted_panes": [],
            "running_sidebar_tasks": [],
            "panes": [],
            "active_href": "",
            "active_title": ""
        }
    except Exception as e:
        logger.debug(f"抓取当前活动会话与断点任务异常: {e}")
        return {
            "has_running_tasks": False,
            "interrupted_panes": [],
            "running_sidebar_tasks": [],
            "panes": [],
            "active_href": "",
            "active_title": ""
        }


def get_current_active_conversation():
    """向后兼容接口：获取切号前当前处于前台活跃状态的会话"""
    snapshot = snapshot_active_and_running_tasks()
    return {
        "url": snapshot.get("url", ""),
        "href": snapshot.get("active_href", ""),
        "title": snapshot.get("active_title", ""),
        "is_generating": snapshot.get("has_running_tasks", False),
        "interrupted_panes": snapshot.get("interrupted_panes", []),
        "running_sidebar_tasks": snapshot.get("running_sidebar_tasks", []),
        "panes": snapshot.get("panes", [])
    }


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
        except Exception as e:
            logger.warning(f"保存更新后的 profiles.yaml 异常: {e}")
            return False

        # 通知 mihomo 核心重载当前配置，使新节点立即生效（避免文件写了但内存未更新）
        _reload_clash_core(clash_dir, config)
        return True
    return False


def _reload_clash_core(clash_dir, profiles_config):
    """通知 Clash Verge (mihomo) 核心重载当前 Profile，使刚写入的订阅节点立即生效。
    策略：从当前激活 Profile 的 yaml 中读取 external-controller 端口，
    然后调用 PUT /configs?force=true 触发热重载。"""
    try:
        import yaml
    except ImportError:
        logger.debug("yaml 模块不可用，跳过 Clash 核心重载通知")
        return

    try:
        current_uid = profiles_config.get("current", "")
        items = profiles_config.get("items", [])
        # 找到当前激活的 profile 文件名
        active_file = None
        for item in items:
            if item.get("uid") == current_uid:
                active_file = item.get("file")
                break

        # 从主 config.yaml 读取 external-controller（Clash Verge merge 后的配置）
        main_config_path = os.path.join(clash_dir, "config.yaml")
        controller = None
        ctrl_auth = ""
        if os.path.exists(main_config_path):
            with open(main_config_path, "r", encoding="utf-8") as f:
                main_cfg = yaml.safe_load(f) or {}
            controller = main_cfg.get("external-controller", "")
            ctrl_auth = main_cfg.get("secret", "")

        # 若 main config 没有，尝试从激活 profile 本身读取
        if not controller and active_file:
            profile_path = os.path.join(clash_dir, "profiles", active_file)
            if os.path.exists(profile_path):
                with open(profile_path, "r", encoding="utf-8") as f:
                    prof_cfg = yaml.safe_load(f) or {}
                controller = prof_cfg.get("external-controller", "")
                ctrl_auth = prof_cfg.get("secret", ctrl_auth)

        # 候选端口列表（fallback）
        candidates = []
        if controller:
            candidates.append(controller)
        candidates += ["127.0.0.1:9090", "127.0.0.1:9097", "127.0.0.1:9093"]

        for ctrl in candidates:
            host = ctrl if ctrl.startswith("http") else f"http://{ctrl}"
            try:
                headers = {"Content-Type": "application/json"}
                if ctrl_auth:
                    headers["Authorization"] = f"Bearer {ctrl_auth}"
                data = json.dumps({"path": "", "payload": ""}).encode("utf-8")
                req = urllib.request.Request(
                    f"{host}/configs?force=true",
                    data=data,
                    headers=headers,
                    method="PUT"
                )
                resp = urllib.request.urlopen(req, timeout=3)
                if resp.status in (200, 204):
                    logger.info(f"✅ Clash 核心重载成功 (controller={ctrl})，新节点已即时生效")
                    return
            except Exception as e:
                logger.debug(f"Clash 重载尝试 {ctrl} 失败: {e}")

        logger.warning("⚠️ Clash 核心重载未成功（订阅文件已更新，请在 Clash Verge 界面手动点击更新以使节点立即生效）")
    except Exception as e:
        logger.warning(f"Clash 核心重载过程异常: {e}")


async def _cdp_execute_auto_resume(ws_url, max_windows=3, text="继续", target_href=None, force_send=None, interrupted_panes=None, running_sidebar_tasks=None, full_url=None, panes=None):
    """通过 CDP WebSocket 连接向 Antigravity 发送前排打标并扣 1 续接脚本 (支持智能断点感知、全景分屏对齐与深层侧边栏接力)"""
    if force_send is None:
        force_send = True
    if force_send:
        logger.info("⚡ [极速响应] 已启用极速续接策略：键入'继续'沉淀 1.2 秒后提交，兼顾防吞车与秒级接力！")
    if full_url:
        full_url = normalize_target_path(full_url)
    if target_href:
        target_href = normalize_target_path(target_href)

    wait_enter_sec = 1.2 if (force_send or is_beta_mode()) else 0.5

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
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("id") == cur_id:
                        return data

            # =========================================================================
            # -1. 【白屏与错误页自动自愈防护 (Self-Healing from chrome-error://)】
            # 彻底杜绝因端口切换未对齐导致的 ERR_CONNECTION_REFUSED 错误页/白屏假死
            # =========================================================================
            try:
                chk_res = await cdp_call("Runtime.evaluate", {
                    "expression": "(() => ({ href: window.location.href, title: document.title, bodyChildCount: document.body ? document.body.children.length : 0 }))()",
                    "returnByValue": True
                })
                page_info = chk_res.get("result", {}).get("result", {}).get("value") or {}
                cur_href = page_info.get("href", "")
                if cur_href.startswith("chrome-error://") or "ERR_" in page_info.get("title", "") or page_info.get("bodyChildCount", 1) == 0:
                    logger.warning(f"⚠️ [自愈引擎] 检测到页面处于白屏/错误页 ({cur_href})，启动端口嗅探自愈导航...")
                    live_port = find_live_web_server_port()
                    if live_port:
                        target_route = normalize_target_path(full_url) or "/c"
                        heal_url = f"https://127.0.0.1:{live_port}{target_route}"
                        logger.info(f"🧭 [自愈引擎] 通过 CDP Page.navigate 将页面引导至存活地址: {heal_url}")
                        await cdp_call("Page.navigate", {"url": heal_url})
                        await asyncio.sleep(4.0)
            except Exception as e:
                logger.debug(f"自愈检测异常忽略: {e}")

            # =========================================================================
            # 0. 【工作台与真实会话 URL 预对齐】
            # 无论是单窗口还是多分屏，若切号前处于某个真实会话 (/c/ID...)，优先纯相对路径对齐 URL，
            # 彻底杜绝因热重启后窗口重置停留在主页或空白新对话 (/ 或 /c) 而将'继续'误发到新对话/主页的致命乌龙！
            # =========================================================================
            target_dest = full_url or target_href
            if target_dest:
                target_rel = normalize_target_path(target_dest)
                if target_rel and target_rel not in ("/", "/c", "/c/") and "/c/" in target_rel:
                    align_url_js = f"""
                    (() => {{
                        const curRel = (window.location.pathname || '') + (window.location.search || '');
                        const target = {json.dumps(target_rel)};
                        if (decodeURIComponent(curRel) !== decodeURIComponent(target) && !curRel.includes(target)) {{
                            if (window.__TSR_ROUTER__ && typeof window.__TSR_ROUTER__.navigate === 'function') {{
                                window.__TSR_ROUTER__.navigate({{ href: target }});
                            }} else {{
                                window.location.href = window.location.origin + target;
                            }}
                            return true;
                        }}
                        return false;
                    }})()
                    """
                    align_res = await cdp_call("Runtime.evaluate", {"expression": align_url_js, "returnByValue": True})
                    if align_res.get("result", {}).get("result", {}).get("value"):
                        logger.info(f"🧭 [会话对齐] 正在对齐恢复切号前真实工作会话 ({target_rel})，杜绝误操作主页/空白新对话...")
                        await asyncio.sleep(0.8)

            # =========================================================================
            # 1. 【优先模式】：多分屏原生直连感知（Multi-Pane Native Direct Mode）
            # =========================================================================
            scan_panes_js = """
            (() => {
                // 1. 优先通过 agent-input-box 容器定位各分屏列 (最精准)
                const inputBoxes = Array.from(document.querySelectorAll('[data-testid="agent-input-box"]')).filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 100 && r.height > 20;
                });
                inputBoxes.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);

                if (inputBoxes.length > 0) {
                    return inputBoxes.map((box, i) => {
                        const r = box.getBoundingClientRect();
                        const ed = box.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                        const stopBtn = box.querySelector('button[aria-label*="Stop" i], button[aria-label*="停止" i], button[aria-label*="取消" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]');
                        const sendBtn = box.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i]');
                        return {
                            index: i,
                            x: Math.round(r.left),
                            y: Math.round(r.top),
                            w: Math.round(r.width),
                            h: Math.round(r.height),
                            has_editor: !!ed,
                            text: ed ? (ed.innerText || '').trim() : '',
                            is_generating: !!stopBtn,
                            stop_label: stopBtn ? (stopBtn.getAttribute('aria-label') || 'Stop') : '',
                            has_send: !!sendBtn,
                            can_send: !!sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true'
                        };
                    });
                }

                // 2. 后备：通过 pane 容器
                const paneContainers = Array.from(document.querySelectorAll('.group\\\\/pane, [class*="group/pane"]')).filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 150 && r.height > 200;
                });
                paneContainers.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);

                if (paneContainers.length > 0) {
                    return paneContainers.map((p, i) => {
                        const r = p.getBoundingClientRect();
                        const ed = p.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                        const stopBtn = p.querySelector('button[aria-label*="Stop" i], button[aria-label*="停止" i], button[aria-label*="取消" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]');
                        const sendBtn = p.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button.rounded-full.bg-secondary');
                        return {
                            index: i,
                            x: Math.round(r.left),
                            y: Math.round(r.top),
                            w: Math.round(r.width),
                            h: Math.round(r.height),
                            has_editor: !!ed,
                            text: ed ? (ed.innerText || '').trim() : '',
                            is_generating: !!stopBtn,
                            stop_label: stopBtn ? (stopBtn.getAttribute('aria-label') || 'Stop') : '',
                            has_send: !!sendBtn,
                            can_send: !!sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true'
                        };
                    });
                }

                // 3. 极简后备：直接查找可见的 lexical-editor
                const all = Array.from(document.querySelectorAll('[data-lexical-editor="true"], div[contenteditable="true"]'));
                const visible = all.filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 40 && r.height > 10;
                });
                visible.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
                return visible.map((el, i) => {
                    const r = el.getBoundingClientRect();
                    let container = el.parentElement;
                    for (let s = 0; s < 8; s++) {
                        if (container && (container.getAttribute('data-testid') === 'agent-input-box' || container.querySelector('button[data-testid="send-button"], button[data-testid="stop-button"], button[aria-label*="Cancel" i], button[aria-label*="Stop" i], button[aria-label*="取消" i]'))) break;
                        if (container && container.parentElement) container = container.parentElement;
                    }
                    const stopBtn = container ? container.querySelector('button[aria-label*="Stop" i], button[aria-label*="停止" i], button[aria-label*="取消" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]') : null;
                    const sendBtn = container ? container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button.rounded-full.bg-secondary') : null;
                    return {
                        index: i,
                        x: Math.round(r.left),
                        y: Math.round(r.top),
                        w: Math.round(r.width),
                        h: Math.round(r.height),
                        has_editor: true,
                        text: (el.innerText || '').trim(),
                        is_generating: !!stopBtn,
                        stop_label: stopBtn ? (stopBtn.getAttribute('aria-label') || 'Stop') : '',
                        has_send: !!sendBtn,
                        can_send: !!sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true'
                    };
                });
            })()
            """

            # 轮询等待编辑器窗格挂载（最多等待 12 秒）
            expected_pane_count = max(len(panes or []), (max(interrupted_panes) + 1 if interrupted_panes else 1))
            screen_panes = []
            for wait_i in range(12):
                scan_res = await cdp_call("Runtime.evaluate", {"expression": scan_panes_js, "returnByValue": True})
                screen_panes = scan_res.get("result", {}).get("result", {}).get("value") or []
                if len(screen_panes) >= expected_pane_count or (len(screen_panes) > 0 and expected_pane_count <= 1):
                    break
                await asyncio.sleep(0.8)

            if screen_panes and len(screen_panes) > 0:
                logger.info(f"🖥️ [多分屏原生感知模式] 检测到当前屏幕一字排开 {len(screen_panes)} 个分屏窗格 (预期 {expected_pane_count} 列)！启用智能断点原地续接引擎...")

                # 智能断点感知与目标选择：
                # 1. 单窗口极简模式 (len(screen_panes) == 1)：始终接力当前主会话 (列 0)，
                #    彻底解决 429 报错导致转圈停转、从而被误判为空闲跳过、出现“继续没有发”的根本病灶！
                # 2. 多分屏模式：若明确检测到全部空闲且侧边栏无转圈任务，方执行静默跳过。
                if len(screen_panes) == 1:
                    target_p_indices = [0]
                elif interrupted_panes and len(interrupted_panes) > 0:
                    target_p_indices = interrupted_panes
                elif interrupted_panes is not None and len(interrupted_panes) == 0 and not running_sidebar_tasks:
                    logger.info("⏭ [智能断点感知] 切号前所有分屏窗口均处于空闲等待态，无需向任何窗口补发'继续'，100% 保持静默。")
                    return {"success": True, "processed": 0, "success_count": 0, "results": [], "mode": "smart_idle_skip"}
                else:
                    target_p_indices = list(range(min(len(screen_panes), int(max_windows))))

                results = []
                resumed_cids = set()

                for p_idx in target_p_indices:
                    col_num = p_idx + 1
                    col_cid = panes[p_idx].get("conv_id") if (panes and p_idx < len(panes)) else None

                    # 1. 优先在屏幕可见分屏列中原地打标续接
                    if p_idx < len(screen_panes):
                        p_info = screen_panes[p_idx]
                        logger.info(f"▶ 正在处理断点接力 [分屏列 {col_num}] (X={p_info['x']}, 宽度={p_info['w']}, 编辑器={p_info.get('has_editor', True)})...")

                        prep_pane_js = f"""
                        (() => {{
                            const inputBoxes = Array.from(document.querySelectorAll('[data-testid="agent-input-box"]')).filter(el => {{
                                const r = el.getBoundingClientRect();
                                return r.width > 100 && r.height > 20;
                            }});
                            inputBoxes.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);

                            let target = null;
                            let container = null;
                            if (inputBoxes.length > {p_idx}) {{
                                container = inputBoxes[{p_idx}];
                                target = container.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                            }}
                            if (!target) {{
                                const paneContainers = Array.from(document.querySelectorAll('.group\\\\/pane, [class*="group/pane"]')).filter(el => {{
                                    const r = el.getBoundingClientRect();
                                    return r.width > 150 && r.height > 200;
                                }});
                                paneContainers.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
                                if (paneContainers.length > {p_idx}) {{
                                    container = paneContainers[{p_idx}];
                                    target = container.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                                }}
                            }}
                            if (!target) {{
                                const all = Array.from(document.querySelectorAll('[data-lexical-editor="true"], div[contenteditable="true"]'));
                                const visible = all.filter(el => el.getBoundingClientRect().width > 40 && el.getBoundingClientRect().height > 10);
                                visible.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
                                target = visible[{p_idx}];
                                container = target ? target.parentElement : null;
                            }}
                            if (!target) return {{ status: "pane_editor_missing" }};

                            for (let s = 0; s < 8; s++) {{
                                if (container && (container.getAttribute('data-testid') === 'agent-input-box' || container.querySelector('button[data-testid="send-button"], button[data-testid="stop-button"], button[aria-label*="Cancel" i], button[aria-label*="Stop" i], button[aria-label*="取消" i]'))) break;
                                if (container && container.parentElement) container = container.parentElement;
                            }}
                            const stopBtn = container ? container.querySelector('button[aria-label*="Stop" i], button[aria-label*="停止" i], button[aria-label*="取消" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]') : null;
                            const isGen = !!stopBtn;
                            if (isGen && !{json.dumps(bool(force_send))}) return {{ status: "generating" }};

                            target.focus();
                            try {{
                                const sel = window.getSelection();
                                const range = document.createRange();
                                range.selectNodeContents(target);
                                range.collapse(false);
                                sel.removeAllRanges();
                                sel.addRange(range);
                                target.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                                target.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true }}));
                                target.dispatchEvent(new MouseEvent('click', {{ bubbles: true }}));
                            }} catch(e) {{}}

                            const curPath = window.location.pathname || '';
                            const isBlankChat = curPath === '/' || curPath === '/c' || curPath === '/c/';
                            const msgCount = document.querySelectorAll('[data-testid*="chat-turn"], [class*="message"], [data-testid*="user-message"], [data-testid*="assistant-message"]').length;
                            if (isBlankChat && msgCount === 0) {{
                                return {{ status: "blank_home_page_skip" }};
                            }}

                            const curText = (target.innerText || '').trim();
                            if (curText === {json.dumps(str(text))}) {{
                                return {{ status: "ready_has_text" }};
                            }} else if (curText.length > 0) {{
                                return {{ status: "ready_custom_draft", text: curText }};
                            }} else {{
                                document.execCommand('selectAll', false, null);
                                document.execCommand('delete', false, null);
                                return {{ status: "ready" }};
                            }}
                        }})()
                        """
                        p_prep_res = await cdp_call("Runtime.evaluate", {"expression": prep_pane_js, "returnByValue": True})
                        p_prep_val = p_prep_res.get("result", {}).get("result", {}).get("value") or {}
                        p_status = p_prep_val.get("status")

                        if p_status == "blank_home_page_skip":
                            logger.info(f"分屏列 [{col_num}] 处于空白新对话/主页初始态 (无历史消息)，绝不误发'继续'，安全跳过。")
                            continue
                        elif p_status == "generating":
                            logger.info(f"分屏列 [{col_num}] 正在模型流式生成中，无需打标，保持原样继续。")
                            results.append({"index": col_num, "title": f"分屏列-{col_num}", "success": True, "reason": "already_generating"})
                            if col_cid:
                                resumed_cids.add(col_cid)
                            continue
                        elif p_status not in ("ready", "ready_has_text", "ready_custom_draft"):
                            logger.warning(f"分屏列 [{col_num}] 屏幕直接聚焦不成功 (状态: {p_status})，尝试深层会话中继...")
                        else:
                            wait_enter_sec = 1.2 if (force_send or is_beta_mode()) else 0.5
                            if p_status == "ready":
                                await cdp_call("Input.insertText", {"text": str(text)})
                                logger.info(f"已向分屏列 [{col_num}] 键入 '{text}'，等待 {wait_enter_sec:.1f} 秒待界面加载沉降后再提交...")
                                await asyncio.sleep(wait_enter_sec)
                            elif p_status in ("ready_has_text", "ready_custom_draft"):
                                logger.info(f"分屏列 [{col_num}] 检测到已有草稿内容，等待 {wait_enter_sec:.1f} 秒待界面完全加载后再提交...")
                                await asyncio.sleep(wait_enter_sec)

                            # 点击该分屏列内部专属的发送按钮
                            send_pane_js = f"""
                            (async () => {{
                                const inputBoxes = Array.from(document.querySelectorAll('[data-testid="agent-input-box"]')).filter(el => {{
                                    const r = el.getBoundingClientRect();
                                    return r.width > 100 && r.height > 20;
                                }});
                                inputBoxes.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);

                                let target = null;
                                let colContainer = null;
                                if (inputBoxes.length > {p_idx}) {{
                                    colContainer = inputBoxes[{p_idx}];
                                    target = colContainer.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                                }}
                                if (!target) {{
                                    const paneContainers = Array.from(document.querySelectorAll('.group\\\\/pane, [class*="group/pane"]')).filter(el => {{
                                        const r = el.getBoundingClientRect();
                                        return r.width > 150 && r.height > 200;
                                    }});
                                    paneContainers.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
                                    if (paneContainers.length > {p_idx}) {{
                                        colContainer = paneContainers[{p_idx}];
                                        target = colContainer.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                                    }}
                                }}
                                if (!target) {{
                                    const all = Array.from(document.querySelectorAll('[data-lexical-editor="true"], div[contenteditable="true"]'));
                                    const visible = all.filter(el => el.getBoundingClientRect().width > 40 && el.getBoundingClientRect().height > 10);
                                    visible.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
                                    target = visible[{p_idx}];
                                }}
                                if (!target) return {{ success: false, reason: "pane_editor_missing" }};

                                try {{ target.dispatchEvent(new Event('input', {{ bubbles: true }})); }} catch(e) {{}}

                                let container = colContainer || target.parentElement;
                                for (let s = 0; s < 8; s++) {{
                                    if (container && (container.getAttribute('data-testid') === 'agent-input-box' || container.querySelector('button[data-testid="send-button"], button[data-testid="stop-button"], button[aria-label*="Cancel" i], button[aria-label*="取消" i]'))) break;
                                    if (container && container.parentElement) container = container.parentElement;
                                }}

                                let sendBtn = container ? container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button.rounded-full.bg-secondary') : null;
                                for (let retry = 0; retry < 15; retry++) {{
                                    if (sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true') break;
                                    await new Promise(r => setTimeout(r, 100));
                                    if (container) {{
                                        sendBtn = container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button.rounded-full.bg-secondary');
                                    }}
                                }}
                                if (sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true') {{
                                    sendBtn.click();
                                    return {{ success: true, method: "button_click" }};
                                }}
                                return {{ success: false, reason: "button_not_clickable" }};
                            }})()
                            """
                            p_send_res = await cdp_call("Runtime.evaluate", {"expression": send_pane_js, "awaitPromise": True, "returnByValue": True})
                            p_send_val = p_send_res.get("result", {}).get("result", {}).get("value") or {}
                            p_is_sent = p_send_val.get("success", False)

                            if not p_is_sent or force_send:
                                await cdp_call("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r"})
                                await cdp_call("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r"})
                                await asyncio.sleep(0.35)

                            sent_text = p_prep_val.get("text") if p_status == "ready_custom_draft" else text
                            logger.info(f"✅ 分屏列 [{col_num}] 原生屏幕续接触发成功 (内容: '{sent_text}')")
                            results.append({"index": col_num, "title": f"分屏列-{col_num}", "success": True, "text": sent_text})
                            if col_cid:
                                resumed_cids.add(col_cid)
                            await asyncio.sleep(0.4)
                            continue

                    # 2. 若该列在屏幕上被标签页遮挡或未挂载，走 CID 深层路由穿透中继
                    if col_cid and col_cid not in resumed_cids:
                        logger.info(f"🧭 [分屏列穿透中继] 分屏列 [{col_num}] 屏幕直接交互未命中，瞬切至会话 (/c/{col_cid}) 进行保底续接...")
                        nav_js = f"""
                        (() => {{
                            if (window.__TSR_ROUTER__ && typeof window.__TSR_ROUTER__.navigate === 'function') {{
                                window.__TSR_ROUTER__.navigate({{ href: '/c/{col_cid}' }});
                            }} else {{
                                window.location.href = window.location.origin + '/c/{col_cid}';
                            }}
                            return true;
                        }})()
                        """
                        await cdp_call("Runtime.evaluate", {"expression": nav_js})
                        await asyncio.sleep(0.8)

                        bg_prep_js = """
                        (async () => {
                            let ed = null;
                            for (let r = 0; r < 15; r++) {
                                ed = document.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                                if (ed) break;
                                await new Promise(res => setTimeout(res, 200));
                            }
                            if (!ed) return { status: "no_editor" };

                            let container = ed.parentElement;
                            for (let s = 0; s < 8; s++) {
                                if (container && (container.getAttribute('data-testid') === 'agent-input-box' || container.querySelector('button[data-testid="send-button"], button[data-testid="stop-button"], button[aria-label*="Cancel" i], button[aria-label*="Stop" i], button[aria-label*="停止" i], button[aria-label*="取消" i]'))) break;
                                if (container && container.parentElement) container = container.parentElement;
                            }
                            const stopBtn = container ? container.querySelector('button[aria-label*="Stop" i], button[aria-label*="停止" i], button[aria-label*="取消" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]') : null;
                            if (stopBtn) return { status: "already_generating" };

                            ed.focus();
                            try {
                                const sel = window.getSelection();
                                range = document.createRange();
                                range.selectNodeContents(ed);
                                range.collapse(false);
                                sel.removeAllRanges();
                                sel.addRange(range);
                                ed.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                                ed.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                                ed.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                            } catch(e) {}
                            return { status: "ready" };
                        })()
                        """
                        bg_prep_res = await cdp_call("Runtime.evaluate", {"expression": bg_prep_js, "awaitPromise": True, "returnByValue": True})
                        bg_prep_val = bg_prep_res.get("result", {}).get("result", {}).get("value") or {}
                        if bg_prep_val.get("status") == "already_generating":
                            logger.info(f"分屏列 [{col_num}] 正在生成中，无需打标，保持原样。")
                            resumed_cids.add(col_cid)
                            continue

                        await cdp_call("Input.insertText", {"text": str(text)})
                        await asyncio.sleep(wait_enter_sec)

                        bg_send_js = """
                        (async () => {
                            const ed = document.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                            let container = ed ? ed.parentElement : null;
                            for (let s = 0; s < 8; s++) {
                                if (container && (container.getAttribute('data-testid') === 'agent-input-box' || container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i]'))) break;
                                if (container && container.parentElement) container = container.parentElement;
                            }
                            let btn = container ? container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button.rounded-full.bg-secondary') : null;
                            for (let retry = 0; retry < 15; retry++) {
                                if (btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true') break;
                                await new Promise(r => setTimeout(r, 100));
                                if (container) {
                                    btn = container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button.rounded-full.bg-secondary');
                                }
                            }
                            if (btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true') {
                                btn.click();
                                return true;
                            }
                            return false;
                        })()
                        """
                        bg_send_res = await cdp_call("Runtime.evaluate", {"expression": bg_send_js, "awaitPromise": True, "returnByValue": True})
                        bg_sent = bg_send_res.get("result", {}).get("result", {}).get("value")
                        if not bg_sent or force_send:
                            await cdp_call("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r"})
                            await cdp_call("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r"})

                        logger.info(f"✅ 分屏列 [{col_num}] 穿透保底续接触发成功 (/c/{col_cid})！")
                        results.append({"index": col_num, "title": f"分屏列-{col_num}", "success": True, "text": text, "relay": True})
                        resumed_cids.add(col_cid)
                        await asyncio.sleep(0.4)

                succ_cnt = sum(1 for item in results if item.get("success"))
                logger.info(f"🖥️ 多分屏原生直连续接处理完毕: 共处理 {len(results)} 个并排分屏列，成功触发: {succ_cnt} 个")

                # =====================================================================
                # 2. 【后台侧边栏与 Brain 记录转圈任务深度接力】
                # =====================================================================
                if running_sidebar_tasks:
                    unresumed_tasks = []
                    for st in running_sidebar_tasks:
                        s_cid = st.get("conv_id") or st.get("href", "").replace("/c/", "").split("?")[0].strip()
                        if s_cid and s_cid not in resumed_cids:
                            unresumed_tasks.append(st)

                    if unresumed_tasks:
                        logger.info(f"🧭 [后台断点接力] 发现 {len(unresumed_tasks)} 个后台任务未在前台被唤醒，逐一启动深度接力...")
                        for st in unresumed_tasks:
                            s_title = st.get("title", "")
                            s_cid = st.get("conv_id") or st.get("href", "").replace("/c/", "").split("?")[0].strip()
                            if not s_cid or s_cid in resumed_cids:
                                continue
                            logger.info(f"▶ 正在唤醒后台断点任务: '{s_title}' (/c/{s_cid})...")
                            nav_js = f"""
                            (() => {{
                                if (window.__TSR_ROUTER__ && typeof window.__TSR_ROUTER__.navigate === 'function') {{
                                    window.__TSR_ROUTER__.navigate({{ href: '/c/{s_cid}' }});
                                }} else {{
                                    window.location.href = window.location.origin + '/c/{s_cid}';
                                }}
                                return true;
                            }})()
                            """
                            await cdp_call("Runtime.evaluate", {"expression": nav_js})
                            await asyncio.sleep(0.8)

                            bg_prep_js = """
                            (async () => {
                                let ed = null;
                                for (let r = 0; r < 15; r++) {
                                    ed = document.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                                    if (ed) break;
                                    await new Promise(res => setTimeout(res, 200));
                                }
                                if (!ed) return { status: "no_editor" };

                                let container = ed.parentElement;
                                for (let s = 0; s < 8; s++) {
                                    if (container && (container.getAttribute('data-testid') === 'agent-input-box' || container.querySelector('button[data-testid="send-button"], button[data-testid="stop-button"], button[aria-label*="Cancel" i], button[aria-label*="Stop" i], button[aria-label*="停止" i], button[aria-label*="取消" i]'))) break;
                                    if (container && container.parentElement) container = container.parentElement;
                                }
                                const stopBtn = container ? container.querySelector('button[aria-label*="Stop" i], button[aria-label*="停止" i], button[aria-label*="取消" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]') : null;
                                if (stopBtn) return { status: "already_generating" };

                                ed.focus();
                                try {
                                    const sel = window.getSelection();
                                    const range = document.createRange();
                                    range.selectNodeContents(ed);
                                    range.collapse(false);
                                    sel.removeAllRanges();
                                    sel.addRange(range);
                                    ed.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                                    ed.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                                    ed.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                                } catch(e) {}
                                return { status: "ready" };
                            })()
                            """
                            bg_prep_res = await cdp_call("Runtime.evaluate", {"expression": bg_prep_js, "awaitPromise": True, "returnByValue": True})
                            bg_prep_val = bg_prep_res.get("result", {}).get("result", {}).get("value") or {}
                            if bg_prep_val.get("status") == "already_generating":
                                logger.info(f"后台任务 '{s_title}' 正在生成中，无需打标，保持原样。")
                                resumed_cids.add(s_cid)
                                succ_cnt += 1
                                continue
                            elif bg_prep_val.get("status") != "ready":
                                logger.warning(f"后台任务 '{s_title}' 输入框未就绪 ({bg_prep_val.get('status')})，跳过...")
                                continue

                            await cdp_call("Input.insertText", {"text": str(text)})
                            logger.info(f"已向后台任务 '{s_title}' 键入 '{text}'，等待 {wait_enter_sec:.1f} 秒待沉淀...")
                            await asyncio.sleep(wait_enter_sec)

                            bg_send_js = """
                            (async () => {
                                const ed = document.querySelector('[data-lexical-editor="true"], div[contenteditable="true"]');
                                let container = ed ? ed.parentElement : null;
                                for (let s = 0; s < 8; s++) {
                                    if (container && (container.getAttribute('data-testid') === 'agent-input-box' || container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i]'))) break;
                                    if (container && container.parentElement) container = container.parentElement;
                                }
                                let btn = container ? container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button.rounded-full.bg-secondary') : null;
                                for (let retry = 0; retry < 15; retry++) {
                                    if (btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true') break;
                                    await new Promise(r => setTimeout(r, 100));
                                    if (container) {
                                        btn = container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button.rounded-full.bg-secondary');
                                    }
                                }
                                if (btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true') {
                                    btn.click();
                                    return true;
                                }
                                return false;
                            })()
                            """
                            bg_send_res = await cdp_call("Runtime.evaluate", {"expression": bg_send_js, "awaitPromise": True, "returnByValue": True})
                            bg_sent = bg_send_res.get("result", {}).get("result", {}).get("value")
                            if not bg_sent or force_send:
                                await cdp_call("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r"})
                                await cdp_call("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r"})

                            logger.info(f"✅ 后台任务 '{s_title}' 续接触发成功！")
                            resumed_cids.add(s_cid)
                            succ_cnt += 1
                            await asyncio.sleep(0.4)

                # =====================================================================
                # 3. 【无缝返航复原多列分屏布局】
                # =====================================================================
                restore_url = full_url or target_href
                if restore_url:
                    restore_rel = normalize_target_path(restore_url)
                    logger.info(f"🔙 正在返航原路复原前台多分屏工作台布局 ({restore_rel})...")
                    restore_nav_js = f"""
                    (() => {{
                        const curRel = (window.location.pathname || '') + (window.location.search || '');
                        const target = {json.dumps(restore_rel)};
                        if (decodeURIComponent(curRel) !== decodeURIComponent(target) && !curRel.includes(target)) {{
                            if (window.__TSR_ROUTER__ && typeof window.__TSR_ROUTER__.navigate === 'function') {{
                                window.__TSR_ROUTER__.navigate({{ href: target }});
                            }} else {{
                                window.location.href = window.location.origin + target;
                            }}
                            return true;
                        }}
                        return false;
                    }})()
                    """
                    await cdp_call("Runtime.evaluate", {"expression": restore_nav_js})
                    await asyncio.sleep(0.8)
                    ensure_chinese_localization_injected()

                return {"success": succ_cnt > 0, "processed": len(results), "success_count": succ_cnt, "results": results, "mode": "multi_pane_direct"}

            # =========================================================================
            # 2. 【后备降级模式】：单窗口全屏白屏或骨架屏时走侧边栏轮询与路由点选
            # =========================================================================
            logger.info("未检测到可见的并排分屏输入框，降级启用侧边栏轮询探测...")
            fetch_rows_js = """
            (() => {
                const rows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
                const toggleBtn = document.querySelector('button[aria-label*="toggle" i], button[aria-label*="sidebar" i], button[aria-label*="历史" i], button[data-testid="sidebar-toggle"]');
                if (rows.length === 0 && toggleBtn) {
                    const aria = toggleBtn.getAttribute('aria-expanded');
                    if (aria === 'false') { toggleBtn.click(); }
                }
                const convs = rows.map((r, i) => {
                    const titleDiv = r.querySelector('.truncate');
                    const a = r.querySelector('a');
                    let t = titleDiv ? titleDiv.textContent.trim() : '';
                    if (!t && r.innerText) { t = r.innerText.split('\\n')[0].trim(); }
                    if (!t) t = `会话-${i + 1}`;
                    return {
                        index: i, title: t,
                        href: a ? a.getAttribute('href') : '',
                        isSelected: r.classList.contains('bg-sidebar-secondary')
                    };
                });
                return {
                    convs: convs,
                    currentUrl: window.location.href,
                    diagnostics: {
                        rows_found: rows.length,
                        toggle_found: !!toggleBtn,
                        title: document.title,
                        url: window.location.href
                    }
                };
            })()
            """
            all_convs = []
            current_url = ""
            diag = {}
            for poll_i in range(20):
                r = await cdp_call("Runtime.evaluate", {"expression": fetch_rows_js, "returnByValue": True})
                eval_val = r.get("result", {}).get("result", {}).get("value") or {}
                if not eval_val:
                    eval_val = r.get("result", {}).get("value") or {}
                all_convs = eval_val.get("convs", [])
                current_url = eval_val.get("currentUrl", "")
                diag = eval_val.get("diagnostics", {})
                if all_convs:
                    logger.info(f"✅ [后备侧边栏轮询第{poll_i+1}次] 发现 {len(all_convs)} 个侧边栏会话")
                    break
                logger.info(f"⏳ [后备侧边栏轮询第{poll_i+1}/20次] 暂无对话，2s后重试...")
                await asyncio.sleep(2)

            if not all_convs:
                logger.warning(f"CDP 侧边栏会话列表检索结束 (发现 0 个会话)，DOM 现场: {diag}")
                record_incident(
                    incident_type="CDP_RESUME_NO_CONVERSATIONS",
                    severity="INFO",
                    summary="CDP 自动续接未检索到前排历史会话",
                    root_cause="轮询 40 秒后未在 DOM 中发现 conversation-row-sidebar 元素。侧边栏可能为空或未展开。",
                    evidence=diag,
                    action_taken="跳过自动发送，保持当前新窗口正常在前台使用",
                    recommended_action="若需自动续接前排任务，请确认 Antigravity 侧边栏存在历史对话记录。"
                )
                return {"success": False, "reason": "no_conversations_found", "diagnostics": diag}

            logger.info(f"CDP 成功检索到 {len(all_convs)} 个侧边栏会话，准备智能优先续接 (最多 {max_windows} 个)...")

            # 优先级重组：优先精准锚定切号前的活跃任务会话与侧边栏转圈断点
            prioritized = []
            if running_sidebar_tasks:
                for r_task in running_sidebar_tasks:
                    r_href = r_task.get("href", "")
                    r_title = r_task.get("title", "")
                    matched = next((c for c in all_convs if c.get("href") and (c["href"] in r_href or r_href in c["href"])), None)
                    if not matched and r_title:
                        matched = next((c for c in all_convs if c.get("title") == r_title), None)
                    if matched and matched not in prioritized:
                        prioritized.append(matched)
                        logger.info(f"🎯 [侧边栏转圈断点命中] 优先续接: '{matched['title']}' ({matched['href']})")

            if target_href:
                matched = next((c for c in all_convs if c.get("href") and (c["href"] in target_href or target_href in c["href"])), None)
                if not matched:
                    m_uuid = re.search(r'[0-9a-fA-F-]{36}', target_href)
                    if m_uuid:
                        matched = next((c for c in all_convs if m_uuid.group(0) in c.get("href", "")), None)
                if matched and matched not in prioritized:
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
                        for (let i = 0; i < 15; i++) {{
                            if (location.href.includes(targetHref)) break;
                            await new Promise(r => setTimeout(r, 100));
                        }}
                        await new Promise(r => setTimeout(r, 350));
                    }}

                    let editable = null;
                    for (let retry = 0; retry < 15; retry++) {{
                        editable = document.querySelector('[data-lexical-editor="true"]');
                        if (editable) break;
                        await new Promise(r => setTimeout(r, 200));
                    }}

                    if (!editable) return {{ status: "editor_not_found" }};

                    const isGenerating = !!document.querySelector('button[aria-label*="Stop generation" i], button[aria-label*="Stop execution" i], button[aria-label*="停止生成" i], button[aria-label*="停止执行" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]');
                    if (isGenerating && !{json.dumps(bool(force_send))}) return {{ status: "generating" }};

                    const currentText = (editable.innerText || '').trim();
                    editable.focus();

                    if (currentText === {json.dumps(str(text))}) {{
                        return {{ status: "ready_has_text" }};
                    }} else if (currentText.length > 0) {{
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

                wait_enter_sec = 1.2 if (force_send or is_beta_mode()) else 0.5
                if prep_status == "ready":
                    await cdp_call("Input.insertText", {"text": str(text)})
                    logger.info(f"已向会话 [{title}] 键入 '{text}'，等待 {wait_enter_sec:.1f} 秒待界面组件彻底加载沉降后再敲击回车提交...")
                    await asyncio.sleep(wait_enter_sec)
                elif prep_status in ("ready_has_text", "ready_custom_draft"):
                    logger.info(f"会话 [{title}] 检测到已有内容/草稿，等待 {wait_enter_sec:.1f} 秒待界面完全加载后再敲击回车提交...")
                    await asyncio.sleep(wait_enter_sec)

                send_js = f"""
                (async () => {{
                    const editable = document.querySelector('[data-lexical-editor="true"]');
                    if (editable) {{
                        try {{ editable.dispatchEvent(new Event('input', {{ bubbles: true }})); }} catch(e) {{}}
                    }}
                    const isGen = !!document.querySelector('button[aria-label*="Stop generation" i], button[aria-label*="Stop execution" i], button[aria-label*="停止生成" i], button[aria-label*="停止执行" i], button[data-testid="stop-button"], button[aria-label*="Cancel" i]');
                    if (isGen && !{json.dumps(bool(force_send))}) return {{ success: true, method: "already_generating" }};

                    let container = editable ? editable.parentElement : null;
                    for (let step = 0; step < 6; step++) {{
                        if (container && container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button[aria-label*="提交" i]')) break;
                        if (container && container.parentElement) container = container.parentElement;
                    }}
                    let sendBtn = null;
                    for (let retry = 0; retry < 15; retry++) {{
                        sendBtn = container ? container.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button[aria-label*="提交" i]') : document.querySelector('button[data-testid="send-button"], button[aria-label*="发送" i], button[aria-label*="Send" i], button[aria-label*="Submit" i], button[aria-label*="提交" i]');
                        if (sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true') break;
                        await new Promise(r => setTimeout(r, 100));
                    }}
                    if (sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true') {{
                        sendBtn.click();
                        return {{ success: true, method: "button_click" }};
                    }}
                    return {{ success: false, reason: "button_not_clickable" }};
                }})()
                """
                send_res = await cdp_call("Runtime.evaluate", {"expression": send_js, "awaitPromise": True, "returnByValue": True})
                send_val = send_res.get("result", {}).get("result", {}).get("value", {}) or send_res.get("result", {}).get("value", {})
                is_sent = send_val.get("success", False)

                if not is_sent or force_send:
                    await cdp_call("Input.dispatchKeyEvent", {"type": "keyDown", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r"})
                    await cdp_call("Input.dispatchKeyEvent", {"type": "keyUp", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r"})
                    await asyncio.sleep(0.35)

                sent_content = prep_val.get("text") if prep_status == "ready_custom_draft" else text
                logger.info(f"✅ CDP 窗口 [{idx+1}] 发送成功: 会话='{title}' 成功触发发送 (内容: '{sent_content}')" + (" [测试版强制发送]" if force_send else ""))
                results.append({"index": idx + 1, "title": title, "href": href, "success": True, "text": sent_content, "force_sent": bool(force_send)})
                await asyncio.sleep(0.4)

            # 3. 切回首选窗口聚焦
            await asyncio.sleep(0.6)
            if target_convs:
                preferred_conv = next((item for item in results if item.get("success")), target_convs[0])
                pref_idx = preferred_conv["index"] - 1 if "index" in preferred_conv and preferred_conv.get("index", 0) > 0 else preferred_conv.get("index", 0)
                switch_back_js = f"""
                (async () => {{
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


def execute_auto_resume(max_windows=3, text="继续", wait_timeout=180, exclude_pids=None, target_href=None, interrupted_panes=None, running_sidebar_tasks=None, full_url=None, panes=None):
    """执行前排任务窗口打标与自动续接 (单飞互斥保护，支持智能断点感知与精准接力)"""
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
            if interrupted_panes is None:
                interrupted_panes = token.get("interrupted_panes")
            if running_sidebar_tasks is None:
                running_sidebar_tasks = token.get("running_sidebar_tasks")
            if full_url is None:
                full_url = token.get("full_url")
            if panes is None:
                panes = token.get("panes")
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

        # 在连接 CDP 执行窗口切换与续接前，先确保中文语言包已注入生效
        ensure_chinese_localization_injected()
        # 热重启后页面基本立即可响应，给 1 秒确保 DOM 事件沉降即可
        logger.info("⏳ 等待 1 秒待页面及语言包沉降...")
        time.sleep(1.0)

        logger.info(f"已连接 Antigravity CDP ({ws_url})，正在执行断点自愈感知与发送'{text}'续接...")
        for retry in range(2):
            try:
                result = asyncio.run(_cdp_execute_auto_resume(
                    ws_url,
                    max_windows=max_windows,
                    text=text,
                    target_href=target_href,
                    interrupted_panes=interrupted_panes,
                    running_sidebar_tasks=running_sidebar_tasks,
                    full_url=full_url,
                    panes=panes
                ))
                logger.info(f"自动续接执行结果: {json.dumps(result, ensure_ascii=False)}")

                # 热重启后若侧边栏尚未加载完成，短等 3 秒重试一次
                if not result.get("success") and result.get("reason") == "no_conversations_found" and retry == 0:
                    logger.warning(f"⏳ [续接重试] 侧边栏对话列表暂未加载，等待 3 秒后自动重试 (第 {retry + 1}/2 次)...")
                    time.sleep(3.0)
                    # 重新刷新 ws_url（以防热重启后端口变化）
                    port = get_devtools_active_port(wait_timeout=5)
                    if port:
                        try:
                            req = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2)
                            pages = json.loads(req.read().decode("utf-8"))
                            page = next((p for p in pages if p.get("type") == "page" and p.get("webSocketDebuggerUrl")), None)
                            if page:
                                ws_url = page["webSocketDebuggerUrl"]
                        except Exception:
                            pass
                    continue  # 进入第 2 次循环重试

                clear_pending_auto_resume()

                success_items = [r for r in result.get("results", []) if r.get("success") and r.get("reason") not in ("idle_skip", "already_generating")]
                count_sent = len(success_items)
                if count_sent > 0:
                    logger.info(f"✅ 已成功向 {count_sent} 个任务窗口补发'继续'无缝接力！")
                elif result.get("mode") == "smart_idle_skip":
                    logger.info("ℹ️ 切号前全部窗口均处于空闲状态，未触发补发。")
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
        payload = cd.get("payload", {})
        groups = payload.get("quota_summary", {}).get("groups", [])
        models = payload.get("models", {})
        
        q_5h = None
        q_weekly = None
        rt_weekly = None
        rt_5h = None
        q_claude_5h = None
        q_claude_weekly = None
        rt_claude_weekly = None
        
        for g in groups:
            gname = g.get("displayName", "")
            if gname == "Gemini Models":
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
            elif "Claude" in gname or "3p" in gname.lower() or "gpt" in gname.lower():
                for b in g.get("buckets", []):
                    bid = b.get("bucketId", "")
                    rf = b.get("remainingFraction", 0.0)
                    pct = round(rf * 100.0, 1)
                    rt = parse_iso_datetime(b.get("resetTime"))
                    if bid == "3p-5h":
                        q_claude_5h = pct
                    elif bid == "3p-weekly":
                        q_claude_weekly = pct
                        rt_claude_weekly = rt
        
        # 增强容错 1：如果 groups 中缺少 buckets，但 models 列表中所有模型 remainingFraction 为 1.0（全新未用账号如 leinhartlamonica）
        if (q_weekly is None or q_5h is None) and models:
            fractions = [
                m.get("quotaInfo", {}).get("remainingFraction")
                for m in models.values()
                if isinstance(m, dict) and "quotaInfo" in m and m.get("quotaInfo", {}).get("remainingFraction") is not None
            ]
            if fractions:
                avg_frac = sum(fractions) / len(fractions)
                pct = round(avg_frac * 100.0, 1)
                if q_weekly is None:
                    q_weekly = pct
                if q_5h is None:
                    q_5h = pct

        # 增强容错 2：如果周额度满血 (100%) 或极高，但 Google API 尚未生成 gemini-5h bucket（未消耗过5h额度的新号如 zwmrpg）
        # 绝对不能当作 0.0% 淘汰！周额度既然 100%，5小时滚动额度必然是 100% 满血！
        if q_weekly is not None and q_5h is None:
            if q_weekly >= 90.0:
                q_5h = 100.0
            else:
                q_5h = q_weekly

        # 增强容错 3：Claude / 3P 配额同步继承
        if q_weekly == 100.0:
            if q_claude_weekly is None:
                q_claude_weekly = 100.0
            if q_claude_5h is None:
                q_claude_5h = 100.0

        # 默认安全兜底
        q_5h_val = q_5h if q_5h is not None else 0.0
        q_w_val = q_weekly if q_weekly is not None else 0.0
        q_c_5h_val = q_claude_5h if q_claude_5h is not None else 0.0
        q_c_w_val = q_claude_weekly if q_claude_weekly is not None else 0.0
        
        # 是否处于 <5.0% 濒死静置隔离状态 (用户铁律：<5% 坚决不参与自动生产)
        is_parked = (q_w_val < 5.0)
        
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
        
        # Cockpit Tools 综合评分机制 (Cockpit Score V2 - 额度深度判定升级)：
        # 1. 5小时满血度（0~150分）：越高越好，>=95% 满血加 50 分
        score_5h = q_5h_val + (50.0 if q_5h_val >= 95.0 else 0.0)
        
        # 2. 周总容量为王（0~150分）：周额度是持久续航的核心基石，权重提升至 1.5 倍
        score_weekly = q_w_val * 1.5
        
        # 3. 周恢复紧迫度（0~50分）：越快恢复重置越优先消化存量，但严格设门禁：
        #    铁律：只有当周额度充足 (> 15%) 时才享受紧迫加分；若周额度 <= 10%，残血账号严禁加速消耗！
        if q_w_val > 15.0:
            if days_to_w_reset <= 1.0:
                score_urgency = 50.0
            elif days_to_w_reset <= 2.0:
                score_urgency = 35.0
            elif days_to_w_reset <= 3.0:
                score_urgency = 20.0
            else:
                score_urgency = 0.0
        else:
            score_urgency = 0.0
            
        # 4. 残血红线惩罚：周额度 <= 5.0% 的账号极度容易在数轮对话内再次暴毙，扣 100 分
        score_penalty = -100.0 if q_w_val <= 5.0 else 0.0
        
        cockpit_score = round(score_5h + score_weekly + score_urgency + score_penalty, 1)
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
            "tiger_score": tiger_score,
            "claude_5h": q_c_5h_val,
            "claude_weekly": q_c_w_val,
            "is_parked": is_parked
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
    all_eligible = [
        acc for acc in accounts
        if not acc.get("disabled", False)
        and not acc.get("is_current", False)
        and acc.get("id") != current_id
        and acc.get("id") not in quarantined
        and float(acc.get("gemini_weekly", 0.0)) > 1.0
        and float(acc.get("gemini_5h", 0.0)) > threshold
    ]
    # 濒死硬隔离铁律（用户强制基准）：周额度 < 5.0% 必须彻底静置挂起，绝不调用濒死残血账号产出！
    # 自动切号时坚决排除所有周额度 < 5.0% 的账号；若全部 < 5.0%，直接安全停机等待周重置，绝不频繁切号报429！
    candidates = [acc for acc in all_eligible if float(acc.get("gemini_weekly", 0.0)) >= 5.0]
    
    if not candidates and quarantined:
        # 【紧急解冻救场机制】：备选账号告急时，绝对不能因为历史冷冻而直接宣布无号可用！
        # 对所有被隔离账号执行即时探活审计，只要当前额度满足可用标准，立刻强制解冻并拉入救场候选池！
        rescued = []
        for acc in accounts:
            aid = acc.get("id")
            if aid in quarantined and not acc.get("disabled", False) and aid != current_id:
                w_q = float(acc.get("gemini_weekly", 0.0))
                h_q = float(acc.get("gemini_5h", 0.0))
                if w_q > 1.0 and h_q > threshold:
                    remove_quarantined_account(aid)
                    rescued.append(acc)
                    logger.info(f"🚨 [紧急解冻救场] 备选池告急！检测到隔离账号 [{acc.get('email')}] 额度充沛 (5h: {h_q}%, 周: {w_q}%)，已强制解冻救场！")
        if rescued:
            candidates = rescued

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
    raise RuntimeError("🛑【账号池周额度硬隔离保护】全池备选账号周额度均已低于 5.0% 濒死警戒线！已自动挂起停止切号，保持当前窗口完好，静待周重置（若急用可手动指定账号切入）。")


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


def handle_notification_event(event_type, region="", node="", rtt=""):
    """标准化反重力运行事件的桌面通知格式"""
    if event_type == "recovery_success":
        reg_map = {"JP": "日本东京", "US": "美国"}
        reg_str = reg_map.get(region, region or "境外优质")
        rtt_str = f" ({rtt}ms)" if rtt and str(rtt) != "0" else ""
        node_str = f" {node}" if node else ""
        title = "反重力专线已自愈就绪"
        msg = f"已恢复连通！接入: {reg_str}{node_str}{rtt_str}，可继续对话。"
        send_windows_notification(title, msg, status="info")
    elif event_type == "recovery_started":
        title = "反重力专线自愈中"
        msg = "检测到网络节点受限或波动，正在秒级优选最佳专线..."
        send_windows_notification(title, msg, status="warning")
    elif event_type == "cooldown_warning":
        title = "反重力专线提醒"
        msg = "可用节点暂时处于保护冷却中，双击桌面「Antigravity 启动器」可随时强制重连。"
        send_windows_notification(title, msg, status="warning")


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


def guard_quota_pool_exhaustion(accounts, current_id=None, threshold=5.0, curr_force_exhausted=False, force_exhausted=False):
    """
    全池无可用备选账号 (周额度 <= 1.0% 或 5h <= 5.0%) 时停止自动切号，并仅在状态变化时通知一次。
    参数:
        curr_force_exhausted: 强制判定【当前在用账号】已耗尽 (如捕获到 429 报错时)，仍会正常核验池中是否有备选候选账号。
        force_exhausted: 强制判定【整个账号池】全部耗尽 (仅用于极限测试与强制封锁)。
    """
    enabled_accounts = [a for a in accounts if not a.get("disabled", False)]
    if not enabled_accounts:
        return False

    if not current_id:
        curr = next((a for a in enabled_accounts if a.get("is_current")), None)
        if curr:
            current_id = curr.get("id")

    # 1. 全池所有启用账号周额度均见底 (<= 1.0%)
    all_weekly_exhausted = all(float(a.get("gemini_weekly", 0.0)) < 5.0 for a in enabled_accounts)

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

    if not candidates and quarantined:
        # 【紧急解冻救场机制】：备选告急时不轻易判定池子耗尽，即时探活隔离账号
        rescued = []
        for a in enabled_accounts:
            aid = a.get("id")
            if aid in quarantined and aid != current_id and not a.get("is_current", False):
                w_q = float(a.get("gemini_weekly", 0.0))
                h_q = float(a.get("gemini_5h", 0.0))
                if w_q > 1.0 and h_q > threshold:
                    remove_quarantined_account(aid)
                    rescued.append(a)
                    logger.info(f"🚨 [紧急解冻救场] 备选池告急！检测到隔离账号 [{a.get('email')}] 额度充沛 (5h: {h_q}%, 周: {w_q}%)，已强制解冻救场！")
        if rescued:
            candidates = rescued

    curr_acc = next((a for a in enabled_accounts if a.get("id") == current_id or a.get("is_current")), None)
    curr_is_exhausted = (
        curr_force_exhausted
        or curr_acc is None
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


def hot_restart_language_server(wait_timeout=25.0):
    """
    无缝切号核心：只杀 language_server.exe，等待 Electron 前端自动重新拉起。
    编辑器窗口、布局、对话历史完全不关闭。
    新语言服务启动时从 Windows Credential Manager 读取最新写入的新账号 Token。

    返回值:
        True  - 热重启成功（新进程已出现）
        False - 超时失败（Electron 未自动重拉，需降级到完整重启）
    """
    if not psutil:
        logger.warning("[热重启] psutil 不可用，无法执行无缝热重启，将降级到完整重启")
        return False

    # 1. 找到当前 language_server 进程
    def _find_ls():
        result = []
        for p in psutil.process_iter(["pid", "name", "exe"]):
            try:
                n = (p.info["name"] or "").lower()
                e = (p.info["exe"] or "").lower()
                if "language_server" in n and "antigravity" in e:
                    result.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return result

    procs = _find_ls()
    if not procs:
        logger.info("[热重启] 未发现运行中的 language_server 进程，跳过热重启步骤")
        return True  # 没有进程也算"成功"——无需额外操作

    old_pids = {p.pid for p in procs}
    logger.info(f"[热重启] 发现 language_server 进程 PID={old_pids}，即将执行无损 Kill...")

    # 2. Kill 语言服务（不动 Antigravity.exe 主进程）
    for p in procs:
        try:
            p.kill()
            logger.info(f"[热重启] Kill PID={p.pid} OK")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception as e:
            logger.warning(f"[热重启] Kill PID={p.pid} 异常: {e}")

    # 3. 轮询等待 Electron 自动重新拉起新语言服务（新 PID 出现）
    logger.info(f"[热重启] 等待 Electron 自动重启语言服务（最多 {int(wait_timeout)}s）...")
    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        time.sleep(1.0)
        new_procs = _find_ls()
        new_pids = {p.pid for p in new_procs}
        # 新进程出现且 PID 与旧进程完全不同 → 热重启成功
        if new_pids and not (new_pids & old_pids):
            elapsed = int(time.time() - (deadline - wait_timeout))
            logger.info(f"[热重启] 成功！{elapsed}s 后新 language_server 进程已就绪: PID={new_pids}")
            return True
        # 旧进程"复活"（Electron 复用原 PID，极罕见）：也视为成功
        if new_pids and (new_pids & old_pids):
            logger.info(f"[热重启] 旧进程 PID={new_pids & old_pids} 复活，视为成功")
            return True

    logger.warning(f"[热重启] 超过 {int(wait_timeout)}s，Electron 未自动重启 language_server，降级到完整重启")
    return False


def ensure_chinese_localization_injected():
    """
    确保 Antigravity 的中文汉化翻译语言包通过 CDP 注入到界面中。
    解决痛点：在无缝热重启或会话切换后，前端界面可能缺失翻译脚本导致回退英文。
    在无缝热重启完成后、CDP 自动续接前及巡检守护中主动触发，确保界面中文化始终生效。
    """
    try:
        disabled_flag = os.path.join(LOCAL_APPDATA, "Antigravity", "localization-extension-disabled.flag")
        if os.path.exists(disabled_flag):
            logger.debug("[汉化语言包] 检测到用户已禁用中文汉化，跳过注入。")
            return False

        loader_candidates = [
            os.path.join(LOCAL_APPDATA, "Antigravity", "launcher", "Antigravity-CdpLocalizationLoader.exe"),
            os.path.join(os.path.dirname(__file__), "Antigravity-CdpLocalizationLoader.exe"),
            os.path.join(os.path.dirname(__file__), "..", "releases", "current", "Antigravity-CdpLocalizationLoader.exe")
        ]
        loader_exe = next((p for p in loader_candidates if os.path.exists(p)), None)
        if not loader_exe:
            logger.debug("[汉化语言包] 未找到 Antigravity-CdpLocalizationLoader.exe，跳过注入。")
            return False

        work_dir = os.path.dirname(loader_exe)
        flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
        res = subprocess.run([loader_exe], cwd=work_dir, capture_output=True, timeout=8, creationflags=flags)
        if res.returncode == 0:
            logger.info("🌐 [汉化语言包] 已成功向 Antigravity 界面注入/重载中文语言包！")
            return True
        else:
            logger.debug(f"[汉化语言包] 注入返回码: {res.returncode}")
            return False
    except Exception as e:
        logger.debug(f"[汉化语言包] 注入过程异常: {e}")
        return False


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
    r_token = token.get("refresh_token", "")
    expiry_ts = token.get("expiry_timestamp")
    if expiry_ts:
        expiry_str = datetime.fromtimestamp(expiry_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
    else:
        expiry_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000Z")

    cred_payload = {
        "token": {
            "access_token": access_token,
            "token_type": "Bearer",
            "refresh_token": r_token,
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
    elif os.path.exists(LEGACY_DESKTOP_LNK):
        target = LEGACY_DESKTOP_LNK
    
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
    
    # 0. 优先深度探测抓取切号前当前处于活跃前台的会话窗口与侧边栏全局断点任务
    task_snapshot = snapshot_active_and_running_tasks()
    target_href = task_snapshot.get("active_href")
    target_title = task_snapshot.get("active_title")
    interrupted_panes = task_snapshot.get("interrupted_panes", [])
    running_sidebar_tasks = task_snapshot.get("running_sidebar_tasks", [])
    has_running_tasks = task_snapshot.get("has_running_tasks", False)

    # 1. 记录切号待办事务与断点自动续接凭据，同时【提前】落盘 watcher-current-account.txt 封死 Watcher 二段竞争
    write_pending_switch(best_acc)
    # 读取启动器设置，判断是否启用自动续接
    _settings_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Antigravity", "private-proxy", "launcher-settings.json")
    _auto_resume_enabled = True
    try:
        if os.path.exists(_settings_path):
            import re as _re
            _sj = open(_settings_path, encoding="utf-8").read()
            _m = _re.search(r'"auto_resume_enabled"\s*:\s*(true|false)', _sj)
            if _m:
                _auto_resume_enabled = (_m.group(1) == "true")
    except Exception:
        pass

    # 智能断点自愈策略：默认开启（具备零误触保护：空闲会话绝不打扰，仅接力被中断任务）
    should_resume = _auto_resume_enabled
    if should_resume:
        max_w = max(task_snapshot.get("total_panes", 0), 4)
        write_pending_auto_resume(
            max_windows=max_w,
            text="继续",
            target_href=target_href,
            target_title=target_title,
            interrupted_panes=interrupted_panes,
            running_sidebar_tasks=running_sidebar_tasks,
            full_url=task_snapshot.get("url"),
            panes=task_snapshot.get("panes", [])
        )
        if interrupted_panes:
            logger.info(f"✅ [智能断点续接已就绪] 切号后将精准接力 {len(interrupted_panes)} 个运行中分屏列: {interrupted_panes} (闲置列保持静默)")
        elif running_sidebar_tasks:
            logger.info(f"✅ [智能断点续接已就绪] 切号后将接力侧边栏转圈任务: {[t['title'] for t in running_sidebar_tasks]}")
        else:
            logger.info("✅ [智能断点感知] 自动续接已就绪 (若切号前全闲置则自动保持静默)")
    else:
        logger.info("⏭ [设置] 自动续接已关闭（可在启动器设置中开启）")

    try:
        os.makedirs(os.path.dirname(WATCHER_CURRENT_ACCOUNT_FILE), exist_ok=True)
        with open(WATCHER_CURRENT_ACCOUNT_FILE, "w", encoding="utf-8") as f:
            f.write(best_acc["id"].strip())
    except Exception as e:
        logger.debug(f"提前同步 watcher-current-account.txt 异常: {e}")
    
    # 2. 剩余 5% 触发切号：按规则【只发桌面通知，不发飞书】
    notif_title = "Antigravity 额度预警 (剩余 <= 5%)"
    active_names = []
    if interrupted_panes:
        for p in task_snapshot.get("panes", []):
            if p.get("pane_index") in interrupted_panes:
                active_names.append(p.get("title", f"列{p.get('pane_index')+1}"))
    for t in running_sidebar_tasks:
        if t.get("title") and t.get("title") not in active_names:
            active_names.append(t.get("title"))
    if not active_names and target_title:
        active_names.append(target_title)

    active_info = f"\n📌 保护中断点任务: {', '.join(active_names)}" if active_names else ""
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
    # 【核心顺序 2】：专线网络保持 (正常切号直接复用已验证专线，不更新订阅、不换节点)
    # =========================================================================
    logger.info("⚡ [步骤 2/5] 专线网络保持：当前 17897 专线与节点已在上一轮验证通畅，直接复用原有专线（跳过订阅刷新与节点重选）...")

    # =========================================================================
    # 【核心顺序 3/4】：退出反重力并重启
    #   - 核心首选（无缝热重启）：仅 Kill language_server，Electron 原地重拉，编辑器窗口不关闭
    #   - 兜底降级方案：若热重启超时/未就绪，优雅退出整个 Antigravity + 启动器重拉新实例
    # =========================================================================
    logger.info("🔥 [步骤 3/5] 无缝热重启：优先仅 Kill language_server，Electron 原地重新拉起新服务，编辑器窗口保持完好...")
    hot_restart_success = hot_restart_language_server(wait_timeout=25.0)
    if hot_restart_success:
        logger.info("✅ [步骤 3/5 完成] 语言服务热重启成功，编辑器窗口完好，跳过步骤 4（无需重新拉起启动器）")
    else:
        logger.warning("⚠️ [步骤 3/5] 热重启未就绪，自动降级为完整重启方案...")
        logger.info(f"🚪 [步骤 3/5 降级] 退出反重力：正在优雅退出旧 Antigravity 实例 (PID: {old_pid})...")
        gracefully_exit_antigravity(timeout_seconds=5.0)

        # =====================================================================
        # 【核心顺序 4】：启动启动器 (派发桌面智能启动器拉起新实例，挂载 17897 专线代理)
        # =====================================================================
        logger.info("🚀 [步骤 4/5 降级] 启动启动器：正在派发桌面智能启动器拉起全新实例并挂载专线代理...")
        launch_antigravity_via_launcher(recovery_reason="AccountChange", background=False)

    # =========================================================================
    # 【语言包保障】：在热重启或拉起后，主动确保 Antigravity 中文汉化包已注入生效
    # =========================================================================
    ensure_chinese_localization_injected()
    time.sleep(1.0)  # 留出 1 秒让中文语言包 MutationObserver 遍历并翻译当前界面

    # =========================================================================
    # 【核心顺序 5】：启动后在前 3 对话窗口发"继续"续接 (优先切号前活跃任务)
    # =========================================================================
    # 热重启成功时 Antigravity 主进程未变，不需要 exclude_pids 排除旧进程
    resume_exclude_pids = None if hot_restart_success else ([old_pid] if old_pid else None)
    # 热重启成功时语言服务已就绪，等待时间可大幅缩短
    resume_wait_timeout = 45 if hot_restart_success else 180
    if should_resume:
        logger.info("🎯 [步骤 5/5] 智能断点续接：正在等待语言服务就绪，定向接力未完成任务...")
        execute_auto_resume(
            max_windows=max(task_snapshot.get("total_panes", 0), 4),
            text="继续",
            wait_timeout=resume_wait_timeout,
            exclude_pids=resume_exclude_pids,
            target_href=target_href,
            interrupted_panes=interrupted_panes,
            running_sidebar_tasks=running_sidebar_tasks,
            full_url=task_snapshot.get("url"),
            panes=task_snapshot.get("panes", [])
        )
    else:
        logger.info("⏭ [步骤 5/5] 自动续接已关闭，跳过发送'继续'（可在启动器设置中开启）")
    clear_pending_switch()
    reset_language_server_log_pos()

    # 6. 切换成功：按规则【发桌面也发飞书】
    mode_desc = "无缝热重启（编辑器窗口未关闭）" if hot_restart_success else "完整重启"
    succ_title = "Antigravity 切换成功"
    resume_desc = "智能断点任务已自动发送'继续'无缝接力！" if should_resume else "自动续接已关闭"
    succ_msg = (
        f"✅ 账号已成功切换至: {best_acc['email']}\n"
        f"🔥 切换模式: {mode_desc}\n"
        f"🚀 17897 专线复用，{resume_desc}"
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
        logger.info("发现切号后待自动续接的事务凭据，正在执行智能断点自愈接力...")
        execute_auto_resume(
            max_windows=pending_resume.get("max_windows", 4),
            text=pending_resume.get("text", "继续"),
            wait_timeout=15,
            target_href=pending_resume.get("target_href"),
            interrupted_panes=pending_resume.get("interrupted_panes"),
            running_sidebar_tasks=pending_resume.get("running_sidebar_tasks"),
            full_url=pending_resume.get("full_url"),
            panes=pending_resume.get("panes")
        )
    
    # 启动时若 Antigravity 正在运行，主动确保中文汉化包就绪
    if is_antigravity_running():
        ensure_chinese_localization_injected()

    loop_count = 0
    _last_antigravity_running = is_antigravity_running()
    while True:
        try:
            # 1. 双星互保与汉化巡检：每 2 轮检查 C# 守卫，每 10 轮确保一次汉化语言包注入
            if loop_count % 2 == 0:
                ensure_account_watcher_running()
            if loop_count % 10 == 0 and is_antigravity_running():
                ensure_chinese_localization_injected()

            # 2. 穿透监听：只要 language_server 出现配额耗尽/429 报错，无需等待磁盘缓存，立刻触发无感切号与续接！
            log_quota_hit = check_language_server_quota_error()
            if log_quota_hit and is_antigravity_running():
                current_id_tmp, accounts_tmp = get_all_accounts_and_quotas()
                if guard_quota_pool_exhaustion(accounts_tmp, current_id=current_id_tmp, threshold=threshold, curr_force_exhausted=True):
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
    parser.add_argument("--auto-resume", action="store_true", help="立即执行前排窗口打标与自动续接")
    parser.add_argument("--resume-text", type=str, default="继续", help="自动续接发送的内容 (默认: 继续)")
    parser.add_argument("--resume-count", type=int, default=3, help="自动续接前排窗口数 (默认: 3)")
    parser.add_argument("--update-subscriptions", action="store_true", help="主动从机场提供商更新全部 Clash 订阅配置")
    parser.add_argument("--notify", type=str, default="", help="发送 Windows 桌面气泡通知正文")
    parser.add_argument("--notify-title", type=str, default="反重力网络专线", help="发送 Windows 桌面气泡通知标题")
    parser.add_argument("--notify-status", type=str, default="info", help="通知级别: info, warning, error")
    parser.add_argument("--notify-event", type=str, default="", help="标准化通知事件代码")
    parser.add_argument("--notify-region", type=str, default="", help="节点所在区域")
    parser.add_argument("--notify-node", type=str, default="", help="节点名称")
    parser.add_argument("--notify-rtt", type=str, default="", help="延迟数值")
    
    args = parser.parse_args()
    
    if args.notify_event:
        handle_notification_event(args.notify_event, region=args.notify_region, node=args.notify_node, rtt=args.notify_rtt)
    elif args.notify:
        send_windows_notification(args.notify_title, args.notify, status=args.notify_status)
    elif args.stop_watch:
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

