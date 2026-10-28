# -*- coding: utf-8 -*-
"""
antigravity_switcher_gui.py — 反重力 (Antigravity) 算力切号与恢复中枢 (Antigravity Switcher & Quota GUI)
现代化高颜值暗黑科技风 GUI，支持多账号配额一览无余、CP 软件精准回血时刻倒计时、双击秒切、智能盲切、误隔离一键解封与断点续接。
"""

import os
import sys
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
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 确保能载入 launcher 底层库
LAUNCHER_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Antigravity\launcher")
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

# 网络科技风图标
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


class AntigravitySwitcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("反重力 (Antigravity) 算力切号与恢复中枢 - ANTIGRAVITY STATION")
        self.root.geometry("1200x660")
        self.root.minsize(1020, 540)

        if ICON_PATH and os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(default=ICON_PATH)
            except Exception:
                pass

        # 主题色彩（暗黑科技风）
        self.COLOR_BG = "#181926"          # 极夜底色
        self.COLOR_CARD = "#24273a"        # 卡片底色
        self.COLOR_ROW_ALT = "#1e2030"     # 斑马纹行色
        self.COLOR_FG = "#cad3f5"          # 主文本亮白灰
        self.COLOR_MUTED = "#8087a2"       # 次要文本灰蓝
        self.COLOR_ACCENT = "#a6da95"      # 强调绿
        self.COLOR_CYAN = "#8aadf4"        # 科技青/蓝
        self.COLOR_BLUE = "#3b82f6"        # 按钮蓝
        self.COLOR_PURPLE = "#c6a0f6"      # 量子紫
        self.COLOR_ORANGE = "#f5a97f"      # 警告/回血橙
        self.COLOR_RED = "#ed8796"         # 耗尽/隔离浅红
        self.COLOR_CURRENT = "#1e3a5f"     # 当前在用高亮底

        self.root.configure(bg=self.COLOR_BG)

        # 数据缓存
        self.accounts = []
        self.current_id = None
        self.sort_col = "score"
        self.sort_desc = True
        self.cdp_port = None
        self.is_switching = False

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
        # 顶部标题与状态大盘区
        top_frame = tk.Frame(self.root, bg=self.COLOR_BG, padx=20, pady=14)
        top_frame.pack(fill=tk.X)

        title_box = tk.Frame(top_frame, bg=self.COLOR_BG)
        title_box.pack(side=tk.LEFT)

        lbl_title = tk.Label(
            title_box,
            text="反重力 (Antigravity) 算力切号与恢复中枢",
            font=("Segoe UI", 16, "bold"),
            fg=self.COLOR_FG,
            bg=self.COLOR_BG
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            title_box,
            text="100% 独立高科技调度 · CP 精准回血时刻感知 · CDP 断点热感续接 · 误隔离一键秒级解封",
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
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_ACCENT,
            bg="#1e2030",
            padx=10,
            pady=6,
            relief="flat"
        )
        self.lbl_cdp.pack(side=tk.LEFT, padx=4)

        self.lbl_active = tk.Label(
            self.stats_frame,
            text="当前活跃: 加载中...",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_CYAN,
            bg="#1e2030",
            padx=12,
            pady=6,
            relief="flat"
        )
        self.lbl_active.pack(side=tk.LEFT, padx=4)

        self.lbl_proxy = tk.Label(
            self.stats_frame,
            text="专线: 17897",
            font=("Segoe UI", 10),
            fg=self.COLOR_FG,
            bg="#1e2030",
            padx=10,
            pady=6,
            relief="flat"
        )
        self.lbl_proxy.pack(side=tk.LEFT, padx=4)

        # 中部表格区
        mid_frame = tk.Frame(self.root, bg=self.COLOR_BG, padx=20, pady=4)
        mid_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("status", "email", "gemini_5h", "reset_5h", "gemini_weekly", "reset_weekly", "claude_weekly", "score", "status_desc")
        self.tree = ttk.Treeview(
            mid_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Treeview"
        )

        col_defs = [
            ("status", "当前", 70, "center"),
            ("email", "登录账号 / 邮箱", 220, "w"),
            ("gemini_5h", "5h 配额", 85, "center"),
            ("reset_5h", "5h 精确回血时间 (CP同步)", 185, "center"),
            ("gemini_weekly", "周额度", 80, "center"),
            ("reset_weekly", "周额重置时刻 (CP同步)", 185, "center"),
            ("claude_weekly", "Claude 周额", 95, "center"),
            ("score", "综合算力分", 95, "center"),
            ("status_desc", "健康度与状态说明", 260, "w"),
        ]

        for col_id, col_name, col_w, col_anchor in col_defs:
            self.tree.heading(col_id, text=col_name, command=lambda c=col_id: self._sort_by(c))
            self.tree.column(col_id, width=col_w, minwidth=60, anchor=col_anchor)

        # 行标签颜色
        self.tree.tag_configure("odd", background=self.COLOR_CARD)
        self.tree.tag_configure("even", background=self.COLOR_ROW_ALT)
        self.tree.tag_configure("current", background=self.COLOR_CURRENT, foreground="#ffffff")
        self.tree.tag_configure("quarantined", foreground=self.COLOR_RED)
        self.tree.tag_configure("parked", foreground=self.COLOR_ORANGE)

        # 滚动条
        scrollbar = ttk.Scrollbar(mid_frame, orient=tk.VERTICAL, command=self.tree.yview, style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击秒切
        self.tree.bind("<Double-1>", self.on_double_click)

        # 底部操作栏
        bot_frame = tk.Frame(self.root, bg=self.COLOR_BG, padx=20, pady=14)
        bot_frame.pack(fill=tk.X)

        btn_switch = tk.Button(
            bot_frame,
            text="🎯 切换至所选账号",
            font=("Segoe UI", 10, "bold"),
            bg="#2e7d32",
            fg="#ffffff",
            activebackground="#1b5e20",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.on_switch_clicked
        )
        btn_switch.pack(side=tk.LEFT, padx=(0, 8))

        btn_auto = tk.Button(
            bot_frame,
            text="⚡ 一键智能盲切 (优选最佳)",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLOR_BLUE,
            fg="#ffffff",
            activebackground="#2563eb",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.on_auto_switch_clicked
        )
        btn_auto.pack(side=tk.LEFT, padx=(0, 8))

        btn_unblock = tk.Button(
            bot_frame,
            text="🛡️ 解除误隔离/解封 (--unblock)",
            font=("Segoe UI", 9),
            bg="#475569",
            fg="#f8fafc",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.on_unblock_clicked
        )
        btn_unblock.pack(side=tk.LEFT, padx=(0, 8))

        btn_resume = tk.Button(
            bot_frame,
            text="🚨 智能续接 (扣1恢复)",
            font=("Segoe UI", 9),
            bg="#475569",
            fg="#f8fafc",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.on_resume_clicked
        )
        btn_resume.pack(side=tk.LEFT, padx=(0, 8))

        btn_launch = tk.Button(
            bot_frame,
            text="🚀 打开客户端",
            font=("Segoe UI", 9),
            bg="#334155",
            fg=self.COLOR_CYAN,
            activebackground="#1e293b",
            activeforeground=self.COLOR_CYAN,
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.on_launch_client_clicked
        )
        btn_launch.pack(side=tk.LEFT, padx=(0, 8))

        btn_refresh = tk.Button(
            bot_frame,
            text="🔄 刷新",
            font=("Segoe UI", 10),
            bg="#3b4252",
            fg=self.COLOR_FG,
            activebackground="#4c566a",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.refresh_data
        )
        btn_refresh.pack(side=tk.RIGHT)

        lbl_hint = tk.Label(
            bot_frame,
            text="💡 双击行秒切 · 精准回血时刻实时同步自 CP 缓存",
            font=("Segoe UI", 9),
            fg=self.COLOR_MUTED,
            bg=self.COLOR_BG
        )
        lbl_hint.pack(side=tk.RIGHT, padx=10)

    def refresh_data(self):
        """异步拉取最新账号配额、回血时刻与系统状态"""
        def _fetch():
            try:
                curr_id, accounts = get_all_accounts_and_quotas()
                cdp = get_devtools_active_port()
                is_run = is_antigravity_running()
                sub = get_subscription_summary()
                self.root.after(0, lambda: self._update_table(curr_id, accounts, cdp, is_run, sub))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("数据拉取异常", f"无法加载反重力账号池: {e}"))

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_table(self, curr_id, accounts, cdp, is_run, sub):
        self.accounts = accounts
        self.current_id = curr_id
        self.cdp_port = cdp

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

            # 状态文案
            if is_cur:
                status_text = "● 在用"
            elif acc.get("disabled"):
                status_text = "⛔ 隔离"
            elif acc.get("is_parked"):
                status_text = "⏸ 挂起"
            else:
                status_text = "○ 候选"

            # 精准回血时间格式化
            reset_5h_text = format_reset_time(acc.get("reset_time_5h"), acc.get("gemini_5h"))
            reset_weekly_text = format_reset_time(acc.get("reset_time_weekly"), acc.get("gemini_weekly"))

            # 标签染色
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

        if is_run and cdp:
            self.lbl_cdp.config(text=f"🔥 CDP在线 ({cdp})", fg=self.COLOR_ACCENT)
        elif is_run:
            self.lbl_cdp.config(text="🔵 客户端运行中", fg=self.COLOR_CYAN)
        else:
            self.lbl_cdp.config(text="⚪ 离线 (冷启切号)", fg=self.COLOR_MUTED)

        proxy_text = "专线: 17897 (正常)" if sub else "专线: 17897"
        self.lbl_proxy.config(text=proxy_text, fg=self.COLOR_ACCENT if sub else self.COLOR_FG)

    def _sort_by(self, col):
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = True

        def _get_val(x):
            if col == "gemini_5h":
                return x.get("gemini_5h", 0.0)
            elif col == "gemini_weekly":
                return x.get("gemini_weekly", 0.0)
            elif col == "claude_weekly":
                return x.get("claude_weekly", 0.0)
            elif col == "score":
                return x.get("cockpit_score", 0.0)
            elif col == "reset_5h":
                return x.get("reset_time_5h") or datetime.min.replace(tzinfo=timezone.utc)
            elif col == "reset_weekly":
                return x.get("reset_time_weekly") or datetime.min.replace(tzinfo=timezone.utc)
            return str(x.get(col, ""))

        self.accounts.sort(key=_get_val, reverse=self.sort_desc)
        cdp = get_devtools_active_port()
        is_run = is_antigravity_running()
        sub = get_subscription_summary()
        self._update_table(self.current_id, self.accounts, cdp, is_run, sub)

    def on_double_click(self, event):
        sel = self.tree.selection()
        if sel:
            self._do_switch(sel[0])

    def on_switch_clicked(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在列表中选中一个要切换的账号！")
            return
        self._do_switch(sel[0])

    def _do_switch(self, account_id):
        if self.is_switching:
            messagebox.showinfo("提示", "切号正在执行中，请稍候...")
            return

        target = next((a for a in self.accounts if a["id"] == account_id), None)
        if not target:
            return

        if target.get("is_current") or target.get("id") == self.current_id:
            messagebox.showinfo("提示", f"当前已在使用该账号 ({target.get('email')})，无需重复切换。")
            return

        target_email = target.get("email", "")
        if target.get("disabled"):
            confirm = messagebox.askyesno(
                "账号当前被隔离",
                f"账号【{target_email}】当前处于隔离状态：\n\n原因：{target.get('disabled_reason', '未知')}\n\n是否先自动执行【解除隔离 (--unblock)】并强制切入该账号？"
            )
            if not confirm:
                return
            unblock_account(target_email)

        confirm = messagebox.askyesno(
            "确认切换账号",
            f"确定要切换到账号：\n\n【{target_email}】\n\n5h 配额: {target.get('gemini_5h', 0.0):.1f}%\n周 配 额: {target.get('gemini_weekly', 0.0):.1f}%\n\n是否继续？"
        )
        if not confirm:
            return

        self.is_switching = True

        def _run():
            try:
                res = run_smart_switch(target=target_email, force=True)
                if res in ("not_needed", "quota_pool_exhausted", "busy"):
                    self.root.after(0, lambda: messagebox.showwarning("切号提示", f"切号状态响应: {res}"))
                else:
                    self.root.after(0, lambda: messagebox.showinfo("切号完成", f"已成功触发切换至【{target_email}】！\n客户端已完成调度同步。"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("切号失败", f"切号执行异常: {e}"))
            finally:
                self.is_switching = False
                self.root.after(500, self.refresh_data)

        threading.Thread(target=_run, daemon=True).start()

    def on_auto_switch_clicked(self):
        if self.is_switching:
            messagebox.showinfo("提示", "切号正在执行中，请稍候...")
            return

        confirm = messagebox.askyesno(
            "智能盲切确认",
            "一键盲切将自动基于 Cockpit Tools 调度算法优选当前可用性最高、周额度充沛的账号。\n\n是否继续？"
        )
        if not confirm:
            return

        self.is_switching = True

        def _run():
            try:
                res = run_smart_switch(force=True)
                if res == "not_needed":
                    self.root.after(0, lambda: messagebox.showinfo("提示", "当前账号配额充沛，无需切换。"))
                elif res == "quota_pool_exhausted":
                    self.root.after(0, lambda: messagebox.showwarning("阻断", "全池备选账号周额度均已耗尽，已触发停切保护！"))
                else:
                    self.root.after(0, lambda: messagebox.showinfo("盲切完成", f"智能调度执行完毕：{res}"))
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
