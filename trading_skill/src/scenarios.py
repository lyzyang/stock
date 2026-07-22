"""
股票T+0决策工具 - 场景构造与切换脚本
"""

import sys
import json
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from state_manager import STATE_FILE, _default_state


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


def setup_pre():
    """场景: 盘前等待建议"""
    state = _default_state()
    state["today"] = str(date.today())
    _write_state(state)
    print("场景: 盘前等待建议")


def setup_pt_buy_wait():
    """场景: 设置等待入场确认（正T买入）"""
    state = _default_state()
    state["today"] = str(date.today())
    state["trade_phase"] = "entry"
    state["pending_decision"] = {
        "trade_type": "positive",
        "decision_type": "正T决策",
        "suggested_action": "买入 100 股 (价格参考 28.10)，等待反弹后卖出等量底仓",
        "next_status": "bought_more",
        "target_price": 28.52,
        "stop_loss_price": 27.54,
        "predicted_price": 28.47,
        "reason": "价格接近布林下轨; 价格接近近期低点",
        "stock_code": "600030.SH",
        "stock_name": "中信证券",
        "current_price": 28.1,
        "trade_shares": 100,
        "indicators": "MA5=28.09, MA20=28.17, RSI=36.5, MACD=-0.015",
        "entry_price": 28.1,
    }
    _write_state(state)
    print("场景: 设置等待入场确认（正T买入）")


def setup_pt_buy_exec():
    """场景: 执行入场（正T买入）"""
    state = _load_state()
    pending = state.get("pending_decision")
    if not pending or pending.get("trade_type") != "positive":
        print("错误: 当前不是正T买入待确认状态")
        return

    state["traded_today"] = True
    state["trade_type"] = "positive"
    state["position_status"] = "bought_more"
    state["entry_price"] = pending.get("entry_price")
    state["entry_time"] = "10:05:00"
    state["trade_phase"] = "exit"
    state["pending_decision"] = None
    _write_state(state)
    print("场景: 执行入场（正T买入）")


def setup_pt_sell_wait():
    """场景: 设置等待出场确认（正T卖出）"""
    state = _default_state()
    state["today"] = str(date.today())
    state["traded_today"] = True
    state["trade_type"] = "positive"
    state["trade_phase"] = "exit"
    state["position_status"] = "bought_more"
    state["entry_price"] = 28.1
    state["entry_time"] = "10:05:00"
    state["pending_decision"] = {
        "trade_type": "positive",
        "decision_type": "止盈止损出场建议",
        "suggested_action": "卖出 100 股 (价格参考 28.50)，完成正T",
        "exit_signal": "take_profit",
        "exit_message": "达到止盈目标！当前 28.50，成本 28.10，盈利 1.4%",
        "target_price": 28.52,
        "stop_loss_price": 27.54,
        "predicted_price": 28.47,
        "reason": "达到止盈目标！当前 28.50，成本 28.10，盈利 1.4%",
        "stock_code": "600030.SH",
        "stock_name": "中信证券",
        "current_price": 28.5,
        "indicators": "MA5=28.20, MA20=28.17, RSI=55.2, MACD=0.020",
    }
    _write_state(state)
    print("场景: 设置等待出场确认（正T卖出）")


def setup_pt_sell_exec():
    """场景: 执行出场（正T卖出）"""
    state = _load_state()
    pending = state.get("pending_decision")
    if not pending or pending.get("trade_type") != "positive":
        print("错误: 当前不是正T卖出待确认状态")
        return

    state["position_status"] = "holding"
    state["entry_price"] = None
    state["entry_time"] = None
    state["trade_phase"] = "done"
    state["pending_decision"] = None
    _write_state(state)
    print("场景: 执行出场（正T卖出）")


def setup_at_sell_wait():
    """场景: 设置等待入场确认（反T卖出）"""
    state = _default_state()
    state["today"] = str(date.today())
    state["trade_phase"] = "entry"
    state["pending_decision"] = {
        "trade_type": "negative",
        "decision_type": "反T决策",
        "suggested_action": "卖出 100 股 (价格参考 28.80)，等待回落后买入接回",
        "next_status": "sold_part",
        "target_price": 28.38,
        "stop_loss_price": 29.38,
        "predicted_price": 28.25,
        "reason": "价格接近布林上轨; 价格接近近期高点",
        "stock_code": "600030.SH",
        "stock_name": "中信证券",
        "current_price": 28.8,
        "trade_shares": 100,
        "indicators": "MA5=28.75, MA20=28.25, RSI=65.0, MACD=0.015",
        "entry_price": 28.8,
    }
    _write_state(state)
    print("场景: 设置等待入场确认（反T卖出）")


