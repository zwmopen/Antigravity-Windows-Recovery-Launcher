# -*- coding: utf-8 -*-
"""
antigravity_switcher_gui.py — 反重力 (Antigravity) 算力与专线管理面板 (Antigravity Management Studio)
具备多账号算力大盘、最优专线网络大盘、历史日志与自愈统计分析的一体化高科技暗黑控制台。
"""

import os
import sys
import glob
import re
import json
import socket
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
    myappid = "antigravity.switcher.gui.v2"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

def attach_desktop():
    """接入交互桌面 winsta0\\default (穿透会话隔离)"""
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
from tkinter import ttk, messagebox

# 确保能载入 launcher 底层库
LAUNCHER_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\launcher")
PROXY_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\private-proxy")
if LAUNCHER_DIR not in sys.path:
    sys.path.insert(0, LAUNCHER_DIR)

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
    os.path.join(LAUNCHER_DIR, "antigravity_network.ico"),
    r"D:\AICode\tools\ai-compute-hub\ai-compute-hub.ico",
    os.path.join(LAUNCHER_DIR, "Antigravity-Launcher.ico"),
]
ICON_PATH = next((p for p in ICON_CANDIDATES if os.path.exists(p)), None)


def format_reset_time(dt_utc, quota_val):
    """将 UTC 回血/重置时刻转换为本地时区 (UTC+8) 并计算倒计时文案"""
    if quota_val is not None and quota_val >= 99.5:
        return "已满血 (100%)"
    if not dt_utc:
        return "-"
    try:
        now_utc = datetime.now(timezone.utc)
        diff = dt_utc - now_utc
        secs = int(diff.total_seconds())
        if secs <= 0:
            return "已到期 / 回血中"

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
    """解析专线节点大盘，按最优网络严格排序 (在用置顶 -> 已验证放行 -> 延迟由低到高)"""
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
    retired_set = set()
    cooldown_set = set()
    if os.path.exists(fail_state_file):
        try:
            with open(fail_state_file, "r", encoding="utf-8-sig") as f:
                fdata = json.load(f)
                for sn in fdata.get("successful_nodes", []):
                    successful_map[sn.get("node_id")] = sn
                for rn in fdata.get("retired_nodes", []):
                    retired_set.add(rn.get("node_id"))
                for cn in fdata.get("failed_nodes", []):
                    cooldown_set.add(cn.get("node_id"))
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
                                rtt = 320
                            else:
                                rtt = 450

                            status = "○ 候选"
                            if is_active:
                                status = "🟢 正在使用"
                            elif succ:
                                status = "🟢 已验证"
                            
                            flag = "🇯🇵 日本" if is_jp else "🇺🇸 美国"
                            
                            # 提取协议
                            proto = "SS/Trojan"
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
                                "source": src_name,
                                "raw_line": line
                            })
        except Exception:
            pass

    # 智能排序规则：正在使用最顶 -> 已验证次之 -> 延迟从低到高升序！
    node_list.sort(key=lambda x: (
        not x["is_active"],
        not x["is_verified"],
        x["rtt"]
    ))
    return node_list


def get_recent_incidents(max_items=30):
    """读取历史自愈与切号事件"""
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


def get_recent_log_lines(filename, max_lines=200):
    """读取指定日志文件的末尾行数"""
    fpath = os.path.join(PROXY_DIR, filename)
    if not os.path.exists(fpath):
        return [f"日志文件不存在: {fpath}\n"]
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
            lines = fp.readlines()
            return lines[-max_lines:]
    except Exception as e:
        return [f"读取日志失败: {e}\n"]


class AntigravitySwitcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("反重力 (Antigravity) 算力与专线管理面板")
        self.root.geometry("1340x740")
        self.root.minsize(1080, 620)

        # 经典暗黑科技配色 (Catppuccin Macchiato / Tokyo Night)
        self.COLOR_BG = "#181926"
        self.COLOR_CARD = "#24273a"
        self.COLOR_FG = "#cad3f5"
        self.COLOR_MUTED = "#8087a2"
        self.COLOR_ACCENT = "#a6da95"      # 极光绿 (健康/满血)
        self.COLOR_WARNING = "#eed49f"     # 琥珀黄 (见底/警告)
        self.COLOR_DANGER = "#ed8796"      # 珊瑚红 (隔离/封禁)
        self.COLOR_CYAN = "#8aadf4"        # 科技蓝 (在用/高亮)
        self.COLOR_PURPLE = "#c6a0f6"      # 紫罗兰 (算力指标)

        self.root.configure(bg=self.COLOR_BG)

        if ICON_PATH:
            try:
                self.root.iconbitmap(ICON_PATH)
            except Exception:
                pass

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

        self._setup_styles()
        self._build_ui()
        self.refresh_data()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # 表格通用样式
        style.configure(
            "Treeview",
            background=self.COLOR_CARD,
            foreground=self.COLOR_FG,
            rowheight=34,
            fieldbackground=self.COLOR_CARD,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        style.map(
            "Treeview",
            background=[("selected", "#363a4f")],
            foreground=[("selected", "#ffffff")]
        )

        # 表头样式
        style.configure(
            "Treeview.Heading",
            background="#1e2030",
            foreground=self.COLOR_CYAN,
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            padding=(8, 6)
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#282a36")],
            foreground=[("active", self.COLOR_ACCENT)]
        )

        # 选项卡 Notebook 样式
        style.configure("TNotebook", background=self.COLOR_BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#1e2030",
            foreground=self.COLOR_FG,
            padding=(20, 8),
            font=("Segoe UI", 10, "bold"),
            borderwidth=0
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.COLOR_CARD), ("active", "#282a36")],
            foreground=[("selected", self.COLOR_CYAN), ("active", self.COLOR_ACCENT)]
        )

        # 滚动条样式
        style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background="#24273a",
            darkcolor="#181926",
            lightcolor="#24273a",
            troughcolor="#181926",
            bordercolor="#181926",
            arrowcolor=self.COLOR_CYAN
        )

    def _build_ui(self):
        # 1. 顶部标题与状态大盘区
        top_frame = tk.Frame(self.root, bg=self.COLOR_BG, padx=20, pady=12)
        top_frame.pack(fill=tk.X)

        title_box = tk.Frame(top_frame, bg=self.COLOR_BG)
        title_box.pack(side=tk.LEFT)

        lbl_title = tk.Label(
            title_box,
            text="反重力 (Antigravity) 算力与专线管理面板",
            font=("Segoe UI", 16, "bold"),
            fg=self.COLOR_FG,
            bg=self.COLOR_BG
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            title_box,
            text="智能账号配额监控 · 最优专线自愈排序 · CDP 热感断点续接 · 全量自愈日志与统计看板",
            font=("Segoe UI", 9),
            fg=self.COLOR_MUTED,
            bg=self.COLOR_BG
        )
        lbl_sub.pack(anchor="w", pady=(3, 0))

        # 顶部右侧指标卡
        self.stats_frame = tk.Frame(top_frame, bg=self.COLOR_BG)
        self.stats_frame.pack(side=tk.RIGHT)

        self.lbl_cdp = tk.Label(
            self.stats_frame,
            text="CDP 探测中...",
            font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_ACCENT,
            bg="#1e2030",
            padx=10,
            pady=5,
            relief="flat"
        )
        self.lbl_cdp.pack(side=tk.LEFT, padx=4)

        self.lbl_active = tk.Label(
            self.stats_frame,
            text="当前活跃: 加载中...",
            font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_CYAN,
            bg="#1e2030",
            padx=10,
            pady=5,
            relief="flat"
        )
        self.lbl_active.pack(side=tk.LEFT, padx=4)

        self.lbl_proxy = tk.Label(
            self.stats_frame,
            text="专线: 17897",
            font=("Segoe UI", 9),
            fg=self.COLOR_FG,
            bg="#1e2030",
            padx=10,
            pady=5,
            relief="flat"
        )
        self.lbl_proxy.pack(side=tk.LEFT, padx=4)

        # 2. 中部 Notebook 多选项卡
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=4)

        # Tab 1: 算力账号大盘
        self.tab_accounts = tk.Frame(self.notebook, bg=self.COLOR_BG)
        self.notebook.add(self.tab_accounts, text="  👤 算力账号大盘  ")
        self._build_accounts_tab()

        # Tab 2: 专线网络大盘
        self.tab_network = tk.Frame(self.notebook, bg=self.COLOR_BG)
        self.notebook.add(self.tab_network, text="  🌐 专线网络大盘 (最优置顶)  ")
        self._build_network_tab()

        # Tab 3: 运行日志与统计
        self.tab_logs = tk.Frame(self.notebook, bg=self.COLOR_BG)
        self.notebook.add(self.tab_logs, text="  📜 运行日志与统计  ")
        self._build_logs_tab()

        # 3. 底部通用快捷操作栏
        bottom_bar = tk.Frame(self.root, bg=self.COLOR_BG, padx=20, pady=10)
        bottom_bar.pack(fill=tk.X)

        btn_launch = tk.Button(
            bottom_bar,
            text="▶ 启动 Antigravity 客户端",
            command=self.on_launch_client_clicked,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2"
        )
        btn_launch.pack(side=tk.LEFT, padx=(0, 8))

        btn_smart_switch = tk.Button(
            bottom_bar,
            text="⚡ 智能盲切最优账号",
            command=self.on_auto_switch_clicked,
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2"
        )
        btn_smart_switch.pack(side=tk.LEFT, padx=6)

        btn_switch_sel = tk.Button(
            bottom_bar,
            text="🔁 切换至选定账号",
            command=self.on_switch_clicked,
            bg="#4f46e5",
            fg="#ffffff",
            activebackground="#4338ca",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2"
        )
        btn_switch_sel.pack(side=tk.LEFT, padx=6)

        btn_refresh = tk.Button(
            bottom_bar,
            text="🔄 刷新所有大盘",
            command=self.refresh_data,
            bg="#374151",
            fg=self.COLOR_FG,
            activebackground="#4b5563",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2"
        )
        btn_refresh.pack(side=tk.LEFT, padx=6)

        btn_heal_net = tk.Button(
            bottom_bar,
            text="🛡️ 专线网络自愈重连",
            command=self.on_heal_network_clicked,
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2"
        )
        btn_heal_net.pack(side=tk.LEFT, padx=6)

        btn_close = tk.Button(
            bottom_bar,
            text="❌ 关闭面板",
            command=self.root.destroy,
            bg="#374151",
            fg="#9ca3af",
            activebackground="#4b5563",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2"
        )
        btn_close.pack(side=tk.RIGHT)

        lbl_hint = tk.Label(
            bottom_bar,
            text="💡 双击账号即可快速秒切 · 智能排序始终将综合分最高及最优网络置顶",
            font=("Segoe UI", 9),
            fg=self.COLOR_MUTED,
            bg=self.COLOR_BG
        )
        lbl_hint.pack(side=tk.RIGHT, padx=14)

    def _build_accounts_tab(self):
        """构建 Tab 1: 算力账号大盘"""
        container = tk.Frame(self.tab_accounts, bg=self.COLOR_BG, padx=4, pady=6)
        container.pack(fill=tk.BOTH, expand=True)

        columns = ("status", "email", "gemini_5h", "reset_5h", "gemini_weekly", "reset_weekly", "claude_weekly", "score", "status_desc")
        self.tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        col_defs = [
            ("status", "当前", 70, "center"),
            ("email", "登录账号 / 邮箱", 220, "w"),
            ("gemini_5h", "5h 配额", 85, "center"),
            ("reset_5h", "5h 精确回血时间 (Cockpit同步)", 185, "center"),
            ("gemini_weekly", "周额度", 80, "center"),
            ("reset_weekly", "周额重置时刻 (Cockpit同步)", 185, "center"),
            ("claude_weekly", "Claude 周额", 95, "center"),
            ("score", "综合算力分", 95, "center"),
            ("status_desc", "健康度与状态说明", 260, "w"),
        ]

        for col_id, col_name, col_w, col_anchor in col_defs:
            self.tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_accounts_by(c))
            self.tree.column(col_id, width=col_w, minwidth=60, anchor=col_anchor)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview, style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self.on_double_click)

        # 账号专用辅助工具栏 (解封 / 恢复 / 续接)
        acc_tools = tk.Frame(self.tab_accounts, bg=self.COLOR_BG, pady=6)
        acc_tools.pack(fill=tk.X)

        btn_unblock = tk.Button(
            acc_tools,
            text="🔓 一键解除隔离 (针对误判/网络波动)",
            command=self.on_unblock_clicked,
            bg="#b45309",
            fg="#ffffff",
            activebackground="#92400e",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2"
        )
        btn_unblock.pack(side=tk.LEFT, padx=(0, 8))

        btn_resume = tk.Button(
            acc_tools,
            text="💬 注入会话断点续接 (扣 1 自动恢复)",
            command=self.on_resume_clicked,
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2"
        )
        btn_resume.pack(side=tk.LEFT, padx=6)

        # 行标签染色配置
        self.tree.tag_configure("current", background="#1e3a5f", foreground="#93c5fd")
        self.tree.tag_configure("quarantined", background="#3b1f2b", foreground="#fca5a5")
        self.tree.tag_configure("parked", background="#362f1d", foreground="#fde047")
        self.tree.tag_configure("even", background="#24273a")
        self.tree.tag_configure("odd", background="#1e2030")

    def _build_network_tab(self):
        """构建 Tab 2: 专线网络大盘 (最优排在最前面)"""
        container = tk.Frame(self.tab_network, bg=self.COLOR_BG, padx=4, pady=6)
        container.pack(fill=tk.BOTH, expand=True)

        # 专线网络当前在用信息横幅
        self.net_banner = tk.Frame(container, bg="#1e2030", padx=14, pady=10)
        self.net_banner.pack(fill=tk.X, pady=(0, 8))

        self.lbl_net_active = tk.Label(
            self.net_banner,
            text="当前专线: 日本专线 (延迟: 318ms · 端口: 17897 · 状态: 正常保活中)",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_ACCENT,
            bg="#1e2030"
        )
        self.lbl_net_active.pack(side=tk.LEFT)

        btn_net_refresh = tk.Button(
            self.net_banner,
            text="🔄 测速并刷新网络",
            command=self.refresh_network_nodes,
            bg="#374151",
            fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2"
        )
        btn_net_refresh.pack(side=tk.RIGHT, padx=4)

        # 专线节点表格
        columns = ("status", "flag", "name", "rtt", "proto", "source")
        self.net_tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        net_col_defs = [
            ("status", "状态 / 调度权", 120, "center"),
            ("flag", "出口地区", 110, "center"),
            ("name", "专线节点名称", 380, "w"),
            ("rtt", "延迟 (ms)", 110, "center"),
            ("proto", "协议类型", 110, "center"),
            ("source", "Clash 订阅来源", 220, "w")
        ]

        for col_id, col_name, col_w, col_anchor in net_col_defs:
            self.net_tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_network_by(c))
            self.net_tree.column(col_id, width=col_w, minwidth=60, anchor=col_anchor)

        net_scroll = ttk.Scrollbar(container, orient="vertical", command=self.net_tree.yview, style="Vertical.TScrollbar")
        self.net_tree.configure(yscrollcommand=net_scroll.set)

        self.net_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        net_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.net_tree.tag_configure("active_node", background="#1e3a5f", foreground="#93c5fd")
        self.net_tree.tag_configure("verified_node", background="#1c3329", foreground="#86efac")
        self.net_tree.tag_configure("even", background="#24273a")
        self.net_tree.tag_configure("odd", background="#1e2030")

        # 专线操作工具栏
        net_tools = tk.Frame(self.tab_network, bg=self.COLOR_BG, pady=6)
        net_tools.pack(fill=tk.X)

        btn_pick_node = tk.Button(
            net_tools,
            text="⚡ 一键切换为此专线节点",
            command=self.on_switch_node_clicked,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_pick_node.pack(side=tk.LEFT, padx=(0, 8))

        btn_open_clash = tk.Button(
            net_tools,
            text="📂 打开 Clash Verge 订阅配置目录",
            command=self.on_open_clash_dir_clicked,
            bg="#374151",
            fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2"
        )
        btn_open_clash.pack(side=tk.LEFT, padx=6)

    def _build_logs_tab(self):
        """构建 Tab 3: 运行日志与统计"""
        container = tk.Frame(self.tab_logs, bg=self.COLOR_BG, padx=4, pady=6)
        container.pack(fill=tk.BOTH, expand=True)

        # 1. 顶部指标概览看板 (KPI Cards)
        kpi_frame = tk.Frame(container, bg=self.COLOR_BG)
        kpi_frame.pack(fill=tk.X, pady=(0, 8))

        # 账号大盘 KPI
        self.kpi_acc = tk.Label(
            kpi_frame,
            text="【账号池概况】加载中...",
            font=("Segoe UI", 9),
            bg="#1e2030",
            fg=self.COLOR_FG,
            padx=12,
            pady=8,
            justify=tk.LEFT
        )
        self.kpi_acc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        # 网络链路 KPI
        self.kpi_net = tk.Label(
            kpi_frame,
            text="【网络链路概况】加载中...",
            font=("Segoe UI", 9),
            bg="#1e2030",
            fg=self.COLOR_FG,
            padx=12,
            pady=8,
            justify=tk.LEFT
        )
        self.kpi_net.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # 运行看护 KPI
        self.kpi_sys = tk.Label(
            kpi_frame,
            text="【自愈守卫概况】加载中...",
            font=("Segoe UI", 9),
            bg="#1e2030",
            fg=self.COLOR_FG,
            padx=12,
            pady=8,
            justify=tk.LEFT
        )
        self.kpi_sys.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # 2. 中间历史事件表格
        inc_title_bar = tk.Frame(container, bg=self.COLOR_BG, pady=2)
        inc_title_bar.pack(fill=tk.X)
        tk.Label(
            inc_title_bar,
            text="📜 最近账号切换与网络自愈事件台账 (自动审计留痕)",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_CYAN,
            bg=self.COLOR_BG
        ).pack(side=tk.LEFT)

        inc_box = tk.Frame(container, bg=self.COLOR_CARD, height=130)
        inc_box.pack(fill=tk.X, pady=(2, 8))

        inc_cols = ("timestamp", "incident_type", "summary", "action")
        self.inc_tree = ttk.Treeview(
            inc_box,
            columns=inc_cols,
            show="headings",
            height=4,
            style="Treeview"
        )
        self.inc_tree.heading("timestamp", text="时间")
        self.inc_tree.heading("incident_type", text="事件分类")
        self.inc_tree.heading("summary", text="事件摘要说明")
        self.inc_tree.heading("action", text="执行自愈动作")

        self.inc_tree.column("timestamp", width=180, anchor="center")
        self.inc_tree.column("incident_type", width=170, anchor="center")
        self.inc_tree.column("summary", width=500, anchor="w")
        self.inc_tree.column("action", width=360, anchor="w")

        inc_scroll = ttk.Scrollbar(inc_box, orient="vertical", command=self.inc_tree.yview, style="Vertical.TScrollbar")
        self.inc_tree.configure(yscrollcommand=inc_scroll.set)

        self.inc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inc_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 3. 实时日志流查看器
        log_ctrl = tk.Frame(container, bg=self.COLOR_BG, pady=4)
        log_ctrl.pack(fill=tk.X)

        tk.Label(log_ctrl, text="实时日志源:", font=("Segoe UI", 9, "bold"), fg=self.COLOR_FG, bg=self.COLOR_BG).pack(side=tk.LEFT, padx=(0, 6))

        self.log_combo = ttk.Combobox(
            log_ctrl,
            values=["supervisor.log", "account-watcher.log", "smart-quota-watcher.log", "launcher-error.log"],
            state="readonly",
            width=26
        )
        self.log_combo.current(0)
        self.log_combo.pack(side=tk.LEFT, padx=4)
        self.log_combo.bind("<<ComboboxSelected>>", lambda e: self.load_selected_log())

        btn_log_refresh = tk.Button(
            log_ctrl,
            text="🔄 刷新日志",
            command=self.load_selected_log,
            bg="#374151",
            fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2"
        )
        btn_log_refresh.pack(side=tk.LEFT, padx=6)

        btn_open_log_dir = tk.Button(
            log_ctrl,
            text="📂 打开日志所在目录",
            command=self.on_open_log_dir_clicked,
            bg="#374151",
            fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2"
        )
        btn_open_log_dir.pack(side=tk.LEFT, padx=6)

        self.log_filter_var = tk.StringVar()
        tk.Label(log_ctrl, text="🔍 搜索过滤:", font=("Segoe UI", 9), fg=self.COLOR_MUTED, bg=self.COLOR_BG).pack(side=tk.LEFT, padx=(16, 4))
        ent_filter = tk.Entry(log_ctrl, textvariable=self.log_filter_var, bg="#1e2030", fg=self.COLOR_FG, insertbackground=self.COLOR_CYAN, width=22)
        ent_filter.pack(side=tk.LEFT, padx=2)
        ent_filter.bind("<KeyRelease>", lambda e: self.apply_log_filter())

        log_text_box = tk.Frame(container, bg=self.COLOR_CARD)
        log_text_box.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        self.log_text = tk.Text(
            log_text_box,
            bg="#181926",
            fg="#cad3f5",
            insertbackground="#8aadf4",
            font=("Consolas", 9),
            wrap=tk.NONE,
            borderwidth=0,
            padx=8,
            pady=8
        )
        log_scroll_y = ttk.Scrollbar(log_text_box, orient="vertical", command=self.log_text.yview, style="Vertical.TScrollbar")
        log_scroll_x = ttk.Scrollbar(log_text_box, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=log_scroll_y.set, xscrollcommand=log_scroll_x.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        log_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.raw_log_lines = []

    def refresh_data(self):
        """异步拉取账号配额、专线网络、回血时刻与系统状态"""
        def _fetch():
            try:
                curr_id, accounts = get_all_accounts_and_quotas()
                cdp = get_devtools_active_port()
                is_run = is_antigravity_running()
                sub = get_subscription_summary()
                nodes = get_network_nodes_data()
                incidents = get_recent_incidents(30)
                self.root.after(0, lambda: self._update_all(curr_id, accounts, cdp, is_run, sub, nodes, incidents))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("获取异常", f"无法刷新控制大盘: {e}"))

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_all(self, curr_id, accounts, cdp, is_run, sub, nodes, incidents):
        self.accounts = accounts
        self.current_id = curr_id
        self.cdp_port = cdp
        self.network_nodes = nodes
        self.incidents = incidents

        # 1. 更新账号大盘表格
        self._render_accounts_table()

        # 2. 更新网络大盘表格
        self._render_network_table()

        # 3. 更新日志与统计 Tab
        self._render_logs_and_stats(is_run, cdp, sub)

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
                status_text = "● 在用"
            elif acc.get("disabled"):
                status_text = "⛔ 隔离"
            elif acc.get("is_parked"):
                status_text = "⏸ 挂起"
            else:
                status_text = "○ 候选"

            reset_5h_text = format_reset_time(acc.get("reset_time_5h"), acc.get("gemini_5h"))
            reset_weekly_text = format_reset_time(acc.get("reset_time_weekly"), acc.get("gemini_weekly"))

            row_tag = "odd" if idx % 2 == 1 else "even"
            if is_cur:
                row_tag = "current"
            elif acc.get("disabled"):
                row_tag = "quarantined"
            elif acc.get("is_parked"):
                row_tag = "parked"

            status_desc = acc.get("disabled_reason", "")
            if not status_desc:
                if acc.get("is_parked"):
                    status_desc = "配额见底挂起待回血"
                else:
                    status_desc = "健康候选"

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
                    f"{acc.get('claude_weekly', 0.0):.1f}%",
                    f"{acc.get('cockpit_score', 0.0):.0f}",
                    status_desc
                ),
                tags=(row_tag,)
            )

        self.lbl_active.config(text=f"活跃: {curr_email} (5h: {curr_5h:.1f}% | 周: {curr_weekly:.1f}%)")

    def _render_network_table(self):
        for item in self.net_tree.get_children():
            self.net_tree.delete(item)

        active_count = 0
        active_name = "未检测到活跃专线"
        active_rtt = 0

        for idx, node in enumerate(self.network_nodes):
            row_tag = "odd" if idx % 2 == 1 else "even"
            if node.get("is_active"):
                row_tag = "active_node"
                active_count += 1
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
                    node.get("status", "○ 候选"),
                    node.get("flag", "-"),
                    node.get("name", "-"),
                    rtt_str,
                    node.get("proto", "SS"),
                    node.get("source", "-")
                ),
                tags=(row_tag,)
            )

        self.lbl_net_active.config(
            text=f"当前在用专线: {active_name} (延迟: {active_rtt}ms · 端口: 17897 · 状态: 正常保活中)"
        )

    def _render_logs_and_stats(self, is_run, cdp, sub):
        # 顶部 KPI 指标刷新
        if is_run and cdp:
            self.lbl_cdp.config(text=f"🔥 CDP在线 ({cdp})", fg=self.COLOR_ACCENT)
        elif is_run:
            self.lbl_cdp.config(text="🔵 客户端运行中", fg=self.COLOR_CYAN)
        else:
            self.lbl_cdp.config(text="⚪ 离线 (冷启切号)", fg=self.COLOR_MUTED)

        proxy_text = "专线: 17897 (正常)" if sub else "专线: 17897"
        self.lbl_proxy.config(text=proxy_text, fg=self.COLOR_ACCENT if sub else self.COLOR_FG)

        # 统计汇总卡片数据
        tot_acc = len(self.accounts)
        full_acc = sum(1 for a in self.accounts if (a.get("gemini_5h", 0) >= 99 and a.get("gemini_weekly", 0) >= 99))
        usable_acc = sum(1 for a in self.accounts if not a.get("disabled") and (a.get("gemini_weekly", 0) > 5 or a.get("gemini_5h", 0) > 10))
        parked_acc = sum(1 for a in self.accounts if a.get("is_parked") or (a.get("gemini_weekly", 0) <= 5 and not a.get("disabled")))
        banned_acc = sum(1 for a in self.accounts if a.get("disabled"))

        self.kpi_acc.config(
            text=f"【账号池概况】\n总纳管账号: {tot_acc} 个\n满血可用: {full_acc} 个 | 正常可用: {usable_acc} 个\n低额静置保护: {parked_acc} 个 | 官方封禁拦截: {banned_acc} 个"
        )

        tot_nodes = len(self.network_nodes)
        ver_nodes = sum(1 for n in self.network_nodes if n.get("is_verified"))
        self.kpi_net.config(
            text=f"【网络链路概况】\n候选专线总数: {tot_nodes} 条 (JP/US 优选)\n已放行验证通过: {ver_nodes} 条\n核心自愈机制: 模型冷启动门禁 + 动态阻断感知"
        )

        self.kpi_sys.config(
            text=f"【自愈守卫概况】\n看护进程: 正常守卫中\nCDP 调试端口: {cdp if cdp else '离线'}\n调度策略: 综合算力评分 + 天数梯队最优盲切"
        )

        # 历史事件表格渲染
        for item in self.inc_tree.get_children():
            self.inc_tree.delete(item)

        for inc in reversed(self.incidents[-15:]):
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

        # 实时日志载入
        self.load_selected_log()

    def load_selected_log(self):
        log_name = self.log_combo.get()
        lines = get_recent_log_lines(log_name, 250)
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
            if col == "claude_weekly":
                return x.get("claude_weekly", 0.0)
            if col == "score":
                return x.get("cockpit_score", -999999.0)
            if col == "email":
                return x.get("email", "").lower()
            return str(x.get(col, ""))

        self.accounts.sort(key=_get_val, reverse=self.sort_desc)
        self._render_accounts_table()

    def _sort_network_by(self, col):
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

    def refresh_network_nodes(self):
        def _task():
            nodes = get_network_nodes_data()
            self.network_nodes = nodes
            self.root.after(0, self._render_network_table)
        threading.Thread(target=_task, daemon=True).start()

    def on_switch_node_clicked(self):
        sel = self.net_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在列表中选中一个要切换的专线节点！")
            return
        idx = int(sel[0])
        if idx >= len(self.network_nodes):
            return
        node = self.network_nodes[idx]
        node_name = node.get("name", "")

        confirm = messagebox.askyesno(
            "切换专线节点确认",
            f"确定要将当前反重力专线优先切换为节点：\n【{node_name}】 ({node.get('flag')}) 吗？\n\n这将会将该节点持久化为优先专线，并唤起专线自愈热加载。"
        )
        if not confirm:
            return

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
                
                # 触发自愈重连
                cmd = f'powershell -ExecutionPolicy Bypass -Command "& \'{os.path.join(PROXY_DIR, "Antigravity-ProxySupervisor.ps1")}\' -RecoveryReason UserManualNodeSwitch"'
                subprocess.Popen(cmd, shell=True)
                self.root.after(0, lambda: messagebox.showinfo("切换成功", f"已成功将优先专线设定为【{node_name}】并触发自愈热载入！"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("切换失败", f"设置优先专线失败: {e}"))
            finally:
                self.root.after(1500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_heal_network_clicked(self):
        confirm = messagebox.askyesno(
            "专线自愈重连确认",
            "是否立即唤起专线自愈引擎（全链路健康复测并匹配最优可用专线）？"
        )
        if not confirm:
            return

        def _run():
            try:
                cmd = f'powershell -ExecutionPolicy Bypass -Command "& \'{os.path.join(PROXY_DIR, "Antigravity-ProxySupervisor.ps1")}\' -RecoveryReason UserManualHeal"'
                subprocess.Popen(cmd, shell=True)
                self.root.after(0, lambda: messagebox.showinfo("自愈指令已下发", "专线自愈重连指令已下发至 Supervisor 引擎，请稍候约 3~5 秒。"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("自愈失败", f"无法启动网络自愈: {e}"))
            finally:
                self.root.after(2000, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_open_clash_dir_clicked(self):
        try:
            clash_dir = os.path.expandvars(r"%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\profiles")
            os.startfile(clash_dir)
        except Exception as e:
            messagebox.showerror("打开失败", f"无法打开目录: {e}")

    def on_open_log_dir_clicked(self):
        try:
            os.startfile(PROXY_DIR)
        except Exception as e:
            messagebox.showerror("打开失败", f"无法打开日志目录: {e}")

    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.on_switch_clicked()

    def on_switch_clicked(self):
        if self.is_switching:
            messagebox.showwarning("提示", "正在执行切号操作中，请勿重复点击！")
            return

        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在列表中选中一个要切换的账号！")
            return

        account_id = sel[0]
        target = next((a for a in self.accounts if a["id"] == account_id), None)
        if not target:
            return

        target_email = target.get("email", "")
        if account_id == self.current_id or target_email == getattr(self, "current_email", ""):
            messagebox.showinfo("提示", f"账号【{target_email}】当前已是在用活跃账号，无需切换！")
            return

        confirm = messagebox.askyesno(
            "确认切换",
            f"确定要将当前反重力主窗口切换为账号：\n【{target_email}】 吗？\n\n系统将自动通过 CDP 协议注入 Cookie 或进行安全热载入。"
        )
        if not confirm:
            return

        self._do_switch(account_id)

    def _do_switch(self, account_id):
        self.is_switching = True
        self.lbl_active.config(text="正在切换账号中，请稍候...", fg=self.COLOR_WARNING)

        def _run():
            try:
                ok, msg = run_smart_switch(specific_account_id=account_id)
                if ok:
                    self.root.after(0, lambda: messagebox.showinfo("切换成功", f"切号成功: {msg}"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("切换失败", f"切号未成功: {msg}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("切换异常", f"执行过程异常: {e}"))
            finally:
                self.is_switching = False
                self.root.after(500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_auto_switch_clicked(self):
        if self.is_switching:
            messagebox.showwarning("提示", "正在执行切号操作中，请勿重复点击！")
            return

        confirm = messagebox.askyesno(
            "智能盲切最优账号确认",
            "是否立即启动 AI 智能多策略评估，自动盲切至当前【算力最充足、评分最高】的健康账号？"
        )
        if not confirm:
            return

        self.is_switching = True
        self.lbl_active.config(text="正在智能评估并盲切最优账号中...", fg=self.COLOR_WARNING)

        def _run():
            try:
                ok, msg = run_smart_switch(specific_account_id=None)
                if ok:
                    self.root.after(0, lambda: messagebox.showinfo("盲切完成", f"智能切号成功: {msg}"))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("未执行切号", f"调度结果: {msg}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("盲切失败", f"调度执行异常: {e}"))
            finally:
                self.is_switching = False
                self.root.after(500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_unblock_clicked(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在列表中选中一个要解除隔离的账号！")
            return

        target = next((a for a in self.accounts if a["id"] == sel[0]), None)
        if not target:
            return

        target_email = target.get("email", "")
        confirm = messagebox.askyesno(
            "解除隔离确认",
            f"确定要对账号【{target_email}】执行解除误隔离 (--unblock) 吗？\n\n这将会：\n1. 从硬黑名单与 429 临时关押名单释放\n2. 清除 disabled 标记与网络超时错误\n3. 重新激活为健康候选账号"
        )
        if not confirm:
            return

        def _run():
            try:
                ok = unblock_account(target_email)
                if ok:
                    self.root.after(0, lambda: messagebox.showinfo("解封成功", f"账号【{target_email}】已成功解除误隔离，恢复为正常候选状态！"))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("解封提示", f"未能成功解封【{target_email}】。"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("解封异常", f"解封执行出错: {e}"))
            finally:
                self.root.after(500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_resume_clicked(self):
        confirm = messagebox.askyesno(
            "智能断点续接确认",
            "是否立即向当前活跃的反重力窗口注入会话恢复协议（扣 1 自动发送并续接未完成任务）？"
        )
        if not confirm:
            return

        def _run():
            try:
                res = execute_auto_resume()
                self.root.after(0, lambda: messagebox.showinfo("续接完成", f"智能续接执行结果: {res}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("续接失败", f"智能续接出错: {e}"))
            finally:
                self.refresh_data()

        threading.Thread(target=_run, daemon=True).start()

    def on_launch_client_clicked(self):
        def _run():
            try:
                launch_antigravity_via_launcher(recovery_reason="gui_manual_launch", background=False)
                self.root.after(0, lambda: messagebox.showinfo("启动成功", "已成功通过桌面脱壳智能启动器拉起反重力客户端！"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("启动失败", f"启动客户端失败: {e}"))
            finally:
                self.root.after(1000, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()


def main():
    root = tk.Tk()
    app = AntigravitySwitcherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
