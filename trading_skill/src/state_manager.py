"""
股票T+0决策工具 - 状态管理
只记录客观交易状态（阶段、方向、入场价），不存储任何决策建议。
决策建议是 LLM 的推理产物，存在于对话上下文中，不落入状态文件。
"""

import json
import os
from datetime import date, datetime
from typing import Optional, Dict, Any


STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")

VALID_TRADE_TYPES = ("positive", "negative")


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
        "traded_today": False,          # 今日是否已入场
        "trade_type": None,             # 交易方向: "positive" / "negative" / None
        "trade_phase": "entry",         # 交易阶段: "entry" / "exit" / "done"
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
    """检查今日是否还可以入场"""
    state = get_state()
    return not state["traded_today"]


def confirm_decision(price: float, trade_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    用户确认执行，按当前 trade_phase 做确定性状态流转：
    - entry 阶段：必须由调用方（LLM）告知方向 positive/negative，记录实际入场价后进入 exit
    - exit 阶段：恢复底仓状态，进入 done
    流转失败（阶段不匹配/方向缺失）返回 None。
    """
    state = get_state()

    if state["trade_phase"] == "entry":
        if trade_type not in VALID_TRADE_TYPES:
            return None

        state["traded_today"] = True
        state["trade_type"] = trade_type
        state["position_status"] = "bought_more" if trade_type == "positive" else "sold_part"
        state["entry_price"] = price
        state["entry_time"] = datetime.now().strftime("%H:%M:%S")
        state["trade_phase"] = "exit"
        _save_state(state)
        return state

    if state["trade_phase"] == "exit":
        state["position_status"] = "holding"
        state["entry_price"] = None
        state["entry_time"] = None
        state["trade_phase"] = "done"
        _save_state(state)
        result = state.copy()
        result["exit_price"] = price
        return result

    return None


def is_trade_done() -> bool:
    """今日交易是否已全部完成（已做完整T+0）"""
    state = get_state()
    return state.get("trade_phase") == "done"


def get_status_summary() -> str:
    """获取状态摘要（调试用）"""
    state = get_state()
    lines = [
        f"- 日期: {state['today']}",
        f"- 交易阶段: {state['trade_phase']}",
        f"- 今日已入场: {'是' if state['traded_today'] else '否'}",
    ]
    if state["trade_type"]:
        lines.append(f"- 交易方向: {'正T' if state['trade_type'] == 'positive' else '反T'}")
    if state["entry_price"]:
        lines.append(f"- 入场价格: {state['entry_price']}")
    if state["entry_time"]:
        lines.append(f"- 入场时间: {state['entry_time']}")
    return "\n".join(lines)
