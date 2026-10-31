#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书统一事件状态流通知管理器 (Feishu Event-Driven State Flow Notifier)
======================================================================
核心设计哲学：
1. 飞书群是“状态面板”，不是“运行日志”；
2. 同一个事件只创建 1 条飞书消息，状态流转全程原地 PATCH 更新；
3. 严格的事件生命周期管理与去重 (event_id ↔ feishu_message_id 账本持久化)；
4. 告警防抖与秒级自愈抑制（闪断零打扰）；
5. 统一颜色规范：
   - 🟢 green  = 已恢复 / 已完成 / 无需处理
   - 🟡 yellow = 风险预警，但暂时无需操作
   - 🟠 orange = 系统正在自动处理中
   - 🔴 red    = 自动处理失败 / 需要人工介入
"""

import os
import sys
import time
import json
import uuid
import logging
import urllib.request
import urllib.error

logger = logging.getLogger("FeishuEventManager")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 引入并再导出统一 NotificationCenter
try:
    from notification_center import (
        NotificationCenter,
        get_notification_manager,
        Severity,
        EventStatus,
        EventType
    )
except ImportError:
    pass

LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
LEDGER_DIR = os.path.join(LOCAL_APPDATA, "Antigravity", "private-proxy")
LEDGER_FILE = os.path.join(LEDGER_DIR, "event_notifications_ledger.json")

FEISHU_CONFIG_FILE = r"D:\AICode\AI\secrets\平台服务\飞书\feishu_config.json"

# 网络故障通知防抖阈值（秒）：短暂异常 < 20 秒不发飞书，只记本地日志
NETWORK_ALERT_DELAY_SECONDS = int(os.environ.get("NETWORK_ALERT_DELAY_SECONDS", 20))

# Token 缓存
_TOKEN_CACHE = {
    "token": None,
    "expires_at": 0.0
}


def _load_ledger():
    """读取事件通知账本（含断电/重启自愈恢复）"""
    try:
        if os.path.exists(LEDGER_FILE):
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "active_events" not in data:
                        data["active_events"] = {}
                    if "history" not in data:
                        data["history"] = []
                    return data
    except Exception as e:
        logger.debug(f"读取事件通知账本异常: {e}")
    return {"active_events": {}, "history": []}


def _save_ledger(ledger):
    """原子保存事件通知账本"""
    try:
        os.makedirs(LEDGER_DIR, exist_ok=True)
        temp_file = LEDGER_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, LEDGER_FILE)
    except Exception as e:
        logger.warning(f"保存事件通知账本异常: {e}")


def get_tenant_access_token():
    """获取飞书鉴权 tenant_access_token（带 1.5 小时缓存与自动续期）"""
    global _TOKEN_CACHE
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
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
            token_info = json.loads(resp.read().decode("utf-8"))

        token = token_info.get("tenant_access_token")
        expire_sec = token_info.get("expire", 7200)
        if token:
            _TOKEN_CACHE["token"] = token
            # 提前 5 分钟过期
            _TOKEN_CACHE["expires_at"] = now + max(60, expire_sec - 300)
            return token
    except Exception as e:
        logger.warning(f"获取飞书 token 异常: {e}")
    return None


def get_target_chat_ids(chat_names=None):
    """解析目标群聊 chat_id 列表"""
    if not os.path.exists(FEISHU_CONFIG_FILE):
        return []
    try:
        with open(FEISHU_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        group_map = cfg.get("群列表", {})
        default_switch_cid = (
            cfg.get("account_switch_chat_id")
            or group_map.get(cfg.get("account_switch_chat"))
            or cfg.get("infra_ops_chat_id")
            or group_map.get("🚨-安全与验证码紧急报警")
            or "oc_260a8c92df29c17216d5e4047c2aa612"
        )
        targets = []
        if chat_names:
            for name in chat_names:
                cid = group_map.get(name)
                if not cid:
                    if str(name).startswith("oc_"):
                        cid = str(name)
                    elif name in ("账号状态通知群", "account_switch", "切号群"):
                        cid = default_switch_cid
                if cid and cid not in targets:
                    targets.append(cid)
        if not targets:
            targets.append(default_switch_cid)
        return targets
    except Exception as e:
        logger.warning(f"获取目标群聊 ID 异常: {e}")
        return []


def _build_card_json(title, content_md, template="orange"):
    """
    构造统一标准的飞书交互式卡片 JSON。
    template: 'orange' | 'green' | 'red' | 'yellow' | 'blue'
    """
    valid_templates = {"orange", "green", "red", "yellow", "blue", "grey", "turquoise", "carmine"}
    card_template = template if template in valid_templates else "orange"

    return {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": title
            },
            "template": card_template
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content_md
                }
            }
        ]
    }


def _raw_send_card(title, content_md, template="orange", chat_names=None):
    """底层物理发送卡片接口，返回成功发送的 [message_id] 列表"""
    token = get_tenant_access_token()
    targets = get_target_chat_ids(chat_names)
    if not token or not targets:
        return []

    card_json = _build_card_json(title, content_md, template)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    msg_ids = []
    for cid in targets:
        try:
            send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
            payload = {
                "receive_id": cid,
                "msg_type": "interactive",
                "content": json.dumps(card_json, ensure_ascii=False)
            }
            send_req = urllib.request.Request(send_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(send_req, timeout=10) as s_resp:
                res_data = json.loads(s_resp.read().decode("utf-8"))
                mid = res_data.get("data", {}).get("message_id")
                if mid:
                    msg_ids.append(mid)
        except Exception as e:
            logger.debug(f"发送飞书卡片异常 (cid={cid}): {e}")

    return msg_ids


def _raw_patch_card(message_id, title, content_md, template="green", max_retries=2):
    """
    底层物理 PATCH 原地更新卡片接口（带失败重试机制）。
    返回 True 表示更新成功，False 表示更新失败。
    """
    if not message_id:
        return False

    token = get_tenant_access_token()
    if not token:
        return False

    card_json = _build_card_json(title, content_md, template)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    patch_url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
    patch_payload = {
        "content": json.dumps(card_json, ensure_ascii=False)
    }

    for attempt in range(max_retries):
        try:
            patch_req = urllib.request.Request(
                patch_url,
                data=json.dumps(patch_payload).encode("utf-8"),
                headers=headers,
                method="PATCH"
            )
            with urllib.request.urlopen(patch_req, timeout=10) as resp:
                res_patch = json.loads(resp.read().decode("utf-8"))
                if res_patch.get("code") == 0:
                    logger.info(f"🎉 飞书状态卡片原地更新成功 (msg_id: {message_id}) -> 状态已刷新为: {title}")
                    return True
                else:
                    logger.warning(
                        f"飞书卡片更新返回异常 (code: {res_patch.get('code')}, attempt {attempt+1}/{max_retries}): {res_patch.get('msg')}"
                    )
        except Exception as e:
            logger.warning(f"PATCH 更新飞书卡片异常 ({message_id}, attempt {attempt+1}/{max_retries}): {e}")
        time.sleep(0.5)

    return False


# =============================================================================
# 统一高阶事件状态流 API (Event Lifecycle Management)
# =============================================================================

def get_active_event(event_type):
    """查询指定事件类型当前是否有正在进行的活跃事件"""
    ledger = _load_ledger()
    return ledger.get("active_events", {}).get(event_type)


def create_event_message(
    event_type,
    title,
    content_md,
    template="orange",
    status="PROCESSING",
    event_id=None,
    metadata=None,
    chat_names=None
):
    """
    创建一次新的独立事件消息（首发卡片）。
    严格去重铁律：若该 event_type 已存在未关闭的活跃事件，优先直接原地更新原卡片，绝不刷屏创建第二条！
    """
    ledger = _load_ledger()
    active_events = ledger.setdefault("active_events", {})

    # 1. 检查是否已有活跃事件
    existing = active_events.get(event_type)
    if existing and existing.get("feishu_message_id"):
        logger.info(f"💡 [事件去重保护] 检测到事件类型 [{event_type}] 已有活跃事件 ({existing.get('event_id')})，转为原地更新原消息。")
        update_success = update_event_message(
            event_type,
            title=title,
            content_md=content_md,
            template=template,
            status=status,
            metadata=metadata
        )
        if update_success:
            return active_events.get(event_type)

    # 2. 真正创建全新事件
    eid = event_id or f"{event_type.lower()}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    now = time.time()

    msg_ids = _raw_send_card(title, content_md, template=template, chat_names=chat_names)
    primary_mid = msg_ids[0] if msg_ids else None

    event_record = {
        "event_id": eid,
        "event_type": event_type,
        "status": status,
        "title": title,
        "content_md": content_md,
        "template": template,
        "feishu_message_id": primary_mid,
        "all_message_ids": msg_ids,
        "chat_names": chat_names or [],
        "started_at": now,
        "updated_at": now,
        "finished_at": None,
        "metadata": metadata or {}
    }

    if primary_mid:
        active_events[event_type] = event_record
        _save_ledger(ledger)
        logger.info(f"📤 [事件已创建] 类型: {event_type} | ID: {eid} | 飞书消息ID: {primary_mid} | 初始状态: {status}")
    else:
        logger.warning(f"⚠️ [事件卡片首发失败] 类型: {event_type} | ID: {eid} | 飞书接口未返回消息 ID")

    return event_record


def update_event_message(
    event_type_or_id,
    title,
    content_md,
    template="green",
    status=None,
    metadata=None,
    mention_at=False
):
    """
    原地更新事件原消息。
    降级策略：
    1. 有限重试更新原消息；
    2. 只有确认原消息彻底无法更新时，才允许发送一条标注接续的新消息；
    3. 严禁形成通知刷屏。
    """
    ledger = _load_ledger()
    active_events = ledger.setdefault("active_events", {})

    # 查找事件
    event_type = None
    event_record = None
    if event_type_or_id in active_events:
        event_type = event_type_or_id
        event_record = active_events[event_type]
    else:
        for etype, rec in active_events.items():
            if rec.get("event_id") == event_type_or_id:
                event_type = etype
                event_record = rec
                break

    if not event_record or not event_record.get("feishu_message_id"):
        logger.debug(f"未找到对应的活跃事件 ({event_type_or_id})，无法原地更新。")
        return False

    final_content_md = content_md
    if mention_at:
        final_content_md += "\n\n<at id=\"all\">所有人</at>"

    mid = event_record.get("feishu_message_id")
    success = _raw_patch_card(mid, title, final_content_md, template=template)

    now = time.time()
    if success:
        event_record["title"] = title
        event_record["content_md"] = content_md
        event_record["template"] = template
        event_record["updated_at"] = now
        if status:
            event_record["status"] = status
        if metadata:
            event_record.setdefault("metadata", {}).update(metadata)
        _save_ledger(ledger)
        return True
    else:
        # 降级策略：重试失败后的受控接续，绝不产生发送风暴
        logger.warning(f"⚠️ [原卡片更新失败] 事件: {event_type} | 消息ID: {mid}。正在执行受控接续降级...")
        fallback_content = f"⚠️ *原状态消息更新失败，本条为状态接续。*\n\n{final_content_md}"
        new_mids = _raw_send_card(title, fallback_content, template=template, chat_names=event_record.get("chat_names"))
        if new_mids:
            event_record["feishu_message_id"] = new_mids[0]
            event_record["all_message_ids"] = new_mids
            event_record["title"] = title
            event_record["content_md"] = content_md
            event_record["template"] = template
            event_record["updated_at"] = now
            if status:
                event_record["status"] = status
            if metadata:
                event_record.setdefault("metadata", {}).update(metadata)
            _save_ledger(ledger)
            return True
        return False


def close_event(
    event_type_or_id,
    title=None,
    content_md=None,
    template="green",
    status="SUCCESS",
    metadata=None
):
    """
    关闭事件（终局闭环）：
    1. 若传入了 final title/content，原地更新为绿色完成状态；
    2. 将事件标记为 finished，从 active_events 移动至 history（保留最新 50 条）；
    3. 后续再次发生的相同类型告警将创建新的独立 event。
    """
    ledger = _load_ledger()
    active_events = ledger.setdefault("active_events", {})
    history = ledger.setdefault("history", [])

    event_type = None
    event_record = None
    if event_type_or_id in active_events:
        event_type = event_type_or_id
        event_record = active_events[event_type]
    else:
        for etype, rec in active_events.items():
            if rec.get("event_id") == event_type_or_id:
                event_type = etype
                event_record = rec
                break

    if not event_record:
        if title and content_md and status == "FAILED":
            logger.info(f"未找到进行中活跃事件 ({event_type_or_id})，直接创建失败卡片并归档...")
            new_ev = create_event_message(
                event_type=event_type_or_id,
                title=title,
                content_md=content_md,
                template=template,
                status="FAILED",
                metadata=metadata
            )
            ledger = _load_ledger()
            active_events = ledger.setdefault("active_events", {})
            history = ledger.setdefault("history", [])
            target_key = new_ev.get("event_type") or event_type_or_id
            if target_key in active_events:
                rec = active_events.pop(target_key)
                rec["finished_at"] = time.time()
                history.append(rec)
                if len(history) > 50:
                    ledger["history"] = history[-50:]
                _save_ledger(ledger)
            return True
        logger.debug(f"尝试关闭不存在的活跃事件: {event_type_or_id}")
        return False

    # 若提供了内容，先执行最后一次原地更新
    if title and content_md:
        update_event_message(
            event_type,
            title=title,
            content_md=content_md,
            template=template,
            status=status,
            metadata=metadata
        )

    now = time.time()
    event_record["status"] = status
    event_record["finished_at"] = now
    if metadata:
        event_record.setdefault("metadata", {}).update(metadata)

    # 归档并移出活跃列表
    del active_events[event_type]
    history.append(event_record)
    if len(history) > 50:
        ledger["history"] = history[-50:]

    _save_ledger(ledger)
    logger.info(f"🏁 [事件已关闭并归档] 类型: {event_type} | 最终状态: {status} | 耗时: {now - event_record.get('started_at', now):.1f}s")
    return True


def mark_event_failed(
    event_type_or_id,
    title,
    content_md,
    error_summary="未知异常",
    metadata=None,
    mention_at=True
):
    """
    标记事件失败并关闭：
    1. 原地更新卡片为红色 🔴，附带失败原因；
    2. 仅在 FAILED 状态时允许 @负责人；
    3. 归档关闭事件。
    """
    meta = metadata or {}
    meta["error_summary"] = error_summary
    return close_event(
        event_type_or_id,
        title=title,
        content_md=content_md,
        template="red",
        status="FAILED",
        metadata=meta
    )


# =============================================================================
# 网络专线防抖与状态机专属业务层
# =============================================================================

_NETWORK_DEGRADE_STATE_FILE = os.path.join(LEDGER_DIR, "network_degrade_state.json")


def _load_network_degrade_state():
    try:
        if os.path.exists(_NETWORK_DEGRADE_STATE_FILE):
            with open(_NETWORK_DEGRADE_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _save_network_degrade_state(state):
    try:
        os.makedirs(LEDGER_DIR, exist_ok=True)
        tmp = _NETWORK_DEGRADE_STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _NETWORK_DEGRADE_STATE_FILE)
    except Exception:
        pass


def _clear_network_degrade_state():
    try:
        if os.path.exists(_NETWORK_DEGRADE_STATE_FILE):
            os.remove(_NETWORK_DEGRADE_STATE_FILE)
    except Exception:
        pass


def handle_network_degraded_event(node="", reason="检测到网络受限或波动", force_alert=False):
    """
    网络专线异常感知与防抖入栈：
    1. 短暂异常（持续 < 20 秒）只记本地日志，不发飞书！
    2. 连续异常持续 >= 20 秒，才首次发送橙色报警卡片。
    """
    now = time.time()
    state = _load_network_degrade_state()
    if not state:
        # 首次感知到异常，记录开始时间并进入防抖观察期
        state = {
            "first_degraded_at": now,
            "original_node": node,
            "reason": reason,
            "alerted": False
        }
        _save_network_degrade_state(state)
        if not force_alert:
            logger.info(f"⏱️ [网络专线防抖启动] 专线 [{node}] 出现波动，启动 {NETWORK_ALERT_DELAY_SECONDS}s 观察期 (暂不发飞书)...")
            return False

    elapsed = now - state.get("first_degraded_at", now)
    # 若已经发过通知，无需重复发送，保持活跃
    if state.get("alerted", False):
        return True

    # 超过防抖阈值或显式强制报警，真正触发飞书首次卡片
    if force_alert or elapsed >= NETWORK_ALERT_DELAY_SECONDS:
        title = "🟠【Antigravity｜专线异常，正在自愈】"
        orig_node = state.get("original_node") or node or "当前专线"
        content_md = (
            f"当前专线：`{orig_node}`\n"
            f"异常：{reason}\n\n"
            f"🔄 正在自动处理\n"
            f"• 检测可用节点\n"
            f"• 切换备用专线\n"
            f"• 验证 Antigravity 连通性\n\n"
            f"当前任务：🛡️ 已保护\n"
            f"状态：正在恢复…"
        )
        create_event_message(
            event_type="ANTIGRAVITY_NETWORK",
            title=title,
            content_md=content_md,
            template="orange",
            status="RECOVERING",
            metadata={"original_node": orig_node, "first_degraded_at": state.get("first_degraded_at")}
        )
        state["alerted"] = True
        _save_network_degrade_state(state)
        return True

    logger.debug(f"网络异常观察中 ({elapsed:.1f}s / {NETWORK_ALERT_DELAY_SECONDS}s)，暂不打扰群聊。")
    return False


def handle_network_recovered_event(current_node="", latency_ms="", region=""):
    """
    网络专线恢复事件：
    1. 若处于防抖观察期（异常总时间 < 20 秒）：完全不发飞书，直接消除状态！
    2. 若此前已向飞书发送了橙色告警卡片：原地更新为绿色，绝不发新消息！
    """
    now = time.time()
    state = _load_network_degrade_state()
    active_ev = get_active_event("ANTIGRAVITY_NETWORK")

    if not state and not active_ev:
        logger.debug("网络专线连通良好，无挂起故障事件。")
        return

    orig_node = (state or {}).get("original_node", "")
    first_degraded = (state or {}).get("first_degraded_at", now)
    duration = now - first_degraded
    _clear_network_degrade_state()

    # 场景 1：闪断且未发飞书（耗时 < 阈值）
    if not (state or {}).get("alerted", False) and not active_ev:
        logger.info(f"⚡ [网络专线闪断自愈] 专线在 {duration:.1f} 秒内即自愈恢复 (< {NETWORK_ALERT_DELAY_SECONDS}s)，已抑制飞书通知！")
        return

    # 场景 2：此前已发橙色卡片，必须原地更新原卡片
    is_switched_node = bool(orig_node and current_node and orig_node != current_node)
    title = "🟢【Antigravity｜专线已自愈】" if is_switched_node else "🟢【Antigravity｜专线已恢复】"

    node_section = f"原专线：`{orig_node}`\n当前专线：`{current_node}`" if is_switched_node else f"当前专线：`{current_node or orig_node}`"
    rtt_str = f"{latency_ms} ms" if latency_ms else "正常"

    content_md = (
        f"{node_section}\n"
        f"当前延迟：{rtt_str}\n\n"
        f"✅ 网络恢复\n"
        f"✅ Antigravity 已重新连通\n"
        f"✅ 当前任务继续运行\n\n"
        f"状态：正常｜无需处理"
    )

    close_event(
        "ANTIGRAVITY_NETWORK",
        title=title,
        content_md=content_md,
        template="green",
        status="RECOVERED",
        metadata={"current_node": current_node, "latency_ms": latency_ms, "duration": duration}
    )


def handle_network_failed_event(original_node="", attempted_count=0, error_summary="所有节点均不可用或尝试超时"):
    """
    网络专线自愈失败事件：
    原地更新为红色 🔴，提示人工处理并 @负责人。
    """
    state = _load_network_degrade_state()
    orig_node = (state or {}).get("original_node") or original_node or "当前专线"
    _clear_network_degrade_state()

    title = "🔴【Antigravity｜专线自愈失败】"
    content_md = (
        f"原专线：`{orig_node}`\n\n"
        f"已尝试：{attempted_count} 个节点\n"
        f"Antigravity：仍未恢复\n\n"
        f"🛡️ 当前任务已保护\n\n"
        f"失败原因：{error_summary}\n\n"
        f"▶ 需要人工处理"
    )

    mark_event_failed(
        "ANTIGRAVITY_NETWORK",
        title=title,
        content_md=content_md,
        error_summary=error_summary,
        metadata={"attempted_count": attempted_count, "original_node": orig_node},
        mention_at=True
    )
