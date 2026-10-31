#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notification_center.py - 本地自动化流水线飞书统一事件中枢 (Unified Notification Center)
======================================================================================
核心设计哲学：
1. 飞书群是“状态面板”，不是“运行日志”；
2. 同一个事件全生命周期只占 1 条飞书消息，事件状态流转全程原地 PATCH 更新原消息；
3. 严格的事件唯一键 (event_key) 去重与生命周期管理，未关闭前严禁创建第二条独立消息；
4. 统一五级严重度与颜色规范：
   - INFO       -> 🟢 green   (正常 / 已完成 / 已恢复 / 无需处理)
   - WARNING    -> 🟡 yellow  (风险预警 / 当前仍能运行 / 建议处理)
   - PROCESSING -> 🟠 orange  (系统正在自动处理中)
   - ERROR      -> 🔴 red     (自动处理失败 / 需要人工介入)
   - CRITICAL   -> 🚨 carmine (极限熔断 / 保护模式)
5. 每条消息末尾必须明确回答：“我现在要不要做什么？”
   - 状态：正常运行 ｜ 无需处理
   - 状态：正在自愈 ｜ 正在自动处理
   - 状态：任务暂停 ｜ 需要人工处理
   - 状态：空间预警 ｜ 建议处理
6. 彻底剔除内部打分、重试堆栈、函数名、长路径等所有日志噪音；
7. 原地 PATCH 失败受控降级：有限重试 2 次，确实失效时发送 1 条标注“原状态消息更新失败，本条为状态接续”的接续卡片；
8. 覆盖八大流水线场景：
   - PRODUCTION_BATCH (批次完成通知：10套或60分钟触发一次，单套完成 0 条群打扰)
   - PRODUCTION_MASTER_CARD (素材生产总控卡：长期存在，单卡原地滚动更新)
   - PRODUCTION_ERROR (任务异常橙色，自愈转绿，超阈值 MAX_AUTO_RETRY=3 转红报警)
   - PRODUCTION_DAILY_SUMMARY (流水线每日日报：每天 1 次)
   - DISK_SPACE (C盘水位阶梯状态机：<15GB 橙卡清理，自愈转绿，不足转红，<8GB 熔断，同状态持续静默 0 刷屏)
   - ANTIGRAVITY_ACCOUNT_SWITCH (额度 <= 5% 橙卡切号，成功转绿，失败转红)
   - ANTIGRAVITY_NETWORK (20s 防抖，<20s 闪断 0 飞书，>=20s 橙卡自愈，恢复转绿，失败转红)
   - PIPELINE_STATE (启动/恢复/全部完成：普通自动启动 0 打扰，大重启/恢复发 1 条绿卡)
