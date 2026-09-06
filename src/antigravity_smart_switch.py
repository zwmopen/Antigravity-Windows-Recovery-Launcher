# -*- coding: utf-8 -*-
"""
Antigravity Smart Account Switcher & Smooth Launcher
=====================================================
CCOCK专属切号规则 (CCOCK Rules):
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
import time
import json
import asyncio
import logging
import argparse
import subprocess
import base64
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone

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
COCKPIT_DIR = os.path.join(USER_PROFILE, ".antigravity_cockpit")
ACCOUNTS_FILE = os.path.join(COCKPIT_DIR, "accounts.json")
SERVER_FILE = os.path.join(COCKPIT_DIR, "server.json")
QUOTA_CACHE_DIR = os.path.join(COCKPIT_DIR, "cache", "quota_api_v1_desktop", "authorized")
DAEMON_LOG_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "smart-quota-watcher.log")
PENDING_SWITCH_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "pending-switch.json")
PENDING_AUTO_RESUME_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "pending-auto-resume.json")
SUBSCRIPTION_REPORT_FILE = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy", "subscription-report.json")
DEVTOOLS_PORT_FILE = os.path.join(os.environ.get("APPDATA", os.path.join(USER_PROFILE, "AppData", "Roaming")), "Antigravity", "DevToolsActivePort")
LANGUAGE_SERVER_LOG = os.path.join(os.environ.get("APPDATA", os.path.join(USER_PROFILE, "AppData", "Roaming")), "Antigravity", "logs", "language_server.log")

LAUNCHER_EXE = os.path.join(LOCAL_APPDATA, "Antigravity", "launcher", "Antigravity-Recovery-Launcher.exe")
ACCOUNT_WATCHER_EXE = os.path.join(LOCAL_APPDATA, "Antigravity", "launcher", "Antigravity-AccountWatcher.exe")
DESKTOP_LNK = os.path.join(USER_PROFILE, "Desktop", "Antigravity 启动器.lnk")


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
        with open(SUBSCRIPTION_REPORT_FILE, "r", encoding="utf-8") as f:
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


def write_pending_auto_resume(max_windows=3, text="1"):
    """写入自动续接待办事务凭据 (5分钟 TTL 单次令牌)"""
    try:
        os.makedirs(os.path.dirname(PENDING_AUTO_RESUME_FILE), exist_ok=True)
        with open(PENDING_AUTO_RESUME_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "action": "auto_resume",
                "text": text,
                "max_windows": max_windows,
                "timestamp": time.time(),
                "created_at": datetime.now().isoformat(),
                "ttl_seconds": 300,
                "status": "pending"
            }, f, indent=2)
        logger.info(f"已写入大任务断点自动续接凭据 (前排 {max_windows} 个窗口，扣 '{text}')")
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
        time.sleep(0.5)
    return None


async def _cdp_execute_auto_resume(ws_url, max_windows=3, text="1"):
    """通过 CDP WebSocket 连接向 Antigravity 发送前排打标并扣 1 续接脚本"""
    import websockets
    async with websockets.connect(ws_url, ping_interval=None) as ws:
        script_template = """
        (async () => {
            const maxCount = __MAX_WINDOWS__;
            const resumeText = __RESUME_TEXT__;

            // 动态轮询等待侧边栏会话列表加载渲染完成 (最多等待 15 秒)
            let rows = [];
            for (let retry = 0; retry < 30; retry++) {
                rows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
                if (rows.length > 0) break;
                // 若侧边栏可能处于折叠状态，在第 3 次重试时自动尝试点击展开侧边栏
                if (retry === 3) {
                    const toggleBtn = document.querySelector('button[aria-label*="sidebar" i], button[aria-label*="Sidebar" i], button[aria-label*="侧边栏" i]');
                    if (toggleBtn) {
                        toggleBtn.click();
                        await new Promise(r => setTimeout(r, 600));
                        rows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
                        if (rows.length > 0) break;
                    }
                }
                await new Promise(r => setTimeout(r, 500));
            }

            if (rows.length === 0) {
                return { success: false, reason: "no_conversations_found" };
            }

            // 纯物理序：直接抓取当前侧边栏排在最前面的前 N 个会话 (0, 1, 2)
            const targetCount = Math.min(maxCount, rows.length);
            const topSessionInfos = [];

            for (let i = 0; i < targetCount; i++) {
                const row = rows[i];
                const titleDiv = row.querySelector('.truncate');
                const rawTitle = titleDiv ? titleDiv.textContent.trim() : '未知会话';
                topSessionInfos.push({
                    rank: i + 1,
                    title: rawTitle,
                    href: (row.querySelector('a') || {}).getAttribute ? row.querySelector('a').getAttribute('href') : null
                });
            }

            // 2. 依次切换到实时最新的前排窗口并扣 1 发送
            const results = [];
            for (let i = 0; i < targetCount; i++) {
                const row = rows[i];
                const info = topSessionInfos[i];
                const a = row.querySelector('a');
                const href = info.href;
                if (!a) {
                    results.push({ index: i + 1, title: info.title, success: false, reason: "no_anchor" });
                    continue;
                }

                a.click();
                await new Promise(r => setTimeout(r, 800));

                const stopBtn = document.querySelector('button[aria-label*="Stop"], button[data-testid*="stop"]');
                if (stopBtn) {
                    results.push({ index: i + 1, title: info.title, href: href, skipped: true, reason: "task_running" });
                    continue;
                }

                const editable = document.querySelector('[data-lexical-editor="true"]');
                if (!editable) {
                    results.push({ index: i + 1, title: info.title, href: href, success: false, reason: "editor_not_found" });
                    continue;
                }

                const currentText = (editable.textContent || '').trim();
                if (currentText.length > 0 && currentText !== resumeText) {
                    results.push({ index: i + 1, title: info.title, href: href, skipped: true, reason: "draft_exists" });
                    continue;
                }

                editable.focus();
                document.execCommand('insertText', false, resumeText);
                await new Promise(r => setTimeout(r, 200));

                const sendBtn = document.querySelector('button[data-testid="send-button"]');
                if (sendBtn && !sendBtn.disabled) {
                    sendBtn.click();
                    results.push({ index: i + 1, title: info.title, href: href, success: true, text: resumeText });
                } else {
                    results.push({ index: i + 1, title: info.title, href: href, success: false, reason: "send_button_disabled" });
                }

                await new Promise(r => setTimeout(r, 600));
            }

            // 3. 切回第 1 个窗口聚焦
            if (rows.length > 0) {
                const firstLink = rows[0].querySelector('a');
                if (firstLink) firstLink.click();
            }

            return {
                success: true,
                processed: results.length,
                results: results
            };
        })()
        """
        script = script_template.replace("__MAX_WINDOWS__", str(int(max_windows))).replace("__RESUME_TEXT__", json.dumps(str(text)))
        req = {
            "id": 101,
            "method": "Runtime.evaluate",
            "params": {
                "expression": script,
                "awaitPromise": True,
                "returnByValue": True
            }
        }
        await ws.send(json.dumps(req))
        resp = await ws.recv()
        data = json.loads(resp)
        return data.get("result", {}).get("result", {}).get("value", {})


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


def execute_auto_resume(max_windows=3, text="1", wait_timeout=60, exclude_pids=None):
    """执行前排 1/2/3 窗口打标与自动扣 1 续接任务"""
    if websockets is None:
        logger.warning("未检测到 websockets 模块，无法通过 CDP 执行自动续接。")
        return False

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

    logger.info(f"已连接 Antigravity CDP ({ws_url})，正在执行前排 {max_windows} 个窗口打标与扣 '{text}' 续接...")
    try:
        result = asyncio.run(_cdp_execute_auto_resume(ws_url, max_windows=max_windows, text=text))
        logger.info(f"自动续接执行结果: {json.dumps(result, ensure_ascii=False)}")
        
        clear_pending_auto_resume()
        
        success_items = [r for r in result.get("results", []) if r.get("success")]
        count_sent = len(success_items)
        send_windows_notification(
            "CCOCK 选号引擎 · 断点自动续接",
            f"已定位前排最新 1/2/3 任务窗口！\n成功在 {count_sent} 个窗口自动扣 '1' 继续推进，已平滑切回主窗口！"
        )
        return True
    except Exception as e:
        logger.warning(f"执行自动续接发生异常: {e}")
        return False


def load_cockpit_server_info():
    if not os.path.exists(SERVER_FILE):
        raise FileNotFoundError(f"Cockpit server.json 未找到: {SERVER_FILE} (Cockpit Tools 是否已运行?)")
    with open(SERVER_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "ws_port": data.get("ws_port", 19528),
        "auth_token": data.get("auth_token", ""),
        "pid": data.get("pid", 0)
    }


def get_all_accounts_and_quotas():
    if not os.path.exists(ACCOUNTS_FILE):
        raise FileNotFoundError(f"Cockpit accounts.json 未找到: {ACCOUNTS_FILE}")
    
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
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
                    with open(p, "r", encoding="utf-8") as cf:
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
        
        # 有效额度：取 5小时与周额度中较小值（周额度见底则整号瘫痪）
        effective = min(q_5h_val, q_w_val)
        
        # 周恢复重置时间计算（剩余天数与秒数）
        if rt_weekly:
            sec_to_w_reset = max(0.0, (rt_weekly - now).total_seconds())
            days_to_w_reset = round(sec_to_w_reset / 86400.0, 1)
        else:
            sec_to_w_reset = 7.0 * 86400.0
            days_to_w_reset = 7.0
        
        # CCOCK综合评分机制 (CCOCK Score)：
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
        
        ccock_score = round(score_5h + score_urgency + score_weekly, 1)
        tiger_score = ccock_score
        
        results.append({
            "id": acc_id,
            "email": email,
            "name": name,
            "disabled": disabled,
            "is_current": is_current,
            "gemini_5h": q_5h_val,
            "gemini_weekly": q_w_val,
            "reset_time_weekly": rt_weekly,
            "days_to_w_reset": days_to_w_reset,
            "sec_to_w_reset": sec_to_w_reset,
            "effective_quota": effective,
            "score_5h": score_5h,
            "score_urgency": score_urgency,
            "score_weekly": score_weekly,
            "ccock_score": ccock_score,
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
    
    # 门禁过滤（注意事项3）：
    # 1. 排除当前在用与已禁用账号；
    # 2. 周额度 <= 5% 必须一票否决淘汰（周额度耗尽则无法工作）；
    # 3. 5小时额度 <= 5% 必须一票否决淘汰。
    candidates = [
        acc for acc in accounts
        if not acc["disabled"]
        and not acc["is_current"]
        and acc["gemini_weekly"] > threshold
        and acc["gemini_5h"] > threshold
    ]
    
    if candidates:
        # 按 CCOCK 选号引擎综合评分降序排列
        candidates.sort(key=lambda x: x["ccock_score"], reverse=True)
        best = candidates[0]
        reason = (
            f"CCOCK选号引擎优选 [得分: {best['ccock_score']}]：5小时满血({best['gemini_5h']}%)，"
            f"周恢复时间仅剩 {best['days_to_w_reset']}天 (优先消化即将到期额度)，周额度剩余 {best['gemini_weekly']}%"
        )
        return best, reason
    
    # 兜底选择非零可用账号
    fallback = [
        acc for acc in accounts
        if not acc["disabled"] and not acc["is_current"] and acc["effective_quota"] > 0
    ]
    if fallback:
        fallback.sort(key=lambda x: x["ccock_score"], reverse=True)
        best = fallback[0]
        return best, f"兜底选择非零剩余额度账号 ({best['effective_quota']}%)"
    
    raise RuntimeError("当前所有备选账号的 5小时或周额度均已耗尽，无法自动切换！")


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


def send_windows_notification(title, message):
    if sys.platform != "win32":
        return
    try:
        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $True
$n.ShowBalloonTip(6000, '{title}', '{message}', [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 6
$n.Dispose()
"""
        encoded = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-EncodedCommand", encoded],
            creationflags=0x08000000 if sys.platform == "win32" else 0
        )
    except Exception as e:
        logger.debug(f"发送系统通知异常: {e}")


