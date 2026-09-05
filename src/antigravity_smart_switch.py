# -*- coding: utf-8 -*-
"""
Antigravity Smart Account Switcher & Smooth Launcher
=====================================================
小老虎专属切号规则 (Tiger Rules):
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

LAUNCHER_EXE = os.path.join(LOCAL_APPDATA, "Antigravity", "launcher", "Antigravity-Recovery-Launcher.exe")
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
        
        # 小老虎综合评分机制 (Tiger Score)：
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
        
        tiger_score = round(score_5h + score_urgency + score_weekly, 1)
        
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
        # 按小老虎综合评分降序排列
        candidates.sort(key=lambda x: x["tiger_score"], reverse=True)
        best = candidates[0]
        reason = (
            f"小老虎综合优选 [得分: {best['tiger_score']}]：5小时满血({best['gemini_5h']}%)，"
            f"周恢复时间仅剩 {best['days_to_w_reset']}天 (优先消化即将到期额度)，周额度剩余 {best['gemini_weekly']}%"
        )
        return best, reason
    
    # 兜底选择非零可用账号
    fallback = [
        acc for acc in accounts
        if not acc["disabled"] and not acc["is_current"] and acc["effective_quota"] > 0
    ]
    if fallback:
        fallback.sort(key=lambda x: x["tiger_score"], reverse=True)
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


def launch_antigravity_via_launcher():
    target = None
    if os.path.exists(LAUNCHER_EXE):
        target = LAUNCHER_EXE
    elif os.path.exists(DESKTOP_LNK):
        target = DESKTOP_LNK
    
    if not target:
        raise FileNotFoundError(f"未找到启动器文件: {LAUNCHER_EXE}")
    
    logger.info(f"正在拉起桌面智能启动器: {target} ...")
    subprocess.Popen([target], shell=True)
    logger.info("✅ 启动器已拉起，自动挂载 17897 专线代理 + 模型自愈 + 汉化扩展！")


def run_smart_switch(threshold=5.0, target=None, dry_run=False, force=False):
    current_id, accounts = get_all_accounts_and_quotas()
    curr_acc = next((a for a in accounts if a["is_current"]), None)
    curr_email = curr_acc["email"] if curr_acc else "未知"
    curr_effective = curr_acc["effective_quota"] if curr_acc else 0.0
    
    logger.info("=" * 65)
    logger.info(f"当前反重力账号: {curr_email} (有效额度: {curr_effective}%)")
    logger.info("账号池实时小老虎健康度看板:")
    for acc in accounts:
        marker = " <== [当前在用]" if acc["is_current"] else ""
        print(f"  * {acc['email']:28} | 有效: {acc['effective_quota']:5.1f}% | 5h: {acc['gemini_5h']:5.1f}% | 周额: {acc['gemini_weekly']:5.1f}% (剩{acc['days_to_w_reset']:3.1f}天) | 虎分: {acc['tiger_score']:5.1f}{marker}")
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
    
    # 1. 优雅退出 Antigravity
    gracefully_exit_antigravity()
    
    # 2. 读取 Cockpit 端口并切号
    server_info = load_cockpit_server_info()
    ok = asyncio.run(switch_account_via_websocket(server_info, best_acc["id"]))
    if not ok:
        logger.error("切号失败，中断启动流程！")
        return
    
    logger.info(f"账号凭证写入完成，新账号: {best_acc['email']}")
    
    # 3. 启动桌面启动器
    launch_antigravity_via_launcher()


def print_status_table():
    current_id, accounts = get_all_accounts_and_quotas()
    curr_acc = next((a for a in accounts if a["is_current"]), None)
    print("\n" + "=" * 80)
    print(f"【小老虎 Antigravity 账号池配额与恢复排期看板】 当前在用: {curr_acc['email'] if curr_acc else '无'}")
    print("=" * 80)
    print(f"{'序号':<3} {'账号邮箱':<28} {'有效额度':<9} {'5小时限额':<10} {'周限额':<8} {'周恢复倒计时':<12} {'小老虎分':<8} {'状态'}")
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
        print(f"{i:<3} {acc['email']:<28} {acc['effective_quota']:>5.1f}%   {acc['gemini_5h']:>6.1f}%    {acc['gemini_weekly']:>5.1f}%     剩 {acc['days_to_w_reset']:>4.1f} 天    {acc['tiger_score']:>6.1f}   {status}")
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


def run_watch_daemon(threshold=5.0, interval=30):
    os.makedirs(os.path.dirname(DAEMON_LOG_FILE), exist_ok=True)
    file_handler = logging.FileHandler(DAEMON_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(file_handler)
    
    # 互斥锁防止多个 Watcher 重复运行
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        mutex_name = "Local\\AntigravitySmartQuotaWatcher"
        kernel32.CreateMutexW(None, False, mutex_name)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            logger.info("已存在运行中的【小老虎自动续航守护神】实例，静默退出当前多余实例。")
            return
            
    logger.info("=" * 65)
    logger.info("🚀 【小老虎无人值守自动续航守护神】已就绪！")
    logger.info(f"   * 自动切号阈值: <= {threshold}%")
    logger.info(f"   * 巡检轮询周期: {interval} 秒")
    logger.info(f"   * 守护日志路径: {DAEMON_LOG_FILE}")
    logger.info("=" * 65)
    
    loop_count = 0
    while True:
        try:
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
                        logger.warning("🚀 正在无感启动自愈接力闭环：优雅关闭 -> 智能优选满血号 -> 写入凭据 -> 专线拉起置顶")
                        logger.warning("!" * 65)
                        
                        send_windows_notification(
                            "Antigravity 自动续命守护",
                            f"当前账号额度已降至 {curr_effective:.1f}%，正在自动平滑切换下一个满血账号并无感重启..."
                        )
                        
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
    parser = argparse.ArgumentParser(description="Antigravity 智能切号与平滑重启工具 (小老虎规则版)")
    parser.add_argument("--threshold", type=float, default=5.0, help="自动切号配额百分比阈值 (默认: 5.0)")
    parser.add_argument("--target", type=str, default=None, help="指定切换的目标账号 (邮箱或 ID)")
    parser.add_argument("--dry-run", action="store_true", help="演练模式，仅计算选号不实际执行")
    parser.add_argument("--force", action="store_true", help="忽略当前额度强制触发切号")
    parser.add_argument("--status", action="store_true", help="仅打印所有账号的当前配额状态与排期看板")
    parser.add_argument("--watch", action="store_true", help="启动无人值守看门狗守护进程模式")
    parser.add_argument("--interval", type=int, default=30, help="守护巡检轮询间隔秒数 (默认: 30)")
    parser.add_argument("--stop-watch", action="store_true", help="停止正在运行的看门狗守护进程")
    
    args = parser.parse_args()
    
    if args.stop_watch:
        stop_watch_daemon()
    elif args.watch:
        run_watch_daemon(threshold=args.threshold, interval=args.interval)
    elif args.status:
        print_status_table()
    else:
        run_smart_switch(
            threshold=args.threshold,
            target=args.target,
            dry_run=args.dry_run,
            force=args.force
        )


if __name__ == "__main__":
    main()
