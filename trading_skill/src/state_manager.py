"""
股票T+0决策工具 - 状态管理
管理每日交易状态：是否已交易、待确认决策、持仓状态等
"""

import json
import os
from datetime import date, datetime
from typing import Optional, Dict, Any


STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")


def _load_state() -> Dict[str, Any]:
    """加载状态文件"""
    if not os.path.exists(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return _default_state()


def _save_state(state: Dict[str, Any]):
    """保存状态文件"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _default_state() -> Dict[str, Any]:
    """默认状态"""
    return {
        "today": str(date.today()),
        "traded_today": False,          # 今日是否已完成一次T+0
        "trade_type": None,             # 今日交易类型: "positive" / "negative" / None
        "trade_phase": "entry",         # 交易阶段: "entry" / "exit" / "done"
        "pending_decision": None,       # 待确认的决策
        "position_status": "holding",   # 持仓状态: "holding" / "bought_more" / "sold_part"
        "entry_price": None,            # 入场价格
        "entry_time": None,             # 入场时间
    }


def _is_new_day(state: Dict[str, Any]) -> bool:
    """判断是否为新的一天"""
    return state.get("today") != str(date.today())


def reset_if_new_day():
    """如果是新的一天，重置状态"""
    state = _load_state()
    today = str(date.today())
    if not _is_new_day(state):
        return state

    new_state = _default_state()
    new_state["today"] = today
    _save_state(new_state)
    return new_state


def get_state() -> Dict[str, Any]:
    """获取当前状态"""
    return reset_if_new_day()


def can_trade() -> bool:
    """检查今日是否还可以交易"""
    state = get_state()
    return not state["traded_today"]


def set_pending_decision(decision: Dict[str, Any]):
    """设置待确认的决策"""
    state = get_state()
    state["pending_decision"] = decision
    _save_state(state)


def update_pending_decision(decision: Dict[str, Any]):
    """更新待确认的决策"""
    state = get_state()
    state["pending_decision"] = decision
    _save_state(state)


def confirm_decision(price: Optional[float] = None):
    """用户确认执行决策"""
    state = get_state()
    pending = state.get("pending_decision")
    if not pending:
        return None

    if state["trade_phase"] == "entry":
        state["traded_today"] = True
        state["trade_type"] = pending.get("trade_type")
        state["position_status"] = pending.get("next_status", "holding")
        state["entry_price"] = price if price is not None else pending.get("entry_price")
        state["entry_time"] = datetime.now().strftime("%H:%M:%S")
        state["trade_phase"] = "exit"
        pending_decision_copy = pending.copy()
        state["pending_decision"] = None
        _save_state(state)
        result = state.copy()
        result["pending_decision"] = pending_decision_copy
        return result

    if state["trade_phase"] == "exit":
        state["position_status"] = "holding"
        state["entry_price"] = None
        state["entry_time"] = None
        state["trade_phase"] = "done"
        pending_decision_copy = pending.copy()
        state["pending_decision"] = None
        _save_state(state)
        result = state.copy()
        result["pending_decision"] = pending_decision_copy
        if price is not None:
            result["exit_price"] = price
        return result

    return None


def get_pending_decision() -> Optional[Dict[str, Any]]:
    """获取待确认的决策"""
    state = get_state()
    return state.get("pending_decision")


def is_waiting_confirmation() -> bool:
    """是否正在等待用户确认"""
    state = get_state()
    return state.get("pending_decision") is not None


def is_trade_done() -> bool:
    """今日交易是否已全部完成（已做完整T+0）"""
    state = get_state()
    return state.get("trade_phase") == "done"


def get_status_summary() -> str:
    """获取状态摘要（用于OpenClaw上下文）"""
    state = get_state()
    lines = [
        f"- 日期: {state['today']}",
        f"- 今日已交易: {'是' if state['traded_today'] else '否'}",
    ]
    if state["trade_type"]:
        lines.append(f"- 交易类型: {'正T' if state['trade_type'] == 'positive' else '反T'}")
    if state["entry_price"]:
        lines.append(f"- 入场价格: {state['entry_price']}")
    if state["entry_time"]:
        lines.append(f"- 入场时间: {state['entry_time']}")
    if state["pending_decision"]:
        lines.append("- 状态: 等待用户确认决策")
    else:
        lines.append("- 状态: 监控中")
    return "\n".join(lines)


def clear_pending_decision():
    """清除待确认的决策"""
    state = get_state()
    state["pending_decision"] = None
    _save_state(state)
