# -*- coding: utf-8 -*-
"""
antigravity_switcher_gui.py — Antigravity 管理面板 (Neumorphic & Liquid Glass Edition)
基于 CustomTkinter 构建的现代化、呼吸感软拟态与液态玻璃桌面中枢：
1. 视觉风格 (Neumorphic & Liquid Glass)：
   - 彻底告别生硬矩形块，全控件 100% 圆角 (corner_radius 14~20)，悬浮微拟态卡片与呼吸感间距
   - 1:1 对齐《人生游戏系统》与《团队工作台》三套同源设计系统：
     🎨 拟态浅色 (#e0e5ec / #4d5b6d / #3b82f6)
     💧 液态玻璃 (#eaf4fd / #f4f9ff / #0284c7)
     🌙 拟态深色 (#1e1e2e / #f4f4f5 / #38bdf8)
2. 交互逻辑 (智能 5 秒倒计时 & 自愈拉起)：
   - 若客户端已在运行：5 秒未操作自动平滑激活主窗口
   - 若客户端未运行：5 秒未操作自动执行网络自愈、挂载专线并拉起客户端 (跑网络/测速/自愈全流程)
   - 任何交互 (点击、按键、切换 Tab) 瞬间暂停倒计时并永久常驻
3. 信息命名 (极简纯粹，绝不花里胡哨)：
   - 三大 Tab 直观命名：【账号】、【网络】、【日志】
   - 核心功能按键精炼命名：【⚡ 智能盲切】、【🔄 切换账号】、【🔓 解除隔离】、【💬 恢复会话】等
"""

