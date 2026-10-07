"""
股票T+0决策工具 - 场景构造与切换脚本
新状态模型下状态文件只记录客观交易状态，不再包含 pending_decision；
"等待确认的建议"存在于 LLM 对话上下文中。
"""

import sys
import json
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from state_manager import STATE_FILE, _default_state

PT_ENTRY_PRICE = 28.1
AT_ENTRY_PRICE = 28.8
ENTRY_TIME = "10:05:00"


def _write_state(state: dict):
    """写入状态文件"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"已写入场景状态: {STATE_FILE}")


def _load_state():
    """加载状态文件"""
    if not os.path.exists(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return _default_state()


def _entry_state() -> dict:
    """入场阶段（未交易）"""
    state = _default_state()
    state["today"] = str(date.today())
    return state


def _holding_state(trade_type: str, entry_price: float) -> dict:
    """已入场、持仓监控阶段"""
    state = _entry_state()
    state["traded_today"] = True
    state["trade_type"] = trade_type
    state["trade_phase"] = "exit"
    state["position_status"] = "bought_more" if trade_type == "positive" else "sold_part"
    state["entry_price"] = entry_price
    state["entry_time"] = ENTRY_TIME
    return state


def setup_pre():
    """场景: 盘前等待建议"""
    _write_state(_entry_state())
    print("场景: 盘前等待建议（entry 阶段）")


def setup_pt_buy_wait():
    """场景: LLM 已提议正T买入，等待用户确认（脚本侧仍为 entry 阶段）"""
    _write_state(_entry_state())
    print("场景: 等待入场确认（正T买入，建议在对话中）")


def setup_pt_buy_exec():
    """场景: 正T已入场"""
    _write_state(_holding_state("positive", PT_ENTRY_PRICE))
    print("场景: 已入场（正T买入，等待出场）")


def setup_pt_sell_wait():
    """场景: 正T持仓中，LLM 已提议卖出，等待用户确认"""
    _write_state(_holding_state("positive", PT_ENTRY_PRICE))
    print("场景: 等待出场确认（正T卖出，建议在对话中）")


def setup_pt_sell_exec():
    """场景: 正T已完成"""
    state = _holding_state("positive", PT_ENTRY_PRICE)
    state["position_status"] = "holding"
    state["entry_price"] = None
    state["entry_time"] = None
    state["trade_phase"] = "done"
    _write_state(state)
    print("场景: 正T操作全部完成（done）")


def setup_at_sell_wait():
    """场景: LLM 已提议反T卖出，等待用户确认（脚本侧仍为 entry 阶段）"""
    _write_state(_entry_state())
    print("场景: 等待入场确认（反T卖出，建议在对话中）")


def setup_at_sell_exec():
    """场景: 反T已入场"""
    _write_state(_holding_state("negative", AT_ENTRY_PRICE))
    print("场景: 已入场（反T卖出，等待买入接回）")


def setup_at_buy_wait():
    """场景: 反T持仓中，LLM 已提议买入接回，等待用户确认"""
    _write_state(_holding_state("negative", AT_ENTRY_PRICE))
    print("场景: 等待出场确认（反T买入接回，建议在对话中）")


def setup_at_buy_exec():
    """场景: 反T已完成"""
    state = _holding_state("negative", AT_ENTRY_PRICE)
    state["position_status"] = "holding"
    state["entry_price"] = None
    state["entry_time"] = None
    state["trade_phase"] = "done"
    _write_state(state)
    print("场景: 反T操作全部完成（done）")


def show_state():
    """显示当前状态"""
    state = _load_state()
    print(json.dumps(state, ensure_ascii=False, indent=2))


SCENARIOS = {
    "pre": setup_pre,
    "pt_buy_wait": setup_pt_buy_wait,
    "pt_buy_exec": setup_pt_buy_exec,
    "pt_sell_wait": setup_pt_sell_wait,
    "pt_sell_exec": setup_pt_sell_exec,
    "at_sell_wait": setup_at_sell_wait,
    "at_sell_exec": setup_at_sell_exec,
    "at_buy_wait": setup_at_buy_wait,
    "at_buy_exec": setup_at_buy_exec,
    "show": show_state,
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scenarios.py <命令>")
        print("命令: " + " | ".join(SCENARIOS.keys()))
        sys.exit(1)

    cmd = sys.argv[1].strip().lower()
    handler = SCENARIOS.get(cmd)
    if handler:
        handler()
    else:
        print(f"未知命令: {cmd}")
        print("用法: python scenarios.py <" + "|".join(SCENARIOS.keys()) + ">")
        sys.exit(1)