def gracefully_exit_antigravity(timeout_seconds=3.5):
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


async def switch_account_via_websocket(server_info, target_account_id, timeout=10.0):
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
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
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
                break
    
    time.sleep(1.0)
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        curr = json.load(f).get("current_account_id")
        if curr == target_account_id:
            logger.info("校验 accounts.json 确认当前账号已更新成功。")
            return True
    
    return False


def launch_antigravity_via_launcher(recovery_reason="cockpit_account_changed"):
    target = None
    if os.path.exists(LAUNCHER_EXE):
        target = LAUNCHER_EXE
    elif os.path.exists(DESKTOP_LNK):
        target = DESKTOP_LNK
    
    if not target:
        raise FileNotFoundError(f"未找到启动器文件: {LAUNCHER_EXE}")
    
    logger.info(f"正在以脱壳独立进程拉起桌面智能启动器: {target} (reason={recovery_reason}) ...")
    flags = 0
    if sys.platform == "win32":
        # 彻底脱壳：脱离当前控制台、父进程 Job Object 与进程树
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        CREATE_BREAKAWAY_FROM_JOB = 0x01000000
        flags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS | CREATE_BREAKAWAY_FROM_JOB
    
    try:
        if target.endswith(".exe"):
            subprocess.Popen(
                [target, "--background", f"--recovery-reason={recovery_reason}"],
                creationflags=flags,
                close_fds=True
            )
        else:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "", target],
                creationflags=flags,
                close_fds=True
            )
        logger.info("✅ 脱壳启动器已拉起，将无感平滑切换实例并挂载 17897 专线代理 + 模型自愈 + 汉化扩展！")
    except Exception as e:
        logger.warning(f"脱壳拉起启动器异常，执行备用方式: {e}")
        subprocess.Popen([target], shell=True)


