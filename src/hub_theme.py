# -*- coding: utf-8 -*-
"""
hub_theme.py — AI 账号中枢同源桌面设计系统 (Hub Theme System for Desktop GUI)
与 8810 控制台 (console/index.html) 4-Theme Suite 100% 视觉对齐：
1. 拟态浅色 (neo) - 默认高质感浅灰蓝拟态，护眼高级
2. 沉浸暗夜 (midnight) - 深邃深黑，夜间极简科技感
3. 玻璃浅色 (glass) - 柔和通透蓝白

提供：
- 全局主题持久化 (~/.antigravity_cockpit/hub_theme_config.json)
- 原生 Windows 高 DPI 适配与抗锯齿优化
- 统一字体阶梯与 ttk 扁平现代控件样式渲染
- 快捷主题轮换器 (neo -> midnight -> glass -> neo)
"""

import os
import sys
import json
from pathlib import Path

# 1. Windows 原生高 DPI 穿透适配
def enable_high_dpi():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

# 2. 4-Theme 配色字典 (与 console/index.html CSS 变量 1:1 对齐)
THEMES = {
    "neo": {
        "id": "neo",
        "name": "拟态浅色",
        "icon": "🎨",
        "bg": "#e8edf3",
        "panel": "#e2eaf2",
        "card": "#edf2f6",
        "card_alt": "#dbe4ed",
        "border": "#d1dbe4",
        "ink": "#242c38",
        "muted": "#61758a",
        "dim": "#8b9baa",
        "primary": "#2f7ff5",
        "primary_hover": "#1d6fe8",
        "primary_fg": "#ffffff",
        "success": "#10b981",
        "success_bg": "#d1fae5",
        "warning": "#ecaa1c",
        "warning_bg": "#fef3c7",
        "danger": "#ef4444",
        "danger_bg": "#fee2e2",
        "active_row": "#dbeafe",
        "active_row_fg": "#1d4ed8",
        "select_bg": "#bfdbfe",
        "select_fg": "#1e3a8a",
        "tree_bg": "#e2eaf2",
        "tree_fg": "#242c38",
        "tree_heading_bg": "#d5e0ec",
        "tree_heading_fg": "#242c38",
        "chip_bg": "#d5e0ec",
        "chip_fg": "#374151",
        "scroll_bg": "#cbd5e1",
        "scroll_trough": "#e8edf3",
    },
    "midnight": {
        "id": "midnight",
        "name": "沉浸暗夜",
        "icon": "🌙",
        "bg": "#0e141d",
        "panel": "#16202e",
        "card": "#1d293a",
        "card_alt": "#121924",
        "border": "#26354a",
        "ink": "#e2e8f0",
        "muted": "#8b9cb3",
        "dim": "#64748b",
        "primary": "#38bdf8",
        "primary_hover": "#0ea5e9",
        "primary_fg": "#0f172a",
        "success": "#10b981",
        "success_bg": "#064e3b",
        "warning": "#f59e0b",
        "warning_bg": "#78350f",
        "danger": "#f43f5e",
        "danger_bg": "#881337",
        "active_row": "#1e3a5f",
        "active_row_fg": "#38bdf8",
        "select_bg": "#0284c7",
        "select_fg": "#ffffff",
        "tree_bg": "#16202e",
        "tree_fg": "#e2e8f0",
        "tree_heading_bg": "#1d293a",
        "tree_heading_fg": "#e2e8f0",
        "chip_bg": "#1d293a",
        "chip_fg": "#94a3b8",
        "scroll_bg": "#2a3749",
        "scroll_trough": "#0e141d",
    },
    "glass": {
        "id": "glass",
        "name": "玻璃浅色",
        "icon": "💎",
        "bg": "#edf3f8",
        "panel": "#e5edf5",
        "card": "#f0f4f9",
        "card_alt": "#dfe8f2",
        "border": "#d5e2ed",
        "ink": "#1e293b",
        "muted": "#64748b",
        "dim": "#738499",
        "primary": "#3b82f6",
        "primary_hover": "#2563eb",
        "primary_fg": "#ffffff",
        "success": "#10b981",
        "success_bg": "#d1fae5",
        "warning": "#f59e0b",
        "warning_bg": "#fef3c7",
        "danger": "#ef4444",
        "danger_bg": "#fee2e2",
        "active_row": "#dbeafe",
        "active_row_fg": "#1d4ed8",
        "select_bg": "#bfdbfe",
        "select_fg": "#1e3a8a",
        "tree_bg": "#e5edf5",
        "tree_fg": "#1e293b",
        "tree_heading_bg": "#dae6f1",
        "tree_heading_fg": "#1e293b",
        "chip_bg": "#dae6f1",
        "chip_fg": "#334155",
        "scroll_bg": "#cbd5e1",
        "scroll_trough": "#edf3f8",
    }
}