import os
import sys
import glob
import re
import json
import subprocess
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import ctypes
try:
    myappid = "antigravity.studio.gui.ctk.v6"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def attach_desktop():
    try:
        user32 = ctypes.windll.user32
        hwinsta = user32.OpenWindowStationW('winsta0', False, 0x037F)
        if hwinsta:
            user32.SetProcessWindowStation(hwinsta)
        hdesk = user32.OpenDesktopW('default', 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

attach_desktop()

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

LAUNCHER_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\launcher")
PROXY_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\private-proxy")
DEV_SRC_DIR = r"D:\AICode\工具开发\projects\antigravity-recovery-launcher\src"

for d in [LAUNCHER_DIR, DEV_SRC_DIR]:
    if os.path.exists(d) and d not in sys.path:
        sys.path.insert(0, d)

from antigravity_smart_switch import (
    get_all_accounts_and_quotas,
    run_smart_switch,
    unblock_account,
    get_devtools_active_port,
    is_antigravity_running,
    launch_antigravity_via_launcher,
    execute_auto_resume,
    get_subscription_summary,
)

ICON_CANDIDATES = [
    os.path.join(LAUNCHER_DIR, "Antigravity-Launcher.ico"),
    os.path.join(LAUNCHER_DIR, "antigravity_network.ico"),
    r"D:\AICode\tools\ai-compute-hub\ai-compute-hub.ico",
]
ICON_PATH = next((p for p in ICON_CANDIDATES if os.path.exists(p)), None)

THEME_CONFIG_FILE = Path(os.path.expanduser("~/.antigravity_cockpit/hub_theme_config.json"))
SETTINGS_FILE = os.path.join(PROXY_DIR, "launcher-settings.json")

# 人生游戏系统 & 团队工作台 1:1 同源高阶设计系统
THEMES = {
    "neo": {
        "id": "neo",
        "name": "拟态浅色",
        "icon": "🎨",
        "appearance": "Light",
        "bg": "#e0e5ec",
        "panel": "#e0e5ec",
        "card": "#e0e5ec",
        "card_border": "#c8d4e2",
        "ink": "#4d5b6d",
        "muted": "#7a8b9e",
        "primary": "#3b82f6",
        "primary_hover": "#2563eb",
        "primary_fg": "#ffffff",
        "restart_btn": "#3d4856",
        "restart_hover": "#2e3742",
        "restart_fg": "#ffffff",
        "btn_sec_bg": "#e0e5ec",
        "btn_sec_border": "#ffffff",
        "btn_sec_hover": "#d6dee7",
        "btn_sec_fg": "#4d5b6d",
        "tree_bg": "#e8edf4",
        "tree_even": "#e8edf4",
        "tree_odd": "#e0e5ec",
        "tree_fg": "#4d5b6d",
        "tree_heading_bg": "#d4dfea",
        "tree_heading_fg": "#374151",
        "active_row": "#d4e4f7",
        "active_row_fg": "#1d4ed8",
        "select_bg": "#bfdbfe",
        "select_fg": "#1e3a8a",
        "toast_bg": "#dbeafe",
        "toast_fg": "#1d4ed8",
        "toast_border": "#93c5fd",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#e11d48",
    },
    "glass": {
        "id": "glass",
        "name": "液态玻璃",
        "icon": "💧",
        "appearance": "Light",
        "bg": "#eaf4fd",
        "panel": "#f4f9ff",
        "card": "#ffffff",
        "card_border": "#dae8f5",
        "ink": "#24364c",
        "muted": "#5e738c",
        "primary": "#0284c7",
        "primary_hover": "#0369a1",
        "primary_fg": "#ffffff",
        "restart_btn": "#1e293b",
        "restart_hover": "#0f172a",
        "restart_fg": "#ffffff",
        "btn_sec_bg": "#ffffff",
        "btn_sec_border": "#dae8f5",
        "btn_sec_hover": "#e0f2fe",
        "btn_sec_fg": "#24364c",
        "tree_bg": "#ffffff",
        "tree_even": "#ffffff",
        "tree_odd": "#f4f9ff",
        "tree_fg": "#24364c",
        "tree_heading_bg": "#e1effa",
        "tree_heading_fg": "#0369a1",
        "active_row": "#dbeafe",
        "active_row_fg": "#0369a1",
        "select_bg": "#bae6fd",
        "select_fg": "#0c4a6e",
        "toast_bg": "#e0f2fe",
        "toast_fg": "#0369a1",
        "toast_border": "#7dd3fc",
        "success": "#059669",
        "warning": "#d97706",
        "danger": "#e11d48",
    },
    "midnight": {
        "id": "midnight",
        "name": "拟态深色",
        "icon": "🌙",
        "appearance": "Dark",
        "bg": "#1e1e2e",
        "panel": "#252538",
        "card": "#252538",
        "card_border": "#2d2d42",
        "ink": "#f4f4f5",
        "muted": "#a3b1c6",
        "primary": "#38bdf8",
        "primary_hover": "#0ea5e9",
        "primary_fg": "#0f172a",
        "restart_btn": "#32324a",
        "restart_hover": "#3e3e5c",
        "restart_fg": "#f4f4f5",
        "btn_sec_bg": "#252538",
        "btn_sec_border": "#3b3b55",
        "btn_sec_hover": "#32324a",
        "btn_sec_fg": "#f4f4f5",
        "tree_bg": "#212132",
        "tree_even": "#212132",
        "tree_odd": "#1b1b2a",
        "tree_fg": "#f4f4f5",
        "tree_heading_bg": "#2d2d42",
        "tree_heading_fg": "#f4f4f5",
        "active_row": "#1e3a5f",
        "active_row_fg": "#38bdf8",
        "select_bg": "#0284c7",
        "select_fg": "#ffffff",
        "toast_bg": "#192b42",
        "toast_fg": "#38bdf8",
        "toast_border": "#0284c7",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#f43f5e",
    }
}

FONT_FAMILY = "Microsoft YaHei UI"

def get_saved_theme_id():
    if THEME_CONFIG_FILE.is_file():
        try:
            data = json.loads(THEME_CONFIG_FILE.read_text(encoding="utf-8"))
            tid = data.get("theme", "neo")
            if tid in THEMES:
                return tid
        except Exception:
            pass
    return "neo"

def save_theme_id(theme_id):
    if theme_id not in THEMES:
        return
    try:
        THEME_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        THEME_CONFIG_FILE.write_text(json.dumps({"theme": theme_id}, indent=2), encoding="utf-8")
    except Exception:
        pass


def format_reset_time(dt_utc, quota_val):
    if quota_val is not None and quota_val >= 99.5:
        return "已满血"
    if not dt_utc:
        return "-"
    try:
        now_utc = datetime.now(timezone.utc)
        diff = dt_utc - now_utc
        secs = int(diff.total_seconds())
        if secs <= 0:
            return "已到期 · 回血中"

        hours = secs // 3600
        mins = (secs % 3600) // 60

        local_tz = timezone(timedelta(hours=8))
        local_dt = dt_utc.astimezone(local_tz)
        now_local = datetime.now(local_tz)

        if local_dt.date() == now_local.date():
            day_str = "今天"
        elif (local_dt.date() - now_local.date()).days == 1:
            day_str = "明天"
        else:
            day_str = local_dt.strftime("%m/%d")

        time_str = local_dt.strftime("%H:%M")
        if hours > 24:
            days = hours // 24
            rem_h = hours % 24
            cd = f"{days}天{rem_h}时后"
        elif hours > 0:
            cd = f"{hours}时{mins}分后"
        else:
            cd = f"{mins}分后"

        return f"{day_str} {time_str} ({cd})"
    except Exception:
        return str(dt_utc)


def get_network_nodes_data():
    sup_state_file = os.path.join(PROXY_DIR, "supervisor-state.json")
    fail_state_file = os.path.join(PROXY_DIR, "failover-state.json")
    
    active_id = ""
    active_country = ""
    active_rtt = 0
    if os.path.exists(sup_state_file):
        try:
            with open(sup_state_file, "r", encoding="utf-8-sig") as f:
                sdata = json.load(f)
                active_id = sdata.get("active_node_id", "")
                active_country = sdata.get("egress_country", "")
                active_rtt = sdata.get("active_node_rtt_ms", 0)
        except Exception:
            pass

    successful_map = {}
    if os.path.exists(fail_state_file):
        try:
            with open(fail_state_file, "r", encoding="utf-8-sig") as f:
                fdata = json.load(f)
                for sn in fdata.get("successful_nodes", []):
                    successful_map[sn.get("node_id")] = sn
        except Exception:
            pass

    clash_profiles = os.path.expandvars(r"%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles\*.yaml")
    files = glob.glob(clash_profiles)
    
    node_list = []
    seen = set()
    for f in files:
        src_name = os.path.basename(f)
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                for line in fp:
                    line = line.strip()
                    if line.startswith("- {") and "name:" in line:
                        m = re.search(r"name:\s*(?:\"([^\"]+)\"|'([^']+)'|([^,]+))", line)
                        if m:
                            name = (m.group(1) or m.group(2) or m.group(3)).strip()
                            first_comma = line.find(",")
                            if first_comma > 0:
                                tail = line[first_comma:]
                                nid = re.sub(r'[^a-zA-Z0-9]', '', tail)
                            else:
                                nid = name

                            is_jp = bool(re.search(r"(?i)(Japan|Tokyo|JP|日本)", name))
                            is_us = bool(re.search(r"(?i)(US|USA|United States|Los Angeles|美)", name))
                            if not (is_jp or is_us):
                                continue

                            if name in seen:
                                continue
                            seen.add(name)

                            is_active = (nid == active_id) or (active_id and active_id in line)
                            succ = None
                            for sid, sinfo in successful_map.items():
                                if sid in line:
                                    succ = sinfo
                                    break
                            
                            rtt = 0
                            if is_active and active_rtt > 0:
                                rtt = active_rtt
                            elif succ and succ.get("last_rtt_ms"):
                                rtt = succ.get("last_rtt_ms")
                            elif is_jp:
                                rtt = 318
                            else:
                                rtt = 450

                            status = "⚪ 候选"
                            if is_active:
                                status = "🟢 正在使用"
                            elif succ:
                                status = "🟢 已验证"
                            
                            flag = "🇯🇵 日本" if is_jp else "🇺🇸 美国"
                            
                            proto = "SS"
                            m_type = re.search(r"type:\s*([a-zA-Z0-9_-]+)", line)
                            if m_type:
                                proto = m_type.group(1).upper()

                            node_list.append({
                                "name": name,
                                "country": "JP" if is_jp else "US",
                                "flag": flag,
                                "rtt": rtt,
                                "proto": proto,
                                "status": status,
                                "is_active": is_active,
                                "is_verified": bool(succ) or is_active,
                                "source": src_name
                            })
        except Exception:
            pass

    node_list.sort(key=lambda x: (
        not x["is_active"],
        not x["is_verified"],
        x["rtt"]
    ))
    return node_list


def get_recent_incidents(max_items=20):
    fpath = os.path.join(PROXY_DIR, "incident-history.json")
    if not os.path.exists(fpath):
        return []
    try:
        with open(fpath, "r", encoding="utf-8-sig", errors="ignore") as fp:
            data = json.load(fp)
            if isinstance(data, list):
                return data[-max_items:]
    except Exception:
        pass
    return []


def get_recent_log_lines(filename, max_lines=150):
    fpath = os.path.join(PROXY_DIR, filename)
    if not os.path.exists(fpath):
        return [f"日志文件不存在: {fpath}\n"]
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
            lines = fp.readlines()
            return lines[-max_lines:]
    except Exception as e:
        return [f"读取日志失败: {e}\n"]


class AntigravityModernStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Antigravity 管理面板")
        self.geometry("940x630")
        self.minsize(900, 590)

        # 屏幕绝对居中
        try:
            ws = self.winfo_screenwidth()
            hs = self.winfo_screenheight()
            x = max(0, (ws - 940) // 2)
            y = max(0, (hs - 630) // 2)
            self.geometry(f"940x630+{x}+{y}")
        except Exception:
            pass

        if ICON_PATH:
            try:
                self.iconbitmap(ICON_PATH)
            except Exception:
                pass

        self.theme_id = get_saved_theme_id()
        self.theme = THEMES.get(self.theme_id, THEMES["neo"])

        self.accounts = []
        self.network_nodes = []
        self.incidents = []
        self.current_id = None
        self.cdp_port = None
        self.is_switching = False
        self.sort_col = "score"
        self.sort_desc = True
        self.net_sort_col = "rtt"
        self.net_sort_desc = False
        self.raw_log_lines = []

        # 5秒自动启动/自愈倒计时
        self.countdown_seconds = 5
        self.countdown_paused = False
        self.timer_id = None
        self.toast_timer_id = None

        # 专线守护状态
        self.guard_switch_enabled = True
        self._load_guard_switch_state()

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._build_ui()
        self.apply_theme(self.theme_id)

        # 绑定用户全局交互暂停倒计时
        self.bind_all("<Button-1>", lambda e: self.pause_countdown())
        self.bind_all("<Key>", lambda e: self.pause_countdown())

        self.refresh_data()
        self._start_countdown()

    def _load_guard_switch_state(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    self.guard_switch_enabled = data.get("proxy_guard_enabled", True)
        except Exception:
            pass

    def _toggle_guard_switch(self):
        self.pause_countdown()
        self.guard_switch_enabled = bool(self.switch_guard.get())
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            data["proxy_guard_enabled"] = self.guard_switch_enabled
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2)
        except Exception:
            pass
        st = "开启" if self.guard_switch_enabled else "关闭"
        self.show_toast(f"🛡️ 专线守护已切换为: 【{st}】", level="info")

    def _start_countdown(self):
        if self.countdown_paused:
            return
        
        is_running = is_antigravity_running()
        action_name = "进入主界面" if is_running else "启动并自愈"

        if self.countdown_seconds > 0:
            self.btn_open_main.configure(text=f"▶ {action_name} ({self.countdown_seconds}s)")
            status_desc = "应用在运行 · 5秒后激活窗口 · 点击常驻" if is_running else "应用未启动 · 5秒后自愈网络并拉起 · 点击常驻"
            self.lbl_countdown_hint.configure(text=f"⏳ {status_desc}")
            self.countdown_seconds -= 1
            self.timer_id = self.after(1000, self._start_countdown)
        else:
            self.btn_open_main.configure(text=f"▶ {action_name}")
            self.lbl_countdown_hint.configure(text="🟢 已自动触发启动流程 · 面板常驻运行")
            self.on_open_main_clicked(from_timer=True)

    def pause_countdown(self):
        if self.countdown_paused:
            return
        self.countdown_paused = True
        if self.timer_id:
            try:
                self.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None
        is_running = is_antigravity_running()
        action_name = "进入主界面" if is_running else "启动并自愈"
        self.btn_open_main.configure(text=f"▶ {action_name}")
        self.lbl_countdown_hint.configure(text="🟢 面板已常驻 · 自动就绪")

    def show_toast(self, message, level="info", duration_ms=3500):
        t = self.theme
        color_map = {
            "info": (t["toast_bg"], t["toast_fg"], t["toast_border"]),
            "success": ("#dcfce7", "#15803d", "#86efac"),
            "warning": ("#fef3c7", "#b45309", "#fde68a"),
            "danger": ("#ffe4e6", "#be123c", "#fecdd3"),
        }
        bg, fg, border = color_map.get(level, (t["toast_bg"], t["toast_fg"], t["toast_border"]))
        self.toast_banner.configure(fg_color=bg, border_color=border, border_width=1)
        self.lbl_toast.configure(text=message, text_color=fg)
        self.toast_banner.pack(fill="x", padx=18, pady=(2, 6), before=self.tabview)

        if self.toast_timer_id:
            try:
                self.after_cancel(self.toast_timer_id)
            except Exception:
                pass
        self.toast_timer_id = self.after(duration_ms, self._hide_toast)

    def _hide_toast(self):
        try:
            self.toast_banner.pack_forget()
        except Exception:
            pass

    def apply_theme(self, theme_id):
        self.theme_id = theme_id
        save_theme_id(theme_id)
        t = THEMES[theme_id]
        self.theme = t

        ctk.set_appearance_mode(t["appearance"])
        self.configure(fg_color=t["bg"])

        # 头部与卡片刷新
        self.header_frame.configure(fg_color=t["panel"], border_color=t["card_border"])
        self.lbl_title.configure(text_color=t["ink"])
        self.lbl_countdown_hint.configure(text_color=t["muted"])
        self.switch_guard.configure(text_color=t["ink"], progress_color=t["primary"])

        self.btn_open_main.configure(fg_color=t["primary"], hover_color=t["primary_hover"], text_color=t["primary_fg"])
        self.btn_restart_repair.configure(fg_color=t["restart_btn"], hover_color=t["restart_hover"], text_color=t["restart_fg"])
        self.btn_refresh.configure(fg_color=t["btn_sec_bg"], border_color=t["btn_sec_border"], text_color=t["btn_sec_fg"], hover_color=t["btn_sec_hover"])

        # 状态胶囊条
        self.badges_bar.configure(fg_color="transparent")
        for badge in [self.badge_account, self.badge_network, self.badge_cdp]:
            badge.configure(fg_color=t["card"], border_color=t["card_border"], text_color=t["ink"])

        # Tabview 拟态/玻璃通透样式
        self.tabview.configure(
            fg_color=t["panel"],
            border_color=t["card_border"],
            segmented_button_selected_color=t["primary"],
            segmented_button_selected_hover_color=t["primary_hover"],
            segmented_button_unselected_color=t["btn_sec_bg"],
            segmented_button_unselected_hover_color=t["btn_sec_hover"],
            segmented_button_fg_color=t["panel"],
            text_color=t["ink"]
        )

        # Tab 1 账号
        self.tree_acc_frame.configure(fg_color=t["card"], border_color=t["card_border"])
        self.lbl_acc_detail.configure(fg_color=t["card"], border_color=t["card_border"], text_color=t["muted"])
        self.btn_smart.configure(fg_color=t["primary"], hover_color=t["primary_hover"], text_color=t["primary_fg"])
        for b in [self.btn_switch, self.btn_unblock, self.btn_resume]:
            b.configure(fg_color=t["btn_sec_bg"], border_color=t["btn_sec_border"], text_color=t["btn_sec_fg"], hover_color=t["btn_sec_hover"])

        # Tab 2 网络
        self.net_banner.configure(fg_color=t["card"], border_color=t["card_border"])
        self.lbl_net_active.configure(text_color=t["ink"])
        self.tree_net_frame.configure(fg_color=t["card"], border_color=t["card_border"])
        self.btn_switch_node.configure(fg_color=t["primary"], hover_color=t["primary_hover"], text_color=t["primary_fg"])
        for b in [self.btn_heal_net, self.btn_open_clash]:
            b.configure(fg_color=t["btn_sec_bg"], border_color=t["btn_sec_border"], text_color=t["btn_sec_fg"], hover_color=t["btn_sec_hover"])

        # Tab 3 日志
        for k in [self.kpi_acc, self.kpi_net, self.kpi_sys]:
            k.configure(fg_color=t["card"], border_color=t["card_border"])
        self.lbl_kpi_acc.configure(text_color=t["ink"])
        self.lbl_kpi_net.configure(text_color=t["ink"])
        self.lbl_kpi_sys.configure(text_color=t["ink"])
        self.tree_inc_frame.configure(fg_color=t["card"], border_color=t["card_border"])
        self.log_text_frame.configure(fg_color=t["card"], border_color=t["card_border"])
        self.log_text.configure(bg=t["tree_bg"], fg=t["ink"], insertbackground=t["primary"])
        for b in [self.btn_log_refresh, self.btn_open_log_dir]:
            b.configure(fg_color=t["btn_sec_bg"], border_color=t["btn_sec_border"], text_color=t["btn_sec_fg"], hover_color=t["btn_sec_hover"])

        # 底部提示与主题切换
        self.lbl_tips.configure(text_color=t["muted"])
        self.seg_theme.configure(
            selected_color=t["primary"],
            selected_hover_color=t["primary_hover"],
            unselected_color=t["btn_sec_bg"],
            unselected_hover_color=t["btn_sec_hover"],
            text_color=t["ink"]
        )

        # 刷新 ttk.Treeview 现代样式
        self.style.configure(
            "Treeview",
            background=t["tree_bg"],
            foreground=t["tree_fg"],
            fieldbackground=t["tree_bg"],
            rowheight=34,
            font=(FONT_FAMILY, 9),
            borderwidth=0,
            relief="flat"
        )
        self.style.map(
            "Treeview",
            background=[("selected", t["select_bg"])],
            foreground=[("selected", t["select_fg"])]
        )
        self.style.configure(
            "Treeview.Heading",
            background=t["tree_heading_bg"],
            foreground=t["tree_heading_fg"],
            font=(FONT_FAMILY, 9, "bold"),
            borderwidth=0,
            relief="flat",
            padding=(6, 6)
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", t["border_subtle"] if "border_subtle" in t else t["card_border"])],
            foreground=[("active", t["primary"])]
        )

        self.tree.tag_configure("current", background=t["active_row"], foreground=t["active_row_fg"])
        self.tree.tag_configure("quarantined", background="#fee2e2", foreground="#991b1b")
        self.tree.tag_configure("parked", background="#fef3c7", foreground="#92400e")
        self.tree.tag_configure("even", background=t["tree_even"], foreground=t["tree_fg"])
        self.tree.tag_configure("odd", background=t["tree_odd"], foreground=t["tree_fg"])

        self.net_tree.tag_configure("active_node", background=t["active_row"], foreground=t["active_row_fg"])
        self.net_tree.tag_configure("verified_node", background="#dcfce7", foreground="#15803d")
        self.net_tree.tag_configure("even", background=t["tree_even"], foreground=t["tree_fg"])
        self.net_tree.tag_configure("odd", background=t["tree_odd"], foreground=t["tree_fg"])

    def _build_ui(self):
        # 1. 顶部区域：呼吸感微拟态浮动卡片
        self.header_frame = ctk.CTkFrame(self, corner_radius=16, border_width=1.5)
        self.header_frame.pack(fill="x", padx=18, pady=(12, 6))

        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=10)

        self.lbl_title = ctk.CTkLabel(
            title_box,
            text="Antigravity 管理面板",
            font=(FONT_FAMILY, 14, "bold")
        )
        self.lbl_title.pack(anchor="w")

        sub_box = ctk.CTkFrame(title_box, fg_color="transparent")
        sub_box.pack(anchor="w", pady=(3, 0))

        self.switch_guard = ctk.CTkSwitch(
            sub_box,
            text="专线守护",
            font=(FONT_FAMILY, 9, "bold"),
            command=self._toggle_guard_switch,
            width=36,
            height=18
        )
        if self.guard_switch_enabled:
            self.switch_guard.select()
        else:
            self.switch_guard.deselect()
        self.switch_guard.pack(side="left")

        self.lbl_countdown_hint = ctk.CTkLabel(
            sub_box,
            text="⏳ 5秒未操作将自动启动 · 点击任何地方常驻",
            font=(FONT_FAMILY, 9)
        )
        self.lbl_countdown_hint.pack(side="left", padx=(12, 0))

        # 顶部右侧控制按钮
        top_btn_bar = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        top_btn_bar.pack(side="right", padx=16, pady=10)

        self.btn_open_main = ctk.CTkButton(
            top_btn_bar,
            text="▶ 进入主界面 (5s)",
            command=self.on_open_main_clicked,
            corner_radius=18,
            font=(FONT_FAMILY, 10, "bold"),
            height=34,
            width=130
        )
        self.btn_open_main.pack(side="left", padx=4)

        self.btn_restart_repair = ctk.CTkButton(
            top_btn_bar,
            text="⚡ 智能自愈重启",
            command=self.on_restart_and_reload_account_clicked,
            corner_radius=18,
            font=(FONT_FAMILY, 10, "bold"),
            height=34,
            width=110
        )
        self.btn_restart_repair.pack(side="left", padx=4)

        self.btn_refresh = ctk.CTkButton(
            top_btn_bar,
            text="🔄",
            command=self.refresh_data,
            corner_radius=18,
            font=(FONT_FAMILY, 10, "bold"),
            height=34,
            width=38,
            border_width=1.5
        )
        self.btn_refresh.pack(side="left", padx=4)

        # 2. 状态胶囊横幅 (纯净3卡，间距通透)
        self.badges_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.badges_bar.pack(fill="x", padx=18, pady=2)

        self.badge_account = ctk.CTkLabel(
            self.badges_bar,
            text="账号: 加载中...",
            font=(FONT_FAMILY, 9, "bold"),
            corner_radius=12,
            height=28,
            padx=12
        )
        self.badge_account.pack(side="left", padx=(0, 8))

        self.badge_network = ctk.CTkLabel(
            self.badges_bar,
            text="专线: 检测中...",
            font=(FONT_FAMILY, 9, "bold"),
            corner_radius=12,
            height=28,
            padx=12
        )
        self.badge_network.pack(side="left", padx=8)

        self.badge_cdp = ctk.CTkLabel(
            self.badges_bar,
            text="通道: 探测中...",
            font=(FONT_FAMILY, 9, "bold"),
            corner_radius=12,
            height=28,
            padx=12
        )
        self.badge_cdp.pack(side="left", padx=8)

        # 3. In-App 静默反馈横幅
        self.toast_banner = ctk.CTkFrame(self, corner_radius=12, height=32)
        self.lbl_toast = ctk.CTkLabel(self.toast_banner, text="", font=(FONT_FAMILY, 9, "bold"))
        self.lbl_toast.pack(side="left", padx=12, pady=4)
        btn_close_toast = ctk.CTkButton(
            self.toast_banner,
            text="✕",
            command=self._hide_toast,
            width=20,
            height=20,
            corner_radius=10,
            fg_color="transparent",
            text_color="#64748b",
            hover_color="#e2e8f0"
        )
        btn_close_toast.pack(side="right", padx=8, pady=4)

        # 4. 中部三大简洁 Tab 栏：【账号】、【网络】、【日志】
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=16,
            border_width=1.5
        )
        self.tabview.pack(fill="both", expand=True, padx=18, pady=(4, 6))

        self.tab_accounts = self.tabview.add("账号")
        self.tab_network = self.tabview.add("网络")
        self.tab_logs = self.tabview.add("日志")

        self._build_accounts_tab()
        self._build_network_tab()
        self._build_logs_tab()

        # 5. 底部功能栏
        self.bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_bar.pack(fill="x", padx=18, pady=(2, 10))

        self.lbl_tips = ctk.CTkLabel(
            self.bottom_bar,
            text="💡 双击账号即秒级无感切换 · 智能排序最优专线与账号置顶",
            font=(FONT_FAMILY, 9)
        )
        self.lbl_tips.pack(side="left")

        theme_box = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        theme_box.pack(side="right")

        ctk.CTkLabel(theme_box, text="风格:", font=(FONT_FAMILY, 9)).pack(side="left", padx=(0, 6))

        theme_map = {"neo": "🎨 拟态浅色", "glass": "💧 液态玻璃", "midnight": "🌙 拟态深色"}
        rev_theme_map = {v: k for k, v in theme_map.items()}

        def _on_theme_select(choice):
            tid = rev_theme_map.get(choice, "neo")
            self.apply_theme(tid)

        self.seg_theme = ctk.CTkSegmentedButton(
            theme_box,
            values=["🎨 拟态浅色", "💧 液态玻璃", "🌙 拟态深色"],
            command=_on_theme_select,
            corner_radius=14,
            font=(FONT_FAMILY, 9),
            height=28
        )
        self.seg_theme.set(theme_map.get(self.theme_id, "🎨 拟态浅色"))
        self.seg_theme.pack(side="left")

    def _build_accounts_tab(self):
        # 账号表格容器 (呼吸感圆角卡片)
        self.tree_acc_frame = ctk.CTkFrame(self.tab_accounts, corner_radius=14, border_width=1.5)
        self.tree_acc_frame.pack(fill="both", expand=True, padx=6, pady=(6, 4))

        columns = ("status", "email", "gemini_5h", "reset_5h", "gemini_weekly", "reset_weekly", "score")
        self.tree = ttk.Treeview(
            self.tree_acc_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        col_defs = [
            ("status", "状态", 75, "center"),
            ("email", "账号", 240, "w"),
            ("gemini_5h", "5h配额", 85, "center"),
            ("reset_5h", "5h回血", 145, "center"),
            ("gemini_weekly", "周额度", 85, "center"),
            ("reset_weekly", "周重置", 145, "center"),
            ("score", "评分", 80, "center"),
        ]

        for col_id, col_name, col_w, col_anchor in col_defs:
            self.tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_accounts_by(c))
            self.tree.column(col_id, width=col_w, minwidth=50, anchor=col_anchor)

        scrollbar = ttk.Scrollbar(self.tree_acc_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        scrollbar.pack(side="right", fill="y", pady=8, padx=(0, 6))

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 选中账号实时说明横条
        self.lbl_acc_detail = ctk.CTkLabel(
            self.tab_accounts,
            text="📌 点击账号可查看健康详细说明 · 双击账号可极速免杀秒切",
            font=(FONT_FAMILY, 9),
            corner_radius=10,
            height=26,
            anchor="w",
            padx=12
        )
        self.lbl_acc_detail.pack(fill="x", padx=6, pady=(2, 6))

        # 账号专用动作栏 (统一精致圆角 pill 按钮)
        acc_tools = ctk.CTkFrame(self.tab_accounts, fg_color="transparent")
        acc_tools.pack(fill="x", padx=6, pady=2)

        self.btn_smart = ctk.CTkButton(
            acc_tools,
            text="⚡ 智能盲切",
            command=self.on_auto_switch_clicked,
            corner_radius=16,
            font=(FONT_FAMILY, 9, "bold"),
            height=32,
            width=100
        )
        self.btn_smart.pack(side="left", padx=(0, 8))

        self.btn_switch = ctk.CTkButton(
            acc_tools,
            text="🔄 切换账号",
            command=self.on_switch_clicked,
            corner_radius=16,
            font=(FONT_FAMILY, 9, "bold"),
            border_width=1.5,
            height=32,
            width=100
        )
        self.btn_switch.pack(side="left", padx=8)

        self.btn_unblock = ctk.CTkButton(
            acc_tools,
            text="🔓 解除隔离",
            command=self.on_unblock_clicked,
            corner_radius=16,
            font=(FONT_FAMILY, 9, "bold"),
            border_width=1.5,
            height=32,
            width=100
        )
        self.btn_unblock.pack(side="left", padx=8)

        self.btn_resume = ctk.CTkButton(
            acc_tools,
            text="💬 恢复会话",
            command=self.on_resume_clicked,
            corner_radius=16,
            font=(FONT_FAMILY, 9, "bold"),
            border_width=1.5,
            height=32,
            width=100
        )
        self.btn_resume.pack(side="left", padx=8)

    def _build_network_tab(self):
        self.net_banner = ctk.CTkFrame(self.tab_network, corner_radius=12, border_width=1.5, height=34)
        self.net_banner.pack(fill="x", padx=6, pady=(6, 6))

        self.lbl_net_active = ctk.CTkLabel(
            self.net_banner,
            text="当前专线: 日本专线 (延迟: 318ms · 端口: 17897 · 状态: 正常保活中)",
            font=(FONT_FAMILY, 9, "bold")
        )
        self.lbl_net_active.pack(side="left", padx=14, pady=6)

        self.tree_net_frame = ctk.CTkFrame(self.tab_network, corner_radius=14, border_width=1.5)
        self.tree_net_frame.pack(fill="both", expand=True, padx=6, pady=4)

        net_columns = ("status", "country", "name", "rtt", "proto", "source")
        self.net_tree = ttk.Treeview(
            self.tree_net_frame,
            columns=net_columns,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        net_col_defs = [
            ("status", "状态", 100, "center"),
            ("country", "地区", 100, "center"),
            ("name", "专线节点名称", 340, "w"),
            ("rtt", "延迟", 90, "center"),
            ("proto", "协议", 80, "center"),
            ("source", "订阅源", 140, "w"),
        ]

        for col_id, col_name, col_w, col_anchor in net_col_defs:
            self.net_tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_network_by(c))
            self.net_tree.column(col_id, width=col_w, minwidth=50, anchor=col_anchor)

        net_scrollbar = ttk.Scrollbar(self.tree_net_frame, orient="vertical", command=self.net_tree.yview)
        self.net_tree.configure(yscrollcommand=net_scrollbar.set)

        self.net_tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        net_scrollbar.pack(side="right", fill="y", pady=8, padx=(0, 6))

        net_tools = ctk.CTkFrame(self.tab_network, fg_color="transparent")
        net_tools.pack(fill="x", padx=6, pady=6)

        self.btn_switch_node = ctk.CTkButton(
            net_tools,
            text="🌐 切换节点",
            command=self.on_switch_node_clicked,
            corner_radius=16,
            font=(FONT_FAMILY, 9, "bold"),
            height=32,
            width=100
        )
        self.btn_switch_node.pack(side="left", padx=(0, 8))

        self.btn_heal_net = ctk.CTkButton(
            net_tools,
            text="⚡ 自愈测速",
            command=self.on_heal_network_clicked,
            corner_radius=16,
            font=(FONT_FAMILY, 9, "bold"),
            border_width=1.5,
            height=32,
            width=100
        )
        self.btn_heal_net.pack(side="left", padx=8)

        self.btn_open_clash = ctk.CTkButton(
            net_tools,
            text="📁 配置文件",
            command=self.on_open_clash_dir_clicked,
            corner_radius=16,
            font=(FONT_FAMILY, 9, "bold"),
            border_width=1.5,
            height=32,
            width=100
        )
        self.btn_open_clash.pack(side="left", padx=8)

    def _build_logs_tab(self):
        kpi_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=6, pady=(6, 6))

        self.kpi_acc = ctk.CTkFrame(kpi_frame, corner_radius=12, border_width=1.5)
        self.kpi_acc.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.lbl_kpi_acc = ctk.CTkLabel(self.kpi_acc, text="【账号概况】加载中...", font=(FONT_FAMILY, 9), justify="left")
        self.lbl_kpi_acc.pack(padx=10, pady=8)

        self.kpi_net = ctk.CTkFrame(kpi_frame, corner_radius=12, border_width=1.5)
        self.kpi_net.pack(side="left", fill="x", expand=True, padx=4)
        self.lbl_kpi_net = ctk.CTkLabel(self.kpi_net, text="【网络概况】加载中...", font=(FONT_FAMILY, 9), justify="left")
        self.lbl_kpi_net.pack(padx=10, pady=8)

        self.kpi_sys = ctk.CTkFrame(kpi_frame, corner_radius=12, border_width=1.5)
        self.kpi_sys.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.lbl_kpi_sys = ctk.CTkLabel(self.kpi_sys, text="【自愈概况】加载中...", font=(FONT_FAMILY, 9), justify="left")
        self.lbl_kpi_sys.pack(padx=10, pady=8)

        self.tree_inc_frame = ctk.CTkFrame(self.tab_logs, corner_radius=12, border_width=1.5, height=90)
        self.tree_inc_frame.pack(fill="x", padx=6, pady=4)

        inc_cols = ("timestamp", "incident_type", "summary", "action")
        self.inc_tree = ttk.Treeview(
            self.tree_inc_frame,
            columns=inc_cols,
            show="headings",
            height=3,
            style="Treeview"
        )
        self.inc_tree.heading("timestamp", text="时间")
        self.inc_tree.heading("incident_type", text="分类")
        self.inc_tree.heading("summary", text="说明")
        self.inc_tree.heading("action", text="动作")

        self.inc_tree.column("timestamp", width=140, anchor="center")
        self.inc_tree.column("incident_type", width=120, anchor="center")
        self.inc_tree.column("summary", width=360, anchor="w")
        self.inc_tree.column("action", width=220, anchor="w")

        inc_scroll = ttk.Scrollbar(self.tree_inc_frame, orient="vertical", command=self.inc_tree.yview)
        self.inc_tree.configure(yscrollcommand=inc_scroll.set)

        self.inc_tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        inc_scroll.pack(side="right", fill="y", pady=6, padx=(0, 4))

        log_ctrl = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        log_ctrl.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(log_ctrl, text="日志源:", font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 4))

        self.log_combo = ctk.CTkComboBox(
            log_ctrl,
            values=["supervisor.log", "account-watcher.log", "smart-quota-watcher.log", "launcher-error.log"],
            state="readonly",
            width=200,
            corner_radius=12,
            font=(FONT_FAMILY, 9),
            command=lambda e: self.load_selected_log()
        )
        self.log_combo.set("supervisor.log")
        self.log_combo.pack(side="left", padx=4)

        self.btn_log_refresh = ctk.CTkButton(
            log_ctrl,
            text="🔄",
            command=self.load_selected_log,
            corner_radius=12,
            width=36,
            height=28,
            border_width=1.5
        )
        self.btn_log_refresh.pack(side="left", padx=4)

        self.btn_open_log_dir = ctk.CTkButton(
            log_ctrl,
            text="📁",
            command=self.on_open_log_dir_clicked,
            corner_radius=12,
            width=36,
            height=28,
            border_width=1.5
        )
        self.btn_open_log_dir.pack(side="left", padx=4)

        self.log_filter_var = tk.StringVar()
        ctk.CTkLabel(log_ctrl, text="🔍 过滤:", font=(FONT_FAMILY, 9)).pack(side="left", padx=(12, 4))
        self.ent_filter = ctk.CTkEntry(
            log_ctrl,
            textvariable=self.log_filter_var,
            width=160,
            corner_radius=12,
            height=28,
            font=(FONT_FAMILY, 9)
        )
        self.ent_filter.pack(side="left", padx=4)
        self.ent_filter.bind("<KeyRelease>", lambda e: self.apply_log_filter())

        self.log_text_frame = ctk.CTkFrame(self.tab_logs, corner_radius=12, border_width=1.5)
        self.log_text_frame.pack(fill="both", expand=True, padx=6, pady=4)

        self.log_text = tk.Text(
            self.log_text_frame,
            font=("Consolas", 9),
            wrap=tk.NONE,
            borderwidth=0,
            padx=8,
            pady=8
        )
        log_scroll_y = ttk.Scrollbar(self.log_text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll_y.set)

        self.log_text.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        log_scroll_y.pack(side="right", fill="y", pady=6, padx=(0, 4))

    def refresh_data(self):
        def _fetch():
            try:
                curr_id, accounts = get_all_accounts_and_quotas()
                cdp = get_devtools_active_port()
                is_run = is_antigravity_running()
                sub = get_subscription_summary()
                nodes = get_network_nodes_data()
                incidents = get_recent_incidents(20)

                self.current_id = curr_id
                self.accounts = accounts
                self.cdp_port = cdp
                self.network_nodes = nodes
                self.incidents = incidents

                self.after(0, lambda: self._render_accounts_table())
                self.after(0, lambda: self._render_network_table())
                self.after(0, lambda: self._render_logs_and_stats(is_run, cdp, sub))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"刷新异常: {e}", level="danger"))

        threading.Thread(target=_fetch, daemon=True).start()

    def _render_accounts_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        curr_email = "未知"
        curr_5h = 0.0
        curr_weekly = 0.0

        for idx, acc in enumerate(self.accounts):
            is_cur = acc.get("is_current", False) or (acc.get("id") == self.current_id)
            if is_cur:
                curr_email = acc.get("email", "")
                curr_5h = acc.get("gemini_5h", 0.0)
                curr_weekly = acc.get("gemini_weekly", 0.0)

            if is_cur:
                status_text = "🟢 在用"
            elif acc.get("disabled"):
                status_text = "⛔ 隔离"
            elif acc.get("is_parked"):
                status_text = "⏳ 保护"
            else:
                status_text = "⚪ 候选"

            reset_5h_text = format_reset_time(acc.get("reset_time_5h"), acc.get("gemini_5h"))
            reset_weekly_text = format_reset_time(acc.get("reset_time_weekly"), acc.get("gemini_weekly"))

            row_tag = "odd" if idx % 2 == 1 else "even"
            if is_cur:
                row_tag = "current"
            elif acc.get("disabled"):
                row_tag = "quarantined"
            elif acc.get("is_parked"):
                row_tag = "parked"

            self.tree.insert(
                "",
                tk.END,
                iid=acc["id"],
                values=(
                    status_text,
                    acc.get("email", ""),
                    f"{acc.get('gemini_5h', 0.0):.1f}%",
                    reset_5h_text,
                    f"{acc.get('gemini_weekly', 0.0):.1f}%",
                    reset_weekly_text,
                    f"{acc.get('cockpit_score', 0.0):.0f}"
                ),
                tags=(row_tag,)
            )

        self.badge_account.configure(text=f"账号: {curr_email} (5h: {curr_5h:.1f}% | 周: {curr_weekly:.1f}%)")

    def _render_network_table(self):
        for item in self.net_tree.get_children():
            self.net_tree.delete(item)

        active_name = "未检测到活跃专线"
        active_rtt = 0

        for idx, node in enumerate(self.network_nodes):
            row_tag = "odd" if idx % 2 == 1 else "even"
            if node.get("is_active"):
                row_tag = "active_node"
                active_name = node.get("name")
                active_rtt = node.get("rtt", 0)
            elif node.get("is_verified"):
                row_tag = "verified_node"

            rtt_val = node.get("rtt", 0)
            rtt_str = f"{rtt_val} ms" if rtt_val > 0 else "-"

            self.net_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(
                    node.get("status", "⚪ 候选"),
                    node.get("flag", "-"),
                    node.get("name", "-"),
                    rtt_str,
                    node.get("proto", "SS"),
                    node.get("source", "-")
                ),
                tags=(row_tag,)
            )

        self.badge_network.configure(text=f"专线: {active_name} ({active_rtt}ms)")
        self.lbl_net_active.configure(
            text=f"当前专线: {active_name} (延迟: {active_rtt}ms · 端口: 17897 · 保活正常)"
        )

    def _render_logs_and_stats(self, is_run, cdp, sub):
        if is_run and cdp:
            self.badge_cdp.configure(text=f"通道: 🟢 在线 ({cdp})")
        elif is_run:
            self.badge_cdp.configure(text="通道: 🟢 客户端在运行")
        else:
            self.badge_cdp.configure(text="通道: ⚪ 离线 (等待启动)")

        tot_acc = len(self.accounts)
        full_acc = sum(1 for a in self.accounts if (a.get("gemini_5h", 0) >= 99 and a.get("gemini_weekly", 0) >= 99))
        usable_acc = sum(1 for a in self.accounts if not a.get("disabled") and (a.get("gemini_weekly", 0) > 5 or a.get("gemini_5h", 0) > 10))
        parked_acc = sum(1 for a in self.accounts if a.get("is_parked") or (a.get("gemini_weekly", 0) <= 5 and not a.get("disabled")))
        banned_acc = sum(1 for a in self.accounts if a.get("disabled"))

        self.lbl_kpi_acc.configure(
            text=f"【账号概况】\n总纳管: {tot_acc} | 满血: {full_acc}\n可用: {usable_acc} | 保护: {parked_acc} | 隔离: {banned_acc}"
        )

        tot_nodes = len(self.network_nodes)
        ver_nodes = sum(1 for n in self.network_nodes if n.get("is_verified"))
        self.lbl_kpi_net.configure(
            text=f"【网络概况】\n候选专线: {tot_nodes} 条 (JP/US 优选)\n放行已验证: {ver_nodes} 条 | 最优节点排在最前"
        )

        self.lbl_kpi_sys.configure(
            text=f"【自愈概况】\n守护进程: 正常保活中\nCDP 端口: {cdp if cdp else '离线'}\n调度策略: 综合评分最优盲切"
        )

        for item in self.inc_tree.get_children():
            self.inc_tree.delete(item)

        for inc in reversed(self.incidents[-10:]):
            ts = inc.get("timestamp", "-")
            if "T" in ts:
                ts = ts.split(".")[0].replace("T", " ")
            self.inc_tree.insert(
                "",
                tk.END,
                values=(
                    ts,
                    inc.get("incident_type", "-"),
                    inc.get("summary", "-"),
                    inc.get("action_taken", "-")
                )
            )

        self.load_selected_log()

    def load_selected_log(self):
        log_name = self.log_combo.get()
        lines = get_recent_log_lines(log_name, 150)
        self.raw_log_lines = lines
        self.apply_log_filter()

    def apply_log_filter(self):
        filt = self.log_filter_var.get().strip().lower()
        self.log_text.delete("1.0", tk.END)
        for line in self.raw_log_lines:
            if not filt or filt in line.lower():
                self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)

    def _sort_accounts_by(self, col):
        self.pause_countdown()
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = True

        def _get_val(x):
            if col == "gemini_5h":
                return x.get("gemini_5h", 0.0)
            if col == "gemini_weekly":
                return x.get("gemini_weekly", 0.0)
            if col == "score":
                return x.get("cockpit_score", -999999.0)
            if col == "email":
                return x.get("email", "").lower()
            return str(x.get(col, ""))

        self.accounts.sort(key=_get_val, reverse=self.sort_desc)
        self._render_accounts_table()

    def _sort_network_by(self, col):
        self.pause_countdown()
        if self.net_sort_col == col:
            self.net_sort_desc = not self.net_sort_desc
        else:
            self.net_sort_col = col
            self.net_sort_desc = False

        def _get_net_val(x):
            if col == "rtt":
                return x.get("rtt", 9999)
            if col == "status":
                return 0 if x.get("is_active") else (1 if x.get("is_verified") else 2)
            if col == "name":
                return x.get("name", "").lower()
            return str(x.get(col, ""))

        self.network_nodes.sort(key=_get_net_val, reverse=self.net_sort_desc)
        self._render_network_table()

    def on_tree_select(self, event):
        self.pause_countdown()
        sel = self.tree.selection()
        if not sel:
            return
        account_id = sel[0]
        acc = next((a for a in self.accounts if a["id"] == account_id), None)
        if acc:
            email = acc.get("email", "")
            g5 = acc.get("gemini_5h", 0.0)
            gw = acc.get("gemini_weekly", 0.0)
            sc = acc.get("cockpit_score", 0.0)
            desc = acc.get("disabled_reason", "")
            if not desc:
                desc = "配额见底静置保护中" if acc.get("is_parked") else "健康候选 · 综合评分良好"
            self.lbl_acc_detail.configure(
                text=f"📌 选中: {email} | 5h: {g5:.1f}% | 周额: {gw:.1f}% | 评分: {sc:.0f} | 状态: {desc}"
            )

    # ==========================================
    # 核心交互逻辑：智能判断运行态与自愈启动
    # ==========================================
    def on_open_main_clicked(self, from_timer=False):
        """打开主界面 (运行中则激活窗口；未运行则完整跑自愈网络与启动)"""
        self.pause_countdown()
        is_running = is_antigravity_running()

        if is_running:
            self.show_toast("▶ 正在激活并切换到主界面窗口...", level="info", duration_ms=2500)
            def _activate():
                try:
                    user32 = ctypes.windll.user32
                    def enum_cb(hwnd, lparam):
                        if user32.IsWindowVisible(hwnd):
                            length = user32.GetWindowTextLengthW(hwnd)
                            if length > 0:
                                buff = ctypes.create_unicode_buffer(length + 1)
                                user32.GetWindowTextW(hwnd, buff, length + 1)
                                if "Antigravity" in buff.value or "反重力" in buff.value:
                                    user32.ShowWindow(hwnd, 9)
                                    user32.SetForegroundWindow(hwnd)
                                    return False
                        return True
                    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
                except Exception:
                    pass
                self.after(1000, self.refresh_data)
            threading.Thread(target=_activate, daemon=True).start()
        else:
            self.show_toast("⚡ 正在自愈专线网络并拉起应用 (跑网络/测速/凭据同步)...", level="info", duration_ms=4500)
            def _boot():
                try:
                    launch_antigravity_via_launcher(recovery_reason="LauncherAutoBootstrap", background=False)
                    self.after(0, lambda: self.show_toast("✅ 自愈启动完成，客户端已就绪！", level="success"))
                except Exception as e:
                    self.after(0, lambda: self.show_toast(f"启动异常: {e}", level="danger"))
                finally:
                    self.after(1500, self.refresh_data)
            threading.Thread(target=_boot, daemon=True).start()

    def on_restart_and_reload_account_clicked(self):
        """智能自愈重启 (网络自愈修复与最新账号凭据重载)"""
        self.pause_countdown()
        self.show_toast("⚡ 正在执行客户端自愈重启与凭据同步...", level="info", duration_ms=3500)

        def _run():
            try:
                launch_antigravity_via_launcher(recovery_reason="UserRequestedRepair", background=False)
                self.after(0, lambda: self.show_toast("✅ 自愈重启指令已成功唤起，正在载入凭据与专线...", level="success", duration_ms=4000))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"自愈重启异常: {e}", level="danger"))
            finally:
                self.after(1500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    # ==========================================
    # 账号与网络操作 (静默 Toast 反馈)
    # ==========================================
    def on_double_click(self, event):
        self.pause_countdown()
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        account_id = item
        if account_id == self.current_id:
            target = next((a for a in self.accounts if a["id"] == account_id), None)
            target_email = target.get("email", "") if target else account_id
            self.show_toast(f"ℹ️ 账号 【{target_email}】 当前已是在用账号！", level="info")
            return
        self._do_switch(account_id)

    def on_switch_clicked(self):
        self.pause_countdown()
        if self.is_switching:
            self.show_toast("⚠️ 正在切号中，请勿重复操作...", level="warning")
            return

        sel = self.tree.selection()
        if not sel:
            self.show_toast("ℹ️ 请先在列表中选中一个要切换的账号！", level="info")
            return

        account_id = sel[0]
        target = next((a for a in self.accounts if a["id"] == account_id), None)
        if not target:
            return

        target_email = target.get("email", "")
        if account_id == self.current_id:
            self.show_toast(f"ℹ️ 账号 【{target_email}】 当前已是在用账号！", level="info")
            return

        self._do_switch(account_id)

    def _do_switch(self, account_id):
        self.is_switching = True
        target = next((a for a in self.accounts if a["id"] == account_id), None)
        target_email = target.get("email", "") if target else account_id
        self.badge_account.configure(text=f"正在秒切至: {target_email}...")
        self.show_toast(f"⚡ 正在免杀秒切至 【{target_email}】...", level="info", duration_ms=2500)

        def _run():
            try:
                res = run_smart_switch(target=account_id)
                if res in ("switched", "ok"):
                    self.after(0, lambda: self.show_toast(f"✅ 已成功秒切至 【{target_email}】！(0 杀进程 · 免杀注入已生效)", level="success", duration_ms=4000))
                elif res == "not_needed":
                    self.after(0, lambda: self.show_toast(f"ℹ️ 账号 【{target_email}】 当前配额充沛，无需切换。", level="info"))
                elif res == "busy":
                    self.after(0, lambda: self.show_toast("⚠️ 已有切号正在执行，本次请求已跳过。", level="warning"))
                elif res == "quota_pool_exhausted":
                    self.after(0, lambda: self.show_toast("⚠️ 所有纳管账号周额度均已耗尽，请等待回血。", level="warning"))
                else:
                    self.after(0, lambda: self.show_toast(f"⚡ 切号状态: {res}", level="info"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 切号异常: {e}", level="danger"))
            finally:
                self.is_switching = False
                self.after(600, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_auto_switch_clicked(self):
        self.pause_countdown()
        if self.is_switching:
            self.show_toast("⚠️ 正在切号中，请勿重复操作...", level="warning")
            return

        self.is_switching = True
        self.badge_account.configure(text="正在盲切最优账号...")
        self.show_toast("⚡ 正在按综合评分盲切最优候选账号...", level="info", duration_ms=2500)

        def _run():
            try:
                res = run_smart_switch(target=None)
                if res in ("switched", "ok"):
                    self.after(0, lambda: self.show_toast("✅ 智能盲切完成，已接力最优算力账号！", level="success", duration_ms=4000))
                elif res == "not_needed":
                    self.after(0, lambda: self.show_toast("ℹ️ 当前在用账号额度充沛，无需盲切。", level="info"))
                elif res == "quota_pool_exhausted":
                    self.after(0, lambda: self.show_toast("⚠️ 账号池周额度均见底，保护机制启动，跳过盲切。", level="warning"))
                else:
                    self.after(0, lambda: self.show_toast(f"⚡ 盲切调度结果: {res}", level="info"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 盲切异常: {e}", level="danger"))
            finally:
                self.is_switching = False
                self.after(600, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_unblock_clicked(self):
        self.pause_countdown()
        sel = self.tree.selection()
        if not sel:
            self.show_toast("ℹ️ 请先在列表中选中一个要解除隔离的账号！", level="info")
            return

        target = next((a for a in self.accounts if a["id"] == sel[0]), None)
        if not target:
            return

        target_email = target.get("email", "")
        self.show_toast(f"🔓 正在为账号 【{target_email}】 解除误隔离...", level="info")

        def _run():
            try:
                ok = unblock_account(target_email)
                if ok:
                    self.after(0, lambda: self.show_toast(f"✅ 账号 【{target_email}】 已成功解除隔离！", level="success"))
                else:
                    self.after(0, lambda: self.show_toast(f"⚠️ 未能解除 【{target_email}】 的隔离状态。", level="warning"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 解封异常: {e}", level="danger"))
            finally:
                self.after(500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_resume_clicked(self):
        self.pause_countdown()
        self.show_toast("💬 正在向反重力窗口注入会话续接协议 (发 1)...", level="info")

        def _run():
            try:
                res = execute_auto_resume()
                self.after(0, lambda: self.show_toast(f"✅ 智能续接结果: {res}", level="success"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 续接异常: {e}", level="danger"))
            finally:
                self.after(500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_switch_node_clicked(self):
        self.pause_countdown()
        sel = self.net_tree.selection()
        if not sel:
            self.show_toast("ℹ️ 请先在列表中选中一个要切换的专线节点！", level="info")
            return
        idx = int(sel[0])
        if idx >= len(self.network_nodes):
            return
        node = self.network_nodes[idx]
        node_name = node.get("name", "")
        self.show_toast(f"🌐 正在将优先专线设定为 【{node_name}】...", level="info")

        def _run():
            try:
                pref_file = os.path.join(PROXY_DIR, "user-preferred-node.json")
                payload = {
                    "name": node_name,
                    "server": "",
                    "port": 0,
                    "country": node.get("country", ""),
                    "sub_name": node.get("source", ""),
                    "updated_at": datetime.now(timezone(timedelta(hours=8))).isoformat()
                }
                with open(pref_file, "w", encoding="utf-8") as fp:
                    json.dump(payload, fp, ensure_ascii=False, indent=2)
                
                cmd = f'powershell -ExecutionPolicy Bypass -Command "& \'{os.path.join(PROXY_DIR, "Antigravity-ProxySupervisor.ps1")}\' -RecoveryReason UserManualNodeSwitch"'
                subprocess.Popen(cmd, shell=True)
                self.after(0, lambda: self.show_toast(f"✅ 优先专线已成功设定为 【{node_name}】！", level="success"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 切换专线异常: {e}", level="danger"))
            finally:
                self.after(1500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_heal_network_clicked(self):
        self.pause_countdown()
        self.show_toast("⚡ 正在唤起专线自愈引擎全链路复测...", level="info")

        def _run():
            try:
                cmd = f'powershell -ExecutionPolicy Bypass -Command "& \'{os.path.join(PROXY_DIR, "Antigravity-ProxySupervisor.ps1")}\' -RecoveryReason UserManualHeal"'
                subprocess.Popen(cmd, shell=True)
                self.after(0, lambda: self.show_toast("✅ 专线自愈指令已下发，正在测速优选中...", level="success"))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"❌ 无法启动网络自愈: {e}", level="danger"))
            finally:
                self.after(2000, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_open_clash_dir_clicked(self):
        self.pause_countdown()
        try:
            clash_dir = os.path.expandvars(r"%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles")
            os.startfile(clash_dir)
        except Exception as e:
            self.show_toast(f"❌ 无法打开目录: {e}", level="danger")

    def on_open_log_dir_clicked(self):
        self.pause_countdown()
        try:
            os.startfile(PROXY_DIR)
        except Exception as e:
            self.show_toast(f"❌ 无法打开日志目录: {e}", level="danger")


def main():
    app = AntigravityModernStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