def run_smart_switch(threshold=5.0, target=None, dry_run=False, force=False):
    current_id, accounts = get_all_accounts_and_quotas()
    curr_acc = next((a for a in accounts if a["is_current"]), None)
    curr_email = curr_acc["email"] if curr_acc else "未知"
    curr_effective = curr_acc["effective_quota"] if curr_acc else 0.0
    sub_summary = get_subscription_summary()
    
    logger.info("=" * 65)
    logger.info(f"当前反重力账号: {curr_email} (有效额度: {curr_effective}%)")
    logger.info(f"专线网络订阅状态: {sub_summary}")
    logger.info("账号池实时 CCOCK 选号引擎健康度看板:")
    for acc in accounts:
        marker = " <== [当前在用]" if acc["is_current"] else ""
        print(f"  * {acc['email']:28} | 有效: {acc['effective_quota']:5.1f}% | 5h: {acc['gemini_5h']:5.1f}% | 周额: {acc['gemini_weekly']:5.1f}% (剩{acc['days_to_w_reset']:3.1f}天) | CCOCK分: {acc['ccock_score']:5.1f}{marker}")
    logger.info("=" * 65)
    
    if not force and not target and curr_effective > threshold:
        logger.info(f"当前账号有效配额 ({curr_effective}%) 高于阈值 ({threshold}%)，无需切号。使用 --force 可强制切换。")
        return
    
    best_acc, reason = select_best_account(accounts, current_id, threshold=threshold, target_email_or_id=target)
    logger.info(f"🎯 【优选目标】: {best_acc['email']} (ID: {best_acc['id']})")
    logger.info(f"📋 【决策理由】: {reason}")
    
    if dry_run:
        logger.info("[DryRun 演练模式] 未执行实际退出与切号操作。")
        return
    
    # 1. 记录切号待办事务与大任务断点自动续接凭据，确保断电或重启后可自愈闭环
    write_pending_switch(best_acc)
    write_pending_auto_resume(max_windows=3, text="1")
    
    # 2. 发送气泡通知 (告知用户正在全自动接力无感切号)
    send_windows_notification(
        "CCOCK 自动续航守护神",
        f"当前账号额度已降至 {curr_effective:.1f}%，已优选下一个满血账号: {best_acc['email']}\n正在全自动写入凭据并无感平滑重启..."
    )
    
    old_pid = get_antigravity_main_pid()

    # 3. 在线通过 WebSocket 写入 Cockpit 凭据 (无损写入凭据并更新 accounts.json)
    server_info = load_cockpit_server_info()
    ok = asyncio.run(switch_account_via_websocket(server_info, best_acc["id"]))
    if not ok:
        logger.error("向 Cockpit 发送切号指令失败，取消本次切换！")
        clear_pending_switch()
        clear_pending_auto_resume()
        return
    
    logger.info(f"✅ Cockpit 账号凭证与 accounts.json 已更新成功！新账号: {best_acc['email']}")
    
    # 3.5 凭据写入成功后，立即优雅退出旧实例，释放锁并彻底避免在专线探测自愈期间遭遇 400 Location 报错
    gracefully_exit_antigravity(timeout_seconds=3.0)

    # 4. 派发脱壳启动器进行平滑重启与专线恢复 (由启动器接管候选探测与新实例拉起)
    launch_antigravity_via_launcher(recovery_reason="AccountChange")
    
    # 5. 等待新实例真正就绪 (排除旧 PID)，并自动续接前排 1/2/3 窗口 (扣 1)
    logger.info("切号指令已派发，正在等待新实例就绪并自动续接前排窗口 (扣 1)...")
    execute_auto_resume(max_windows=3, text="1", wait_timeout=60, exclude_pids=[old_pid] if old_pid else None)
    clear_pending_switch()