# 3. 字体体系 (Tkinter 标准 3 元组规范)
FONTS = {
    "title": ("Segoe UI", 15, "bold"),
    "subtitle": ("Segoe UI", 9),
    "head": ("Segoe UI", 10, "bold"),
    "body": ("Segoe UI", 10),
    "bold": ("Segoe UI", 10, "bold"),
    "mono": ("Consolas", 9),
    "btn": ("Segoe UI", 10, "bold"),
    "btn_sm": ("Segoe UI", 9, "bold"),
    "chip": ("Segoe UI", 9, "bold"),
    "badge": ("Segoe UI", 8, "bold"),
}

THEME_CONFIG_FILE = Path(os.path.expanduser("~/.antigravity_cockpit/hub_theme_config.json"))

def get_current_theme_id():
    """获取当前已保存的主题 ID，默认为 neo (拟态浅色)"""
    if THEME_CONFIG_FILE.is_file():
        try:
            data = json.loads(THEME_CONFIG_FILE.read_text(encoding="utf-8"))
            tid = data.get("theme", "neo")
            if tid in THEMES:
                return tid
        except Exception:
            pass
    return "neo"

def save_current_theme_id(theme_id):
    """持久化保存主题 ID"""
    if theme_id not in THEMES:
        return
    try:
        THEME_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        THEME_CONFIG_FILE.write_text(json.dumps({"theme": theme_id}, indent=2), encoding="utf-8")
    except Exception:
        pass

def get_theme(theme_id=None):
    """获取主题色彩字典"""
    if not theme_id:
        theme_id = get_current_theme_id()
    return THEMES.get(theme_id, THEMES["neo"])

def get_next_theme_id(current_id):
    """获取循环下一个主题 ID"""
    keys = list(THEMES.keys())
    idx = keys.index(current_id) if current_id in keys else 0
    return keys[(idx + 1) % len(keys)]

def apply_ttk_theme(style, theme):
    """为 ttk 控件配置与 AI 账号中枢对齐的现代无凸起平板样式"""
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # 1. 表格主体 Treeview
    style.configure(
        "Treeview",
        background=theme["tree_bg"],
        foreground=theme["tree_fg"],
        fieldbackground=theme["tree_bg"],
        rowheight=36,
        font=FONTS["body"],
        borderwidth=0,
        relief="flat"
    )
    style.map(
        "Treeview",
        background=[("selected", theme["select_bg"])],
        foreground=[("selected", theme["select_fg"])]
    )

    # 2. 表头 Treeview.Heading
    style.configure(
        "Treeview.Heading",
        background=theme["tree_heading_bg"],
        foreground=theme["tree_heading_fg"],
        font=FONTS["head"],
        borderwidth=0,
        relief="flat",
        padding=(8, 8)
    )
    style.map(
        "Treeview.Heading",
        background=[("active", theme["border"])],
        foreground=[("active", theme["primary"])]
    )

    # 3. 滚动条 TScrollbar
    style.configure(
        "Vertical.TScrollbar",
        gripcount=0,
        background=theme["scroll_bg"],
        darkcolor=theme["bg"],
        lightcolor=theme["scroll_bg"],
        troughcolor=theme["scroll_trough"],
        bordercolor=theme["bg"],
        arrowcolor=theme["muted"]
    )