"""

import os
import sys
import time
import json
import uuid
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List, Tuple

# 日志初始化
logger = logging.getLogger("NotificationCenter")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 基础路径配置
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
CANONICAL_LEDGER_DIR = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy")
CANONICAL_LEDGER_FILE = os.path.join(CANONICAL_LEDGER_DIR, "feishu_notification_ledger.json")
LEGACY_LEDGER_FILE = os.path.join(CANONICAL_LEDGER_DIR, "event_notifications_ledger.json")

FEISHU_CONFIG_FILE = r"D:\AICode\AI\secrets\平台服务\飞书\feishu_config.json"

# 流水线全局阈值配置 (支持环境变量覆盖)
PRODUCTION_NOTIFY_BATCH_SIZE = int(os.environ.get("PRODUCTION_NOTIFY_BATCH_SIZE", 10))
PRODUCTION_NOTIFY_INTERVAL_MINUTES = int(os.environ.get("PRODUCTION_NOTIFY_INTERVAL_MINUTES", 60))
MAX_AUTO_RETRY = int(os.environ.get("MAX_AUTO_RETRY", 3))

DISK_WARNING_GB = float(os.environ.get("DISK_WARNING_GB", 25.0))
DISK_DANGER_GB = float(os.environ.get("DISK_DANGER_GB", 15.0))
DISK_CRITICAL_GB = float(os.environ.get("DISK_CRITICAL_GB", 8.0))

NETWORK_ALERT_DELAY_SECONDS = int(os.environ.get("NETWORK_ALERT_DELAY_SECONDS", 20))

# 内存 Token 缓存
_TOKEN_CACHE = {
    "token": None,
    "expires_at": 0.0
}


class Severity:
    INFO = "INFO"              # 🟢 green (正常 / 已完成 / 已恢复 / 无需处理)
    WARNING = "WARNING"        # 🟡 yellow (风险预警 / 当前仍能运行)
    PROCESSING = "PROCESSING"  # 🟠 orange (系统正在自动处理中)
    ERROR = "ERROR"            # 🔴 red (自动处理失败 / 需要人工介入)
    CRITICAL = "CRITICAL"      # 🚨 carmine (极限熔断 / 保护模式)


class EventStatus:
    OPEN = "OPEN"
    PROCESSING = "PROCESSING"
    SWITCHING = "SWITCHING"
    RECOVERING = "RECOVERING"
    SUCCESS = "SUCCESS"
    RESOLVED = "RESOLVED"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"
    CLOSED = "CLOSED"


class EventType:
    PRODUCTION_BATCH = "PRODUCTION_BATCH"
    PRODUCTION_MASTER_CARD = "PRODUCTION_MASTER_CARD"
    PRODUCTION_ERROR = "PRODUCTION_ERROR"
    PRODUCTION_DAILY_SUMMARY = "PRODUCTION_DAILY_SUMMARY"
    DISK_SPACE = "DISK_SPACE"
    ANTIGRAVITY_ACCOUNT_SWITCH = "ANTIGRAVITY_ACCOUNT_SWITCH"
    ANTIGRAVITY_NETWORK = "ANTIGRAVITY_NETWORK"
    PIPELINE_STATE = "PIPELINE_STATE"


COLOR_MAP = {
    Severity.INFO: "green",
    Severity.WARNING: "yellow",
    Severity.PROCESSING: "orange",
    Severity.ERROR: "red",
    Severity.CRITICAL: "carmine",
}


def _get_active_ledger_file() -> str:
    """获取账本路径（优先使用统一账本，兼顾旧账本迁移）"""
    if os.path.exists(CANONICAL_LEDGER_FILE):
        return CANONICAL_LEDGER_FILE
    if os.path.exists(LEGACY_LEDGER_FILE):
        return LEGACY_LEDGER_FILE
    return CANONICAL_LEDGER_FILE


def _load_ledger() -> Dict[str, Any]:
    """读取事件账本（多进程健壮读取与自动初始化）"""
    target_file = _get_active_ledger_file()
    try:
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "active_events" not in data:
                        data["active_events"] = {}
                    if "master_cards" not in data:
                        data["master_cards"] = {}
                    if "production_counters" not in data:
                        data["production_counters"] = {}
                    if "history" not in data:
                        data["history"] = []
                    return data
    except Exception as e:
        logger.debug(f"读取事件账本异常: {e}")
    return {
        "active_events": {},
        "master_cards": {},
        "production_counters": {},
        "history": []
    }


def _save_ledger(ledger: Dict[str, Any]):
    """原子写入保存事件账本"""
    try:
        os.makedirs(CANONICAL_LEDGER_DIR, exist_ok=True)
        temp_file = CANONICAL_LEDGER_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, CANONICAL_LEDGER_FILE)
    except Exception as e:
        logger.warning(f"保存事件账本异常: {e}")


def get_tenant_access_token(force_refresh: bool = False) -> Optional[str]:
    """获取飞书租户凭据 (tenant_access_token)，带内存及文件双级缓存"""
    global _TOKEN_CACHE
    now = time.time()
    if not force_refresh and _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["token"]

    if not os.path.exists(FEISHU_CONFIG_FILE):
        logger.debug(f"飞书配置文件不存在: {FEISHU_CONFIG_FILE}")
        return None

    try:
        with open(FEISHU_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        app_id = cfg.get("app_id")
        app_secret = cfg.get("app_secret")
        if not app_id or not app_secret:
            return None

        auth_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        auth_data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
        req = urllib.request.Request(auth_url, data=auth_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            if res_json.get("code") == 0:
                token = res_json.get("tenant_access_token")
                expires_in = res_json.get("expire", 7200)
                _TOKEN_CACHE["token"] = token
                _TOKEN_CACHE["expires_at"] = now + expires_in - 300  # 提前 5 分钟刷新
                return token
            else:
                logger.error(f"换取飞书 token 失败: {res_json.get('msg')}")
    except Exception as e:
        logger.error(f"获取飞书 token 网络异常: {e}")
    return None


def get_target_chat_id(chat_key: Optional[str] = None, event_type: Optional[str] = None) -> Optional[str]:
    """根据业务类型或群 key 智能路由目标群聊 ID (确保 100% 解析为 oc_ 开头的真实 ID)"""
    if chat_key and chat_key.startswith("oc_"):
        return chat_key

    if not os.path.exists(FEISHU_CONFIG_FILE):
        return None

    try:
        with open(FEISHU_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        chat_map = cfg.get("群列表", {})

        def resolve(val: Any) -> Optional[str]:
            if not val:
                return None
            val_str = str(val).strip()
            if val_str.startswith("oc_"):
                return val_str
            return chat_map.get(val_str)

        # 1. 显式指定已知别名
        if chat_key:
            res = resolve(chat_key) or resolve(cfg.get(chat_key))
            if res:
                return res

        # 2. 按 event_type 智能分流
        if event_type in (EventType.ANTIGRAVITY_ACCOUNT_SWITCH, EventType.ANTIGRAVITY_NETWORK):
            return resolve(cfg.get("account_switch_chat_id")) or resolve(cfg.get("infra_ops_chat_id")) or resolve(cfg.get("account_switch_chat")) or resolve("🚨-安全与验证码紧急报警")
        elif event_type == EventType.DISK_SPACE:
            return resolve(cfg.get("storage_clean_chat_id")) or resolve(cfg.get("storage_clean_chat")) or resolve("W-电脑空间清理和备份")
        elif event_type in (EventType.PRODUCTION_BATCH, EventType.PRODUCTION_MASTER_CARD, EventType.PRODUCTION_ERROR):
            return resolve(cfg.get("task_delivery_chat_id")) or resolve(cfg.get("task_delivery_chat")) or resolve("A-团建API生产线") or resolve("团建内容自动化生产线")
        elif event_type in (EventType.PRODUCTION_DAILY_SUMMARY, EventType.PIPELINE_STATE):
            return resolve(cfg.get("task_delivery_chat_id")) or resolve(cfg.get("task_delivery_chat")) or resolve("A-团建API生产线") or resolve("AI中控")

        # 3. 兜底
        return resolve(cfg.get("reminder_default_chat_id")) or resolve(cfg.get("default_chat")) or resolve("飞书牛马 CLI 私聊")
    except Exception as e:
        logger.error(f"解析飞书目标群聊异常: {e}")
        return None


def _build_interactive_card(title: str, color: str, content_str: str) -> Dict[str, Any]:
    """统一构建标准飞书交互卡片 JSON"""
    valid_colors = {"green", "yellow", "orange", "red", "carmine", "blue", "grey", "violet", "indigo", "turquoise"}
    template_color = color.lower() if color.lower() in valid_colors else "orange"
    if color == "red":
        template_color = "red"
    elif color in ("carmine", "critical"):
        template_color = "carmine"
    elif color == "yellow":
        template_color = "yellow"
    elif color == "green":
        template_color = "green"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": template_color
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content_str
                }
            }
        ]
    }


def send_interactive_card(chat_id: str, card_dict: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """向指定群聊发送初始交互卡片，返回 (成功标志, message_id, 错误信息)"""
    token = get_tenant_access_token()
    if not token:
        return False, None, "获取 tenant_access_token 失败"

    if not chat_id or not chat_id.startswith("oc_"):
        return False, None, f"无效的目标 chat_id: {chat_id}"

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card_dict, ensure_ascii=False)
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            if res_json.get("code") == 0:
                msg_id = res_json.get("data", {}).get("message_id")
                return True, msg_id, None
            else:
                return False, None, f"飞书API报错 code={res_json.get('code')}: {res_json.get('msg')}"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        return False, None, f"发送网络异常 HTTP {e.code}: {err_body}"
    except Exception as e:
        return False, None, f"发送网络异常: {e}"


def update_interactive_card(message_id: str, card_dict: Dict[str, Any], max_retries: int = 2) -> Tuple[bool, Optional[str]]:
    """通过 PATCH 原位编辑飞书卡片消息（含 2 次重试与鉴权自愈）"""
    if not message_id:
        return False, "缺少 message_id"

    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
    payload = {
        "content": json.dumps(card_dict, ensure_ascii=False)
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    last_error = ""
    for attempt in range(max_retries + 1):
        token = get_tenant_access_token(force_refresh=(attempt > 0))
        if not token:
            last_error = "无法获取有效 token"
            continue

        try:
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8"
                },
                method="PATCH"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                if res_json.get("code") == 0:
                    return True, None
                else:
                    last_error = f"code={res_json.get('code')}: {res_json.get('msg')}"
                    logger.warning(f"PATCH 飞书消息失败 (第 {attempt+1} 次): {last_error}")
        except urllib.error.HTTPError as e:
            err_content = e.read().decode("utf-8") if e.fp else ""
            last_error = f"HTTP {e.code}: {err_content}"
            logger.warning(f"PATCH 飞书消息 HTTP 错误 (第 {attempt+1} 次): {last_error}")
        except Exception as e:
            last_error = f"网络异常: {e}"
            logger.warning(f"PATCH 飞书消息异常: {last_error}")

        if attempt < max_retries:
            time.sleep(1.0)

    return False, last_error


# ==============================================================================
# 统一 NotificationCenter 类封装
# ==============================================================================

class NotificationCenter:
    """全流水线统一飞书事件中枢单例"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(NotificationCenter, cls).__new__(cls)
        return cls._instance

    # --------------------------------------------------------------------------
    # 基础事件生命周期：创建、更新、关闭、标记失败
    # --------------------------------------------------------------------------

    def create_event(
        self,
        event_type: str,
        event_key: str,
        title: str,
        color: str,
        elements: List[str],
        chat_key: Optional[str] = None,
        severity: str = Severity.PROCESSING,
        action_required: str = "正在自动处理",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        创建新的事件状态卡片。
        若同一个 event_key 已存在未关闭事件，自动更新原卡片，绝不创建新卡片！
        """
        ledger = _load_ledger()
        active_events = ledger.setdefault("active_events", {})

        # 幂等保护：同一个 event_key 正在运行，直接更新
        if event_key in active_events:
            existing = active_events[event_key]
            logger.info(f"[事件防重] 事件 {event_key} 处于活跃中 (message_id={existing.get('feishu_message_id')})，转入原地更新")
            ok, err = self.update_event(
                event_id=existing.get("event_id"),
                title=title,
                color=color,
                elements=elements,
                new_status=EventStatus.PROCESSING,
                action_required=action_required,
                metadata=metadata
            )
            return ok, existing.get("event_id"), err

        chat_id = get_target_chat_id(chat_key, event_type=event_type)
        if not chat_id:
            logger.warning(f"未找到事件目标飞书群 (chat_key={chat_key}, event_type={event_type})")
            return False, None, "未配置目标群聊"

        # 规范最后一行回答：“我现在要不要做什么？”
        final_elements = list(elements)
        if not any("无需处理" in el or "正在自动处理" in el or "人工处理" in el or "建议处理" in el for el in final_elements):
            final_elements.append(f"状态：{action_required} ｜ ▶ {action_required}")

        content_str = "\n\n".join(final_elements)
        card_json = _build_interactive_card(title, color, content_str)

        ok, msg_id, err = send_interactive_card(chat_id, card_json)
        if not ok:
            logger.error(f"创建事件飞书卡片失败: {err}")
            return False, None, err

        event_id = str(uuid.uuid4())
        event_data = {
            "event_id": event_id,
            "event_type": event_type,
            "event_key": event_key,
            "status": EventStatus.PROCESSING,
            "severity": severity,
            "color": color,
            "chat_id": chat_id,
            "feishu_message_id": msg_id,
            "title": title,
            "created_at": time.time(),
            "updated_at": time.time(),
            "action_required": action_required,
            "metadata": metadata or {}
        }

        active_events[event_key] = event_data
        _save_ledger(ledger)
        logger.info(f"✨ 成功创建飞书事件 [{event_type}] key={event_key} msg_id={msg_id}")
        return True, event_id, None

    def update_event(
        self,
        event_id: str,
        title: str,
        color: str,
        elements: List[str],
        new_status: str = EventStatus.PROCESSING,
        action_required: str = "正在自动处理",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """原地 PATCH 更新指定事件卡片，失败则受控降级接续"""
        ledger = _load_ledger()
        active_events = ledger.setdefault("active_events", {})

        target_key = None
        target_event = None
        for k, ev in active_events.items():
            if ev.get("event_id") == event_id:
                target_key = k
                target_event = ev
                break

        if not target_event:
            return False, f"未找到活跃事件 event_id={event_id}"

        msg_id = target_event.get("feishu_message_id")
        final_elements = list(elements)
        if not any("无需处理" in el or "正在自动处理" in el or "人工处理" in el or "建议处理" in el for el in final_elements):
            final_elements.append(f"状态：{action_required} ｜ ▶ {action_required}")

        content_str = "\n\n".join(final_elements)
        card_json = _build_interactive_card(title, color, content_str)

        ok, err = update_interactive_card(msg_id, card_json)
        if not ok:
            logger.warning(f"原地 PATCH 失败 ({err})，尝试受控接续降级...")
            # 降级：仅当原消息无法编辑时发送 1 条标注接续卡片
            chat_id = target_event.get("chat_id")
            if chat_id:
                fallback_elements = [
                    "⚠️ **原状态消息更新失败，本条为状态接续。**",
                    content_str
                ]
                fallback_card = _build_interactive_card(title, color, "\n\n".join(fallback_elements))
                s_ok, new_msg_id, s_err = send_interactive_card(chat_id, fallback_card)
                if s_ok:
                    target_event["feishu_message_id"] = new_msg_id
                    logger.info(f"受控降级成功，接续至新 message_id={new_msg_id}")
                    ok = True
                else:
                    return False, f"原地更新与接续均失败: {err} / {s_err}"

        target_event["status"] = new_status
        target_event["color"] = color
        target_event["title"] = title
        target_event["updated_at"] = time.time()
        target_event["action_required"] = action_required
        if metadata:
            target_event.setdefault("metadata", {}).update(metadata)

        _save_ledger(ledger)
        logger.info(f"🔄 成功更新事件 [{target_event.get('event_type')}] key={target_key} status={new_status}")
        return True, None

    def close_event(
        self,
        event_id: str,
        title: str,
        color: str,
        elements: List[str],
        final_status: str = EventStatus.SUCCESS,
        action_required: str = "无需处理",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        关闭事件：原地更新为终态卡片，移出 active_events 并归档到 history。
        后续发生新故障时将创建全新独立卡片，绝不混淆！
        """
        ledger = _load_ledger()
        active_events = ledger.setdefault("active_events", {})
        history = ledger.setdefault("history", [])

        target_key = None
        target_event = None
        for k, ev in active_events.items():
            if ev.get("event_id") == event_id:
                target_key = k
                target_event = ev
                break

        if not target_event:
            return False, f"未找到活跃事件 event_id={event_id}"

        # 原地更新为终局状态（通常为绿色）
        ok, err = self.update_event(
            event_id=event_id,
            title=title,
            color=color,
            elements=elements,
            new_status=final_status,
            action_required=action_required,
            metadata=metadata
        )

        # 归档闭环
        del active_events[target_key]
        target_event["closed_at"] = time.time()
        target_event["status"] = final_status
        history.append(target_event)
        # 仅保留最近 100 条归档
        if len(history) > 100:
            ledger["history"] = history[-100:]

        _save_ledger(ledger)
        logger.info(f"🏁 事件闭环归档 [{target_event.get('event_type')}] key={target_key} final_status={final_status}")
        return ok, err

    def mark_event_failed(
        self,
        event_id: str,
        title: str,
        elements: List[str],
        human_readable_error: str,
        at_all: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        标记事件处理失败：原地置红 🔴，明确提示人工介入，按配置 @负责人。
        """
        fail_elements = list(elements)
        fail_elements.extend([
            f"❌ **处理失败**: {human_readable_error}",
            "▶ **需要人工处理**"
        ])
        if at_all:
            fail_elements.append("<at user_id=\"all\">所有人</at>")

        return self.close_event(
            event_id=event_id,
            title=title,
            color="red",
            elements=fail_elements,
            final_status=EventStatus.FAILED,
            action_required="需要人工处理",
            metadata=metadata
        )

    # --------------------------------------------------------------------------
    # 模块一：素材生产 / 图文交付与批量进度 (Production & Batch Progress)
    # --------------------------------------------------------------------------

    def on_single_item_completed(
        self,
        season: str,
        title: str,
        set_idx: int,
        target_total: int = 781,
        duration_sec: float = 0.0,
        img_count: int = 10,
        is_success: bool = True,
        error_msg: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        单套生产完成回调：
        1. 默认坚决不发送单套飞书消息（彻底消除每套刷屏）；
        2. 累加批次计数器与当日计数器；
        3. 自动更新长期存在的【素材生产总控卡】；
        4. 检查是否触发批次战报：达到 10 套 或 满 60 分钟触发一次批次卡片。
        """
        ledger = _load_ledger()
        counters = ledger.setdefault("production_counters", {})
        today_str = time.strftime("%Y-%m-%d")

        today_stat = counters.setdefault(today_str, {
            "today_done": 0,
            "today_success": 0,
            "today_failed": 0,
            "batch_done": 0,
            "batch_start_time": time.time(),
            "latest_title": title,
            "current_season": season
        })

        today_stat["today_done"] += 1
        if is_success:
            today_stat["today_success"] += 1
        else:
            today_stat["today_failed"] += 1

        today_stat["batch_done"] += 1
        today_stat["latest_title"] = title
        today_stat["total_done"] = set_idx

        # 更新长期存在的总控卡
        self.update_production_master_card(
            season=season,
            current_done=set_idx,
            target_total=target_total,
            today_done=today_stat["today_done"],
            today_failed=today_stat["today_failed"],
            latest_title=title,
            current_task=f"第 {set_idx + 1} 套预备中"
        )

        # 检查批次通知条件：套数达标 或 时间达标
        batch_size = today_stat["batch_done"]
        time_elapsed_min = (time.time() - today_stat.get("batch_start_time", time.time())) / 60.0

        should_trigger_batch = False
        trigger_reason = ""
        if batch_size >= PRODUCTION_NOTIFY_BATCH_SIZE:
            should_trigger_batch = True
            trigger_reason = f"满 {batch_size} 套批次阈值"
        elif time_elapsed_min >= PRODUCTION_NOTIFY_INTERVAL_MINUTES and batch_size > 0:
            should_trigger_batch = True
            trigger_reason = f"满 {time_elapsed_min:.0f} 分钟定时阈值"

        if should_trigger_batch:
            logger.info(f"触发生产批次通知 ({trigger_reason})...")
            self.notify_production_batch(
                season=season,
                batch_done=batch_size,
                batch_target=PRODUCTION_NOTIFY_BATCH_SIZE,
                total_done=set_idx,
                target_total=target_total,
                today_done=today_stat["today_done"],
                today_success=today_stat["today_success"],
                today_failed=today_stat["today_failed"],
                latest_title=title,
                img_count=img_count
            )
            # 重置当前批次计数
            today_stat["batch_done"] = 0
            today_stat["batch_start_time"] = time.time()

        _save_ledger(ledger)
        return today_stat

    def notify_production_batch(
        self,
        season: str,
        batch_done: int,
        batch_target: int,
        total_done: int,
        target_total: int,
        today_done: int,
        today_success: int,
        today_failed: int,
        latest_title: str,
        img_count: int = 10
    ) -> Tuple[bool, Optional[str]]:
        """发送批次完成通知（每 10 套或每 60 分钟一次）"""
        percent = (total_done / target_total * 100) if target_total > 0 else 0.0
        remaining = max(0, target_total - total_done)

        title = f"🍂【{season}素材｜批次完成】"
        elements = [
            f"🟢 **本批次：{batch_done} / {batch_target} 套完成**",
            f"**累计进度**：\n• **{total_done} / {target_total} 套** ({percent:.1f}%)\n• 剩余：**{remaining} 套**",
            f"**今日大盘**：\n• 今日完成：**{today_done}** 套 ｜ 成功：**{today_success}** ｜ 异常：**{today_failed}**",
            f"🆕 **最近完成**：\n《{latest_title}》",
            f"📦 **标准交付**：\n• {img_count} 张 3:4 竖版成品大图\n• 小红书 / HR决策 / 抖音 三端文案",
            f"📂 [📁 成品库直达](file:///D:/AICode/项目推进/projects/江湖有旅人/主项目/03-成品库) ｜ 📊 [飞书多维台账](https://my.feishu.cn/sheets/D7OMsirIChkd2gt8TMBcPHD9ndc?sheet=hp4PGN)",
            f"▶ **下一步**：继续{season}素材生产",
            "状态：正常运行 ｜ 无需处理"
        ]

        # 批次完成是一次里程碑，每个批次使用新 event_key 记录一次
        batch_id = int(time.time() // 60)
        event_key = f"prod_batch_{season}_{batch_id}"
        ok, ev_id, err = self.create_event(
            event_type=EventType.PRODUCTION_BATCH,
            event_key=event_key,
            title=title,
            color="green",
            elements=elements,
            severity=Severity.INFO,
            action_required="无需处理"
        )
        return ok, err

    def update_production_master_card(
        self,
        season: str,
        current_done: int,
        target_total: int,
        today_done: int,
        today_failed: int,
        latest_title: str,
        current_task: str
    ) -> Tuple[bool, Optional[str]]:
        """
        素材生产总控卡：全生命周期只创建 1 条，后续无论生产多少套，原地滚动更新！
        """
        ledger = _load_ledger()
        master_cards = ledger.setdefault("master_cards", {})
        card_key = f"prod_master_card_{season}"

        percent = (current_done / target_total * 100) if target_total > 0 else 0.0
        remaining = max(0, target_total - current_done)

        # 进度条渲染 (20格)
        filled = int(percent / 5)
        bar = "█" * filled + "░" * (20 - filled)

        title = f"🍂【{season}素材生产总控】"
        elements = [
            "🟢 **当前运行正常**",
            f"**总进度**：\n• **{current_done} / {target_total} 套** ({percent:.1f}%)\n`{bar}`",
            f"**今日统计**：\n• 今日完成：**{today_done}** 套 ｜ 今日异常：**{today_failed}** ｜ 累计剩余：**{remaining}** 套",
            f"🆕 **最近完成**：\n《{latest_title}》",
            f"⚡ **当前任务**：\n《{current_task}》",
            "状态：生产中 ｜ 无需处理"
        ]

        card_json = _build_interactive_card(title, "green", "\n\n".join(elements))

        if card_key in master_cards:
            msg_id = master_cards[card_key].get("feishu_message_id")
            ok, err = update_interactive_card(msg_id, card_json)
            if ok:
                master_cards[card_key]["updated_at"] = time.time()
                _save_ledger(ledger)
                return True, None
            logger.warning(f"总控卡更新失败 ({err})，尝试重新建卡")

        # 首次创建
        chat_id = get_target_chat_id(event_type=EventType.PRODUCTION_MASTER_CARD)
        if not chat_id:
            return False, "未找到目标群聊"

        ok, msg_id, err = send_interactive_card(chat_id, card_json)
        if ok:
            master_cards[card_key] = {
                "card_key": card_key,
                "feishu_message_id": msg_id,
                "chat_id": chat_id,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            _save_ledger(ledger)
            logger.info(f"✨ 长期总控卡初次创建成功 msg_id={msg_id}")
            return True, None
        return False, err

    def notify_production_error(
        self,
        task_title: str,
        current_page: int,
        total_pages: int,
        error_summary: str,
        retry_count: int = 1
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        单套生产异常通知：
        首次异常创建 1 张橙卡，提示自动重试。
        """
        event_key = f"prod_error_{task_title}"
        title = "🔴【素材流水线｜任务异常】"
        elements = [
            f"**任务**：\n《{task_title}》",
            f"**进度**：\n第 {current_page} / {total_pages} 张",
            f"**异常**：\n{error_summary}",
            f"**系统状态**：\n🛡️ 已保存当前进度\n🟠 正在自动重试 (第 {retry_count}/{MAX_AUTO_RETRY} 次)",
            "状态：正在自动处理 ｜ 当前无需人工处理"
        ]
        return self.create_event(
            event_type=EventType.PRODUCTION_ERROR,
            event_key=event_key,
            title=title,
            color="orange",
            elements=elements,
            severity=Severity.PROCESSING,
            action_required="正在自动处理",
            metadata={"task_title": task_title, "retry_count": retry_count}
        )

    def notify_production_error_recovered(
        self,
        task_title: str,
        error_summary: str
    ) -> Tuple[bool, Optional[str]]:
        """
        异常自动恢复通知：
        原地更新原橙卡为绿卡，禁止发送第二条“恢复成功”新消息！
        """
        ledger = _load_ledger()
        event_key = f"prod_error_{task_title}"
        ev = ledger.get("active_events", {}).get(event_key)
        if not ev:
            return True, None

        title = "🟢【素材流水线｜异常已恢复】"
        elements = [
            f"**任务**：\n《{task_title}》",
            f"**原异常**：\n{error_summary}",
            "✅ 已重新生成\n✅ 质检通过\n✅ 流水线继续运行",
            "状态：正常 ｜ 无需处理"
        ]
        return self.close_event(
            event_id=ev.get("event_id"),
            title=title,
            color="green",
            elements=elements,
            final_status=EventStatus.SUCCESS,
            action_required="无需处理"
        )

    def notify_production_error_failed(
        self,
        task_title: str,
        error_summary: str,
        attempts: int = 3
    ) -> Tuple[bool, Optional[str]]:
        """
        重试超限彻底失败：
        原地更新原卡为红卡，明确提示需要人工处理，并 @负责人。
        """
        ledger = _load_ledger()
        event_key = f"prod_error_{task_title}"
        ev = ledger.get("active_events", {}).get(event_key)
        if not ev:
            # 若不存在则创建
            _, ev_id, _ = self.notify_production_error(task_title, 0, 10, error_summary, attempts)
            ev = {"event_id": ev_id}

        title = "🔴【素材流水线｜自动恢复失败】"
        elements = [
            f"**任务**：\n《{task_title}》",
            f"**异常**：\n{error_summary}",
            f"**已尝试**：\n{attempts} 次自动恢复全部受阻",
            "**当前状态**：\n任务已暂停 ｜ 其他安全任务可继续运行",
            "▶ **需要人工处理**"
        ]
        return self.mark_event_failed(
            event_id=ev.get("event_id"),
            title=title,
            elements=elements,
            human_readable_error=error_summary,
            at_all=True
        )

    # --------------------------------------------------------------------------
    # 模块二：C 盘 / 磁盘空间生命周期通知 (Disk Space Lifecycle)
    # --------------------------------------------------------------------------

    def notify_disk_danger_starting(
        self,
        c_free_gb: float,
        safe_line_gb: float = DISK_DANGER_GB
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        C 盘低于 15GB 首次跌入：
        创建橙色自愈卡片 🟠【C盘空间不足｜正在自动处理】
        """
        event_key = "disk_alert_C"
        title = "🟠【C盘空间不足｜正在自动处理】"
        elements = [
            f"• **当前可用**：**{c_free_gb:.2f} GB** 🔴\n• **安全标准**：{safe_line_gb:.1f} GB",
            "**正在执行自动清理**：\n• Temp 系统临时碎片清理\n• Updater 残留安装包清理\n• WorkBuddy 历史日志归档\n• Win32 回收站清空",
            "🛡️ **任务安全**：Codex 多窗口运行任务、平台身份凭据、剪映草稿工程已保护，清理流程不触碰。",
            "状态：自动处理中… ｜ 正在自动处理"
        ]
        return self.create_event(
            event_type=EventType.DISK_SPACE,
            event_key=event_key,
            title=title,
            color="orange",
            elements=elements,
            severity=Severity.PROCESSING,
            action_required="正在自动处理",
            metadata={"before_c_free": c_free_gb}
        )

    def notify_disk_recovered(
        self,
        before_gb: float,
        current_gb: float,
        released_mb: float
    ) -> Tuple[bool, Optional[str]]:
        """
        清理后成功恢复安全线：
        原地将原卡片更新为 🟢【C盘空间｜风险已解除】并关闭事件！
        """
        ledger = _load_ledger()
        event_key = "disk_alert_C"
        ev = ledger.get("active_events", {}).get(event_key)

        title = "🟢【C盘空间｜风险已解除】"
        released_str = f"{released_mb/1024:.2f} GB" if released_mb >= 1024 else f"{released_mb:.1f} MB"
        elements = [
            f"• **处理前**：{before_gb:.2f} GB\n• **当前可用**：**{current_gb:.2f} GB** 🟢\n• **本次释放**：**+{released_str}**",
            "✅ 已恢复安全空间水位\n✅ 所有 AI 任务健康正常运行中",
            "状态：正常 ｜ 无需处理"
        ]

        if ev:
            return self.close_event(
                event_id=ev.get("event_id"),
                title=title,
                color="green",
                elements=elements,
                final_status=EventStatus.SUCCESS,
                action_required="无需处理"
            )
        else:
            # 若之前无活跃卡片（如正常巡检恢复），发单条绿卡后闭环
            ok, ev_id, err = self.create_event(
                event_type=EventType.DISK_SPACE,
                event_key=event_key,
                title=title,
                color="green",
                elements=elements,
                severity=Severity.INFO,
                action_required="无需处理"
            )
            if ok and ev_id:
                self.close_event(ev_id, title, "green", elements, EventStatus.SUCCESS, "无需处理")
            return ok, err

    def notify_disk_cleanup_insufficient(
        self,
        before_gb: float,
        current_gb: float,
        released_mb: float,
        top_candidates_desc: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """
        清理效果不足（例如仅释放 1.1MB，空间仍低于 15GB）：
        坚决杜绝误导写自愈成功！原地更新原卡为 🔴【C盘空间｜自动清理未解除风险】！
        """
        ledger = _load_ledger()
        event_key = "disk_alert_C"
        ev = ledger.get("active_events", {}).get(event_key)

        title = "🔴【C盘空间｜自动清理未解除风险】"
        released_str = f"{released_mb/1024:.2f} GB" if released_mb >= 1024 else f"{released_mb:.1f} MB"
        elements = [
            f"• **当前可用**：**{current_gb:.2f} GB** 🔴\n• **安全标准**：15.00 GB\n• **本次释放**：+{released_str}",
            "⚠️ **当前仍低于安全线，自动清理未彻底解除风险**",
            f"**下一步建议**：\n已扫描大文件候选，等待进一步迁移 / 人工确认。\n{top_candidates_desc}".strip(),
            "🛡️ **当前任务**：已进入高写盘防护模式，活跃任务完成落盘",
            "▶ **建议处理**"
        ]

        if ev:
            return self.update_event(
                event_id=ev.get("event_id"),
                title=title,
                color="red",
                elements=elements,
                new_status=EventStatus.FAILED,
                action_required="建议处理"
            )
        else:
            ok, ev_id, err = self.create_event(
                event_type=EventType.DISK_SPACE,
                event_key=event_key,
                title=title,
                color="red",
                elements=elements,
                severity=Severity.ERROR,
                action_required="建议处理"
            )
            return ok, err

    def notify_disk_critical_circuit_breaker(
        self,
        current_gb: float
    ) -> Tuple[bool, Optional[str]]:
        """
        C 盘低于 8GB 极限熔断：
        🚨【C盘空间｜进入保护模式】
        """
        ledger = _load_ledger()
        event_key = "disk_alert_C"
        ev = ledger.get("active_events", {}).get(event_key)

        title = "🚨【C盘空间｜进入保护模式】"
        elements = [
            f"• **当前可用**：**{current_gb:.2f} GB** 🚨 (已跌破 8.0 GB 极限底线)",
            "**熔断策略已生效**：\n• 已停止启动新的高写盘任务\n• 正在运行的安全任务：允许完成当前落盘阶段，绝不粗暴强杀",
            "🛡️ **保护项**：\n✅ 平台身份凭据\n✅ 剪映草稿工程\n✅ 关键项目代码文件",
            "▶ **需要释放空间后恢复生产**"
        ]

        if ev:
            return self.update_event(
                event_id=ev.get("event_id"),
                title=title,
                color="carmine",
                elements=elements,
                new_status="CRITICAL",
                action_required="需要人工处理"
            )
        else:
            ok, ev_id, err = self.create_event(
                event_type=EventType.DISK_SPACE,
                event_key=event_key,
                title=title,
                color="carmine",
                elements=elements,
                severity=Severity.CRITICAL,
                action_required="需要人工处理"
            )
            return ok, err

    # --------------------------------------------------------------------------
    # 模块三：流水线启动、恢复、结束与每日日报 (Lifecycle & Daily Summary)
    # --------------------------------------------------------------------------

    def notify_pipeline_resumed(
        self,
        resume_reason: str,
        current_condition: str,
        current_task: str,
        progress_desc: str
    ) -> Tuple[bool, Optional[str]]:
        """
        重大恢复/人工拉起启动通知：普通日常自动启动 0 打扰，仅在异常恢复后发送 1 条绿卡。
        """
        title = "🟢【生产流水线｜已恢复运行】"
        elements = [
            f"**恢复原因**：\n{resume_reason}",
            f"**当前条件**：\n{current_condition}",
            f"**当前任务**：\n{current_task}",
            f"**当前进度**：\n{progress_desc}",
            "状态：正常运行 ｜ 无需处理"
        ]
        event_key = f"pipeline_resume_{int(time.time()//300)}"
        return self.create_event(
            event_type=EventType.PIPELINE_STATE,
            event_key=event_key,
            title=title,
            color="green",
            elements=elements,
            severity=Severity.INFO,
            action_required="无需处理"
        )

    def notify_pipeline_finished_all(
        self,
        season: str,
        total_count: int,
        success_count: int,
        failed_count: int,
        image_count: int,
        copy_count: int,
        next_stage: str = "冬季素材库"
    ) -> Tuple[bool, Optional[str]]:
        """全流程大阶段任务圆满达成通知"""
        percent = (success_count / total_count * 100) if total_count > 0 else 100.0
        title = f"🎉【{season}素材库｜生产完成】"
        elements = [
            f"• **总进度**：**{total_count} / {total_count} 套** (完成率: {percent:.1f}%)\n• 成功：**{success_count}** 套 ｜ 异常待处理：**{failed_count}** 套",
            f"📦 **总产物交付**：\n• **{image_count}** 张 3:4 高清成品图\n• **{copy_count}** 份多端营销文案",
            "📂 [📁 成品库直达](file:///D:/AICode/项目推进/projects/江湖有旅人/主项目/03-成品库) ｜ 📊 [飞书多维台账](https://my.feishu.cn/sheets/D7OMsirIChkd2gt8TMBcPHD9ndc?sheet=hp4PGN)",
            f"▶ **下一阶段**：{next_stage}",
            "状态：阶段完成 ｜ 无需处理"
        ]
        event_key = f"pipeline_finish_{season}"
        return self.create_event(
            event_type=EventType.PIPELINE_STATE,
            event_key=event_key,
            title=title,
            color="green",
            elements=elements,
            severity=Severity.INFO,
            action_required="无需处理"
        )

    def notify_daily_summary(
        self,
        date_str: str,
        today_done: int,
        today_success: int,
        today_failed: int,
        season: str,
        total_done: int,
        target_total: int,
        c_free_gb: float,
        ag_status: str = "正常 🟢",
        net_status: str = "正常 🟢",
        next_plan: str = "明日继续秋季素材生产"
    ) -> Tuple[bool, Optional[str]]:
        """每日生产日报（每天只发 1 次）"""
        percent = (total_done / target_total * 100) if target_total > 0 else 0.0
        c_status_icon = "🟢" if c_free_gb >= 25 else ("🟡" if c_free_gb >= 15 else "🔴")

        title = f"📊【流水线日报｜{date_str}】"
        elements = [
            f"**今日完成**：\n• 总交付：**{today_done}** 套\n• 成功：**{today_success}** 套 ｜ 异常：**{today_failed}** 套",
            f"**{season}总进度**：\n• **{total_done} / {target_total}** ({percent:.1f}%)",
            f"**系统健康大盘**：\n• C 盘空间：**{c_free_gb:.1f} GB** {c_status_icon}\n• Antigravity：{ag_status}\n• 网络专线：{net_status}",
            f"▶ **规划**：{next_plan}",
            "状态：健康正常 ｜ 无需处理"
        ]
        event_key = f"daily_summary_{date_str}"
        return self.create_event(
            event_type=EventType.PRODUCTION_DAILY_SUMMARY,
            event_key=event_key,
            title=title,
            color="green",
            elements=elements,
            severity=Severity.INFO,
            action_required="无需处理"
        )

    # --------------------------------------------------------------------------
    # 模块四：Antigravity 账号切换与专线网络自愈 (Account Switch & Network)
    # --------------------------------------------------------------------------

    def notify_account_switching(
        self,
        current_account: str,
        target_account: str,
        current_5h: float,
        current_week: float,
        target_5h: float,
        target_week: float,
        task_name: str = "默认工作区",
        session_id: str = "主会话"
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """额度 <= 5% 触发切号：创建 1 张橙色卡片 🟠【Antigravity｜额度触发，正在切号】"""
        event_key = f"ag_switch_{current_account}_{target_account}"
        title = "🟠【Antigravity｜额度触发，正在切号】"
        elements = [
            f"**当前账号**：`{current_account}`\n• 5h：{current_5h:.1f}% 🔴 ｜ 周：{current_week:.1f}%",
            f"**接力账号**：`{target_account}`\n• 5h：{target_5h:.1f}% ｜ 周：{target_week:.1f}%",
            f"🛡️ **已保护当前任务**\n{task_name} ｜ 断点会话 {session_id}",
            "⚡ 状态：正在切换… ｜ 正在自动处理"
        ]
        return self.create_event(
            event_type=EventType.ANTIGRAVITY_ACCOUNT_SWITCH,
            event_key=event_key,
            title=title,
            color="orange",
            elements=elements,
            severity=Severity.PROCESSING,
            action_required="正在自动处理",
            metadata={
                "current_account": current_account,
                "target_account": target_account,
                "start_time": time.time()
            }
        )

    def notify_account_switched(
        self,
        current_account: str,
        target_account: str,
        target_5h: float,
        target_week: float
    ) -> Tuple[bool, Optional[str]]:
        """切号成功：原地将橙卡更新为 🟢【Antigravity｜切号完成】，禁止发送第二条新消息！"""
        ledger = _load_ledger()
        event_key = f"ag_switch_{current_account}_{target_account}"
        ev = ledger.get("active_events", {}).get(event_key)
        if not ev:
            # 兼容其他 key 格式
            for k, e in ledger.get("active_events", {}).items():
                if e.get("event_type") == EventType.ANTIGRAVITY_ACCOUNT_SWITCH:
                    ev = e
                    break

        title = "🟢【Antigravity｜切号完成】"
        elements = [
            f"`{current_account}` → `{target_account}`",
            f"**新账号额度**：\n• 5h：{target_5h:.1f}% ｜ 周：{target_week:.1f}%",
            "✅ 当前任务已接力\n✅ 断点会话已恢复\n✅ 订阅状态已更新",
            "状态：正常运行 ｜ 无需处理"
        ]
        if ev:
            return self.close_event(
                event_id=ev.get("event_id"),
                title=title,
                color="green",
                elements=elements,
                final_status=EventStatus.SUCCESS,
                action_required="无需处理"
            )
        else:
            return self.create_event(
                event_type=EventType.ANTIGRAVITY_ACCOUNT_SWITCH,
                event_key=event_key,
                title=title,
                color="green",
                elements=elements,
                severity=Severity.INFO,
                action_required="无需处理"
            )

    def notify_account_switch_failed(
        self,
        current_account: str,
        target_account: str,
        current_5h: float,
        human_readable_error: str
    ) -> Tuple[bool, Optional[str]]:
        """切号失败：原地将原卡更新为 🔴【Antigravity｜自动切号失败】并 @负责人"""
        ledger = _load_ledger()
        event_key = f"ag_switch_{current_account}_{target_account}"
        ev = ledger.get("active_events", {}).get(event_key)
        if not ev:
            for k, e in ledger.get("active_events", {}).items():
                if e.get("event_type") == EventType.ANTIGRAVITY_ACCOUNT_SWITCH:
                    ev = e
                    break

        title = "🔴【Antigravity｜自动切号失败】"
        elements = [
            f"**当前账号**：`{current_account}` (5h: {current_5h:.1f}%)\n**目标账号**：`{target_account}`",
            "🛡️ 当前任务已保护\n❌ 自动切换失败",
            f"**失败原因**：{human_readable_error}",
            "▶ **需要人工处理**"
        ]
        if ev:
            return self.mark_event_failed(
                event_id=ev.get("event_id"),
                title=title,
                elements=elements,
                human_readable_error=human_readable_error,
                at_all=True
            )
        else:
            ok, ev_id, err = self.create_event(
                event_type=EventType.ANTIGRAVITY_ACCOUNT_SWITCH,
                event_key=event_key,
                title=title,
                color="red",
                elements=elements,
                severity=Severity.ERROR,
                action_required="需要人工处理"
            )
            return ok, err

    def handle_network_degraded(
        self,
        node: str = "",
        reason: str = "检测到网络受限或波动",
        force_alert: bool = False
    ) -> bool:
        """网络专线异常感知与防抖入栈：<20s 闪断只记本地日志 0 飞书，>=20s 橙卡自愈"""
        state_file = os.path.join(CANONICAL_LEDGER_DIR, "network_degrade_state.json")
        now = time.time()
        state = None
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
        except Exception:
            pass

        if not state:
            state = {
                "first_degraded_at": now,
                "original_node": node,
                "reason": reason,
                "alerted": False
            }
            try:
                os.makedirs(CANONICAL_LEDGER_DIR, exist_ok=True)
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False)
            except Exception:
                pass
            if not force_alert:
                logger.info(f"⏱️ [专线防抖] 专线 [{node}] 波动，启动 {NETWORK_ALERT_DELAY_SECONDS}s 观察期 (暂不发飞书)...")
                return False

        elapsed = now - state.get("first_degraded_at", now)
        if state.get("alerted", False):
            return True

        if force_alert or elapsed >= NETWORK_ALERT_DELAY_SECONDS:
            title = "🟠【Antigravity｜专线异常，正在自愈】"
            orig_node = state.get("original_node") or node or "当前专线"
            elements = [
                f"当前专线：`{orig_node}`\n异常：{reason}",
                "🔄 正在自动处理\n• 检测可用节点\n• 切换备用专线\n• 验证 Antigravity 连通性",
                "当前任务：🛡️ 已保护\n状态：正在恢复… ｜ 正在自动处理"
            ]
            self.create_event(
                event_type=EventType.ANTIGRAVITY_NETWORK,
                event_key="ag_net_incident",
                title=title,
                color="orange",
                elements=elements,
                severity=Severity.PROCESSING,
                action_required="正在自动处理",
                metadata={"original_node": orig_node, "first_degraded_at": state.get("first_degraded_at")}
            )
            state["alerted"] = True
            try:
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False)
            except Exception:
                pass
            return True
        return False

    def handle_network_recovered(
        self,
        current_node: str = "",
        latency_ms: str = ""
    ) -> bool:
        """网络专线恢复：<20s 闪断清除状态 0 飞书；此前已发橙卡则原地转绿"""
        state_file = os.path.join(CANONICAL_LEDGER_DIR, "network_degrade_state.json")
        now = time.time()
        state = None
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                os.remove(state_file)
        except Exception:
            pass

        ledger = _load_ledger()
        ev = ledger.get("active_events", {}).get("ag_net_incident")
        if not state and not ev:
            return True

        orig_node = (state or {}).get("original_node", "")
        if not (state or {}).get("alerted", False) and not ev:
            logger.info("⚡ [专线闪断自愈] 20 秒内瞬时自愈，0 飞书通知打扰！")
            return True

        # 原地更新为绿色
        is_switched = bool(orig_node and current_node and orig_node != current_node)
        title = "🟢【Antigravity｜专线已自愈】" if is_switched else "🟢【Antigravity｜专线已恢复】"
        node_sec = f"原专线：`{orig_node}`\n当前专线：`{current_node}`" if is_switched else f"当前专线：`{current_node or orig_node}`"
        rtt_str = f"{latency_ms} ms" if latency_ms else "正常"
        elements = [
            f"{node_sec}\n当前延迟：{rtt_str}",
            "✅ 网络恢复\n✅ Antigravity 已重新连通\n✅ 当前任务继续运行",
            "状态：正常 ｜ 无需处理"
        ]
        if ev:
            self.close_event(
                event_id=ev.get("event_id"),
                title=title,
                color="green",
                elements=elements,
                final_status=EventStatus.SUCCESS,
                action_required="无需处理"
            )
        return True

    def handle_network_failed(
        self,
        attempts: int = 3,
        error_summary: str = "全部备用节点连接超时"
    ) -> bool:
        """网络换节点彻底失败：原地置红 🔴 并提示人工处理"""
        state_file = os.path.join(CANONICAL_LEDGER_DIR, "network_degrade_state.json")
        orig_node = "当前专线"
        try:
            if os.path.exists(state_file):
                with open(state_file, "r", encoding="utf-8") as f:
                    s = json.load(f)
                    orig_node = s.get("original_node", orig_node)
                os.remove(state_file)
        except Exception:
            pass

        ledger = _load_ledger()
        ev = ledger.get("active_events", {}).get("ag_net_incident")
        title = "🔴【Antigravity｜专线自愈失败】"
        elements = [
            f"原专线：`{orig_node}`",
            f"已尝试：{attempts} 个节点\nAntigravity：仍未恢复",
            "🛡️ 当前任务已保护",
            f"失败原因：{error_summary}",
            "▶ **需要人工处理**"
        ]
        if ev:
            self.mark_event_failed(
                event_id=ev.get("event_id"),
                title=title,
                elements=elements,
                human_readable_error=error_summary,
                at_all=True
            )
        else:
            self.create_event(
                event_type=EventType.ANTIGRAVITY_NETWORK,
                event_key="ag_net_incident",
                title=title,
                color="red",
                elements=elements,
                severity=Severity.ERROR,
                action_required="需要人工处理"
            )
        return True


# 全局单例工厂
_DEFAULT_NOTIFIER = None


def get_notification_manager() -> NotificationCenter:
    """获取全局统一 NotificationCenter 实例"""
    global _DEFAULT_NOTIFIER
    if _DEFAULT_NOTIFIER is None:
        _DEFAULT_NOTIFIER = NotificationCenter()
    return _DEFAULT_NOTIFIER


# 向后兼容辅助函数
def create_event_message(*args, **kwargs):
    return get_notification_manager().create_event(*args, **kwargs)


def update_event_message(*args, **kwargs):
    return get_notification_manager().update_event(*args, **kwargs)


def close_event(*args, **kwargs):
    return get_notification_manager().close_event(*args, **kwargs)


def mark_event_failed(*args, **kwargs):
    return get_notification_manager().mark_event_failed(*args, **kwargs)


def handle_network_degraded_event(*args, **kwargs):
    return get_notification_manager().handle_network_degraded(*args, **kwargs)


def handle_network_recovered_event(*args, **kwargs):
    return get_notification_manager().handle_network_recovered(*args, **kwargs)


def handle_network_failed_event(*args, **kwargs):
    return get_notification_manager().handle_network_failed(*args, **kwargs)