def print_status_table():
    current_id, accounts = get_all_accounts_and_quotas()
    curr_acc = next((a for a in accounts if a["is_current"]), None)
    sub_summary = get_subscription_summary()
    print("\n" + "=" * 80)
    print(f"【CCOCK选号引擎 Antigravity 账号池配额与恢复排期看板】")
    print(f"当前在用: {curr_acc['email'] if curr_acc else '无'} | 专线网络订阅: {sub_summary}")
    print("=" * 80)
    print(f"{'序号':<3} {'账号邮箱':<28} {'有效额度':<9} {'5小时限额':<10} {'周限额':<8} {'周恢复倒计时':<12} {'CCOCK分':<8} {'状态'}")
    print("-" * 80)
    for i, acc in enumerate(accounts, 1):
        if acc["is_current"]:
            status = "★ 当前在用"
        elif acc["gemini_weekly"] <= 5.0:
            status = "✕ 周额度耗尽"
        elif acc["gemini_5h"] <= 5.0:
            status = "✕ 5h额度耗尽"
        else:
            status = "✔ 健康待命"
        print(f"{i:<3} {acc['email']:<28} {acc['effective_quota']:>5.1f}%   {acc['gemini_5h']:>6.1f}%    {acc['gemini_weekly']:>5.1f}%     剩 {acc['days_to_w_reset']:>4.1f} 天    {acc['ccock_score']:>6.1f}   {status}")
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
    """穿透监听 language_server.log，毫秒级感知 429 / RESOURCE_EXHAUSTED / quota 耗尽报错"""
    global _last_language_log_pos
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
            # 文件被重建或轮转
            _last_language_log_pos = 0
            
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
                logger.warning(f"🚨 [实时日志穿透感知] 在 language_server.log 捕获到模型额度耗尽特征: '{pat}'！")
                return True
    except Exception as e:
        logger.debug(f"检查 language_server 日志异常: {e}")
        
    return False