def setup_at_sell_exec():
    """场景: 执行入场（反T卖出）"""
    state = _load_state()
    pending = state.get("pending_decision")
    if not pending or pending.get("trade_type") != "negative":
        print("错误: 当前不是反T卖出待确认状态")
        return

    state["traded_today"] = True
    state["trade_type"] = "negative"
    state["position_status"] = "sold_part"
    state["entry_price"] = pending.get("entry_price")
    state["entry_time"] = "10:05:00"
    state["trade_phase"] = "exit"
    state["pending_decision"] = None
    _write_state(state)
    print("场景: 执行入场（反T卖出）")


def setup_at_buy_wait():
    """场景: 设置等待出场确认（反T买入接回）"""
    state = _default_state()
    state["today"] = str(date.today())
    state["traded_today"] = True
    state["trade_type"] = "negative"
    state["trade_phase"] = "exit"
    state["position_status"] = "sold_part"
    state["entry_price"] = 28.8
    state["entry_time"] = "10:05:00"
    state["pending_decision"] = {
        "trade_type": "negative",
        "decision_type": "止盈止损出场建议",
        "suggested_action": "买入接回 100 股 (价格参考 28.30)，完成反T",
        "exit_signal": "take_profit",
        "exit_message": "达到止盈目标！当前 28.30，成本 28.80，盈利 1.7%",
        "target_price": 28.38,
        "stop_loss_price": 29.38,
        "predicted_price": 28.25,
        "reason": "达到止盈目标！当前 28.30，成本 28.80，盈利 1.7%",
        "stock_code": "600030.SH",
        "stock_name": "中信证券",
        "current_price": 28.3,
        "indicators": "MA5=28.40, MA20=28.25, RSI=45.0, MACD=-0.015",
    }
    _write_state(state)
    print("场景: 设置等待出场确认（反T买入接回）")


def setup_at_buy_exec():
    """场景: 执行出场（反T买入接回）"""
    state = _load_state()
    pending = state.get("pending_decision")
    if not pending or pending.get("trade_type") != "negative":
        print("错误: 当前不是反T买入接回待确认状态")
        return

    state["position_status"] = "holding"
    state["entry_price"] = None
    state["entry_time"] = None
    state["trade_phase"] = "done"
    state["pending_decision"] = None
    _write_state(state)
    print("场景: 执行出场（反T买入接回）")


def show_state():
    """显示当前状态"""
    state = _load_state()
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scenarios.py <命令>")
        print("场景:")
        print("  pre             - 盘前等待建议")
        print("  pt_buy_wait     - 设置等待入场确认（正T买入）")
        print("  pt_buy_exec     - 执行入场（正T买入）")
        print("  pt_sell_wait    - 设置等待出场确认（正T卖出）")
        print("  pt_sell_exec    - 执行出场（正T卖出）")
        print("  at_sell_wait    - 设置等待入场确认（反T卖出）")
        print("  at_sell_exec    - 执行入场（反T卖出）")
        print("  at_buy_wait     - 设置等待出场确认（反T买入接回）")
        print("  at_buy_exec     - 执行出场（反T买入接回）")
        print("其他:")
        print("  show            - 显示当前状态")
        sys.exit(1)

    cmd = sys.argv[1].strip().lower()

    if cmd == "pre":
        setup_pre()
    elif cmd == "pt_buy_wait":
        setup_pt_buy_wait()
    elif cmd == "pt_buy_exec":
        setup_pt_buy_exec()
    elif cmd == "pt_sell_wait":
        setup_pt_sell_wait()
    elif cmd == "pt_sell_exec":
        setup_pt_sell_exec()
    elif cmd == "at_sell_wait":
        setup_at_sell_wait()
    elif cmd == "at_sell_exec":
        setup_at_sell_exec()
    elif cmd == "at_buy_wait":
        setup_at_buy_wait()
    elif cmd == "at_buy_exec":
        setup_at_buy_exec()
    elif cmd == "show":
        show_state()
    else:
        print(f"未知命令: {cmd}")
        print("用法: python scenarios.py <pre|pt_buy_wait|pt_buy_exec|pt_sell_wait|pt_sell_exec|at_sell_wait|at_sell_exec|at_buy_wait|at_buy_exec|show>")
        sys.exit(1)