def run_watch_daemon(threshold=5.0, interval=30):
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
            logger.info("已存在运行中的【CCOCK无人值守自动续航守护神】实例，静默退出当前多余实例。")
            return
        _global_mutex_handle = handle
            
    sub_summary = get_subscription_summary()
    logger.info("=" * 65)
    logger.info("🚀 【CCOCK无人值守自动续航守护神】已就绪！(双星互保脱壳常驻模式)")
    logger.info(f"   * 自动切号阈值: <= {threshold}%")
    logger.info(f"   * 巡检轮询周期: {interval} 秒")
    logger.info(f"   * 专线网络订阅: {sub_summary}")
    logger.info(f"   * 守护日志路径: {DAEMON_LOG_FILE}")
    logger.info("=" * 65)
    
    # 开机或守护启动自愈：检查是否存在未闭环的待切事务
    pending = read_pending_switch()
    if pending and (time.time() - pending.get("timestamp", 0) > 10):
        logger.info(f"发现未闭环的切号待办事务 (目标: {pending.get('target_email')})，正在自动补发自愈拉起...")
        launch_antigravity_via_launcher(recovery_reason="cockpit_account_changed")
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
    while True:
        try:
            # 1. 双星互保：每 2 轮 (约 60 秒) 检查一次 C# 守卫存活状态
            if loop_count % 2 == 0:
                ensure_account_watcher_running()

            # 2. 穿透监听：只要 language_server 出现配额耗尽/429 报错，无需等待磁盘缓存，立刻触发无感切号与续接！
            log_quota_hit = check_language_server_quota_error()
            if log_quota_hit and is_antigravity_running():
                logger.warning("!" * 65)
                logger.warning("🚀 【实时日志报错触发】捕获到模型 429/配额耗尽异常！立刻启动全自动无感自愈续航闭环！")
                logger.warning("!" * 65)
                run_smart_switch(threshold=threshold, force=True)
                logger.info("自愈切换指令已下发，休眠 35 秒等待新实例完全就绪...")
                time.sleep(35)
                loop_count = 0
                continue

            # 3. 常规磁盘配额轮询
            if is_antigravity_running():
                current_id, accounts = get_all_accounts_and_quotas()
                curr_acc = next((a for a in accounts if a["is_current"]), None)
                if curr_acc:
                    curr_effective = curr_acc["effective_quota"]
                    curr_email = curr_acc["email"]
                    
                    if loop_count % 10 == 0:
                        logger.info(
                            f"[巡检心跳] Antigravity 运行中 | 当前在用: {curr_email} | "
                            f"有效额度: {curr_effective:.1f}% (5h: {curr_acc['gemini_5h']:.1f}%, 周: {curr_acc['gemini_weekly']:.1f}%)"
                        )
                    
                    if curr_effective <= threshold:
                        logger.warning("!" * 65)
                        logger.warning(
                            f"⚠️ 【阈值触发】当前账号 {curr_email} 有效额度打至阈值 ({curr_effective:.1f}% <= {threshold}%)！"
                        )
                        logger.warning("🚀 正在启动CCOCK全自动无感自愈续航闭环：在线写凭据 -> 脱壳拉起启动器 -> 平滑置顶")
                        logger.warning("!" * 65)
                        
                        run_smart_switch(threshold=threshold, force=True)
                        
                        logger.info("自愈切换指令已下发，休眠 35 秒等待新实例完全就绪...")
                        time.sleep(35)
                        loop_count = 0
                        continue
            else:
                if loop_count % 20 == 0:
                    logger.debug("[巡检挂起] 未检测到 Antigravity 运行实例，处于低耗待命模式...")
        except Exception as e:
            logger.warning(f"巡检发生异常 (将在下一周期自动重试): {e}")
        
        loop_count += 1
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Antigravity 智能切号与平滑重启工具 (CCOCK选号引擎版)")
    parser.add_argument("--threshold", type=float, default=5.0, help="自动切号配额百分比阈值 (默认: 5.0)")
    parser.add_argument("--target", type=str, default=None, help="指定切换的目标账号 (邮箱或 ID)")
    parser.add_argument("--dry-run", action="store_true", help="演练模式，仅计算选号不实际执行")
    parser.add_argument("--force", action="store_true", help="忽略当前额度强制触发切号")
    parser.add_argument("--status", action="store_true", help="仅打印所有账号的当前配额状态与排期看板")
    parser.add_argument("--watch", action="store_true", help="启动无人值守看门狗守护进程模式")
    parser.add_argument("--interval", type=int, default=30, help="守护巡检轮询间隔秒数 (默认: 30)")
    parser.add_argument("--stop-watch", action="store_true", help="停止正在运行的看门狗守护进程")
    parser.add_argument("--auto-resume", action="store_true", help="立即执行前排窗口打标与扣1自动续接")
    parser.add_argument("--resume-text", type=str, default="1", help="自动续接发送的内容 (默认: 1)")
    parser.add_argument("--resume-count", type=int, default=3, help="自动续接前排窗口数 (默认: 3)")
    
    args = parser.parse_args()
    
    if args.stop_watch:
        stop_watch_daemon()
    elif args.watch:
        run_watch_daemon(threshold=args.threshold, interval=args.interval)
    elif args.status:
        print_status_table()
    elif args.auto_resume:
        execute_auto_resume(max_windows=args.resume_count, text=args.resume_text, wait_timeout=5)
    else:
        run_smart_switch(
            threshold=args.threshold,
            target=args.target,
            dry_run=args.dry_run,
            force=args.force
        )


if __name__ == "__main__":
    main()
