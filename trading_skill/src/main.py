"""
股票T+0决策工具 - 主入口脚本
被 OpenClaw Skill 调用，执行一次完整的分析-决策流程
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    STOCK_CODE, STOCK_NAME, EXCHANGE,
    DECISION_TEMPLATE,
    HOLDING_SHARES, MAX_POSITION_PCT,
    TAKE_PROFIT_PCT, STOP_LOSS_PCT,
    MA_SHORT,
)
from logger import info
from data_fetcher import get_realtime_quote, get_kline_data, get_daily_kline
from analyzer import (
    analyze_t0_signal, check_exit_signal, analyze_exit_decision,
    calculate_bollinger, calculate_predicted_price,
)
from state_manager import (
    get_state, can_trade, set_pending_decision, update_pending_decision,
    confirm_decision,
    get_pending_decision, is_waiting_confirmation,
    is_trade_done, get_status_summary,
)


def run_analysis() -> dict:
    """
    执行一次完整的T+0分析流程
    返回结果字典，OpenClaw 根据结果决定如何回复用户
    """
    state = get_state()
    result = {
        "action": "monitor",       # monitor / decision / confirmation / exit_signal / done / error
        "message": "",
        "decision": None,
    }

    # 检查今日是否已完成
    if is_trade_done():
        result["message"] = "今日T+0已完成，明日再战。"
        result["action"] = "done"
        return result

    # 获取实时行情
    quote = get_realtime_quote()
    if not quote:
        result["action"] = "error"
        result["message"] = "获取实时行情失败，请检查网络或数据源配置。"
        return result

    current_price = quote["price"]

    # === 场景1: 正在等待用户确认之前的决策 ===
    if is_waiting_confirmation():
        pending = get_pending_decision()
        if pending:
            trade_type = pending.get("trade_type")
            trade_shares = pending.get("trade_shares", int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100)
            decision_type = pending.get("decision_type", "")
            is_exit_decision = pending.get("exit_signal") is not None or "出场" in decision_type or "止盈止损" in decision_type
            
            pending["current_price"] = current_price
            
            kline = get_kline_data(realtime_price=current_price)
            daily_kline = get_daily_kline()

            if kline is not None and not kline.empty:
                if not is_exit_decision:
                    latest_signal = analyze_t0_signal(kline, current_price, daily_kline)
                    if latest_signal:
                        latest_trade_type = latest_signal.get("trade_type")
                        if latest_trade_type == trade_type:
                            pending["reason"] = latest_signal.get("reason", pending.get("reason"))
                            pending["indicators"] = latest_signal.get("indicators", pending.get("indicators"))
                        else:
                            info(f"信号方向反转: {trade_type} -> {latest_trade_type}，保持原决策不变")

                bollinger = calculate_bollinger(kline["close"])
                pending["predicted_price"] = calculate_predicted_price(current_price, bollinger, kline["close"], trade_type)
            
            if is_exit_decision:
                trade_type_label = "正T" if trade_type == "positive" else "反T"
                if trade_type == "positive":
                    pending["suggested_action"] = (
                        f"卖出 {trade_shares} 股 (价格参考 {current_price:.2f})，完成正T"
                    )
                elif trade_type == "negative":
                    pending["suggested_action"] = (
                        f"买入接回 {trade_shares} 股 (价格参考 {current_price:.2f})，完成反T"
                    )
                if pending.get("exit_message"):
                    pending["reason"] = pending["exit_message"].replace("positive", "正T").replace("negative", "反T")
                
                if kline is not None and not kline.empty and not pending.get("indicators"):
                    from analyzer import calculate_ma, calculate_rsi, calculate_macd
                    ma_short_val = calculate_ma(kline["close"], MA_SHORT)
                    rsi_val = calculate_rsi(kline["close"])
                    macd_data = calculate_macd(kline["close"])
                    pending["indicators"] = (
                        f"MA{MA_SHORT}: {ma_short_val:.2f} / RSI: {rsi_val:.1f} / MACD: {macd_data['macd']:.3f}"
                    )
            else:
                if trade_type == "positive":
                    pending["target_price"] = round(current_price * (1 + TAKE_PROFIT_PCT), 2)
                    pending["stop_loss_price"] = round(current_price * (1 - STOP_LOSS_PCT), 2)
                    pending["suggested_action"] = (
                        f"买入 {trade_shares} 股 (价格参考 {current_price:.2f})，等待反弹后卖出等量底仓"
                    )
                elif trade_type == "negative":
                    pending["target_price"] = round(current_price * (1 - TAKE_PROFIT_PCT), 2)
                    pending["stop_loss_price"] = round(current_price * (1 + STOP_LOSS_PCT), 2)
                    pending["suggested_action"] = (
                        f"卖出 {trade_shares} 股 (价格参考 {current_price:.2f})，等待回落后买入接回"
                    )
            
            if pending.get("exit_signal") is None:
                pending["entry_price"] = current_price
            
            update_pending_decision(pending)
            
            result["action"] = "confirmation"
            result["message"] = format_decision_message(pending)
            result["decision"] = pending
        return result

    # === 场景2: 今日已交易，检查止盈止损、尾盘强平或给出新的出场建议 ===
    if state["traded_today"] and state["entry_price"]:
        # 反T场景需要布林带数据进行上涨保护判断
        kline = get_kline_data(realtime_price=current_price)
        bollinger = calculate_bollinger(kline["close"]) if kline is not None and not kline.empty else None

        exit_signal = check_exit_signal(
            current_price,
            state["entry_price"],
            state["trade_type"],
            bollinger=bollinger,
        )

        # 先尝试基于技术指标的动态出场建议
        exit_decision = analyze_exit_decision(
            kline, current_price, state["entry_price"], state["trade_type"]
        )

        # 如果达到止盈止损或触发保护，覆盖决策类型并添加止盈止损消息
        if exit_signal:
            indicators = ""
            if kline is not None and not kline.empty:
                from analyzer import calculate_ma, calculate_rsi, calculate_macd
                ma_short_val = calculate_ma(kline["close"], MA_SHORT)
                rsi_val = calculate_rsi(kline["close"])
                macd_data = calculate_macd(kline["close"])
                indicators = (
                    f"MA{MA_SHORT}: {ma_short_val:.2f} / RSI: {rsi_val:.1f} / MACD: {macd_data['macd']:.3f}"
                )

            if exit_decision:
                exit_decision["decision_type"] = "止盈止损出场建议"
                exit_decision["exit_signal"] = exit_signal["signal"]
                exit_decision["exit_message"] = exit_signal["message"]
                exit_decision["reason"] = f"{exit_signal['message']}; {exit_decision.get('reason', '')}".strip("; ")
                if indicators:
                    exit_decision["indicators"] = indicators
            else:
                predicted_price = "N/A"
                if kline is not None and not kline.empty and bollinger:
                    predicted_price = calculate_predicted_price(current_price, bollinger, kline["close"], state["trade_type"])

                exit_decision = {
                    "trade_type": state["trade_type"],
                    "decision_type": "止盈止损出场建议",
                    "suggested_action": (
                        "卖出" if state["trade_type"] == "positive" else "买入接回"
                    ) + f" {int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100} 股 (价格 {current_price:.2f})",
                    "exit_signal": exit_signal["signal"],
                    "exit_message": exit_signal["message"],
                    "current_price": current_price,
                    "entry_price": state["entry_price"],
                    "stock_code": f"{STOCK_CODE}.{EXCHANGE}",
                    "stock_name": STOCK_NAME,
                    "target_price": round(state["entry_price"] * (1 + TAKE_PROFIT_PCT), 2) if state["trade_type"] == "positive" else round(state["entry_price"] * (1 - TAKE_PROFIT_PCT), 2),
                    "stop_loss_price": round(state["entry_price"] * (1 - STOP_LOSS_PCT), 2) if state["trade_type"] == "positive" else round(state["entry_price"] * (1 + STOP_LOSS_PCT), 2),
                    "predicted_price": predicted_price,
                    "reason": exit_signal["message"],
                    "indicators": indicators,
                }

        if exit_decision:
            set_pending_decision(exit_decision)
            result["action"] = "exit_signal"
            result["message"] = format_decision_message(exit_decision)
            result["decision"] = exit_decision
        else:
            trade_type = state["trade_type"]
            if trade_type == "positive":
                target_price = round(state["entry_price"] * (1 + TAKE_PROFIT_PCT), 2)
                stop_loss_price = round(state["entry_price"] * (1 - STOP_LOSS_PCT), 2)
            else:
                target_price = round(state["entry_price"] * (1 - TAKE_PROFIT_PCT), 2)
                stop_loss_price = round(state["entry_price"] * (1 + STOP_LOSS_PCT), 2)

            predicted_price = "N/A"
            if kline is not None and not kline.empty:
                bollinger = calculate_bollinger(kline["close"])
                predicted_price = calculate_predicted_price(current_price, bollinger, kline["close"], trade_type)

            if trade_type == "positive":
                pnl = current_price - state["entry_price"]
                pnl_pct = pnl / state["entry_price"] * 100
            else:
                pnl = state["entry_price"] - current_price
                pnl_pct = pnl / state["entry_price"] * 100

            result["action"] = "monitor"
            result["message"] = (
                f"[持仓监控] {STOCK_NAME} 当前 {current_price:.2f} 元\n"
                f"入场价: {state['entry_price']:.2f} | 盈亏: {pnl:+.2f} ({pnl_pct:+.2f}%)\n"
                f"目标价: {target_price:.2f} | 止损价: {stop_loss_price:.2f} | 预测价: {predicted_price}"
            )
            result["decision"] = {
                "trade_type": trade_type,
                "current_price": current_price,
                "entry_price": state["entry_price"],
                "target_price": target_price,
                "stop_loss_price": stop_loss_price,
                "predicted_price": predicted_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            }
        return result

    # === 场景3: 今日未交易，分析T+0信号 ===
    if not can_trade():
        result["action"] = "done"
        result["message"] = "今日已完成T+0交易，明日再战。"
        return result

    # 获取K线数据
    kline = get_kline_data(realtime_price=current_price)
    daily_kline = get_daily_kline()

    # 分析信号
    signal = analyze_t0_signal(kline, current_price, daily_kline)

    if signal:
        # 保存待确认决策
        set_pending_decision(signal)

        result["action"] = "decision"
        result["message"] = format_decision_message(signal)
        result["decision"] = signal
    else:
        result["action"] = "monitor"
        result["message"] = (
            f"[监控中] {STOCK_NAME} 当前 {current_price:.2f} 元 "
            f"(涨跌幅 {quote.get('change_pct', 0):.2f}%)"
        )

    return result


def format_decision_message(decision: dict) -> str:
    """格式化决策消息"""
    return DECISION_TEMPLATE.format(
        stock_name=decision.get("stock_name", STOCK_NAME),
        stock_code=decision.get("stock_code", f"{STOCK_CODE}.{EXCHANGE}"),
        decision_type=decision.get("decision_type", "未知"),
        decision_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        current_price=decision.get("current_price", 0),
        suggested_action=decision.get("suggested_action", ""),
        predicted_price=decision.get("predicted_price", "N/A"),
        target_price=decision.get("target_price", "N/A"),
        stop_loss_price=decision.get("stop_loss_price", "N/A"),
        reason=decision.get("reason", ""),
        indicators=decision.get("indicators", ""),
    )


def handle_user_response(price: float) -> dict:
    """
    处理用户的回复（执行）
    由 OpenClaw Skill 在收到用户消息时调用
    """
    state = confirm_decision(price)
    if state:
        trade_type = state.get("trade_type", "")
        type_label = "正T" if trade_type == "positive" else "反T"
        decision_type = state.get("pending_decision", {}).get("decision_type", "")

        # 出场确认后交易完成（正T卖出 / 反T买入接回）
        if state.get("trade_phase") == "done":
            exit_price = state.get("exit_price", price)
            return {
                "action": "done",
                "message": (
                    f"[已确认执行] {type_label}操作已全部完成，今日结束。\n"
                    f"出场价: {exit_price:.2f}\n"
                    "请在广发易淘金APP中确认最终持仓已恢复为底仓。"
                ),
            }

        # 入场确认（正T买入 / 反T卖出）
        return {
            "action": "confirmed",
            "message": (
                f"[已确认执行] {type_label}入场\n"
                f"入场价: {price:.2f}\n"
                f"请在广发易淘金APP中手动操作：\n"
                f"{state.get('pending_decision', {}).get('suggested_action', '')}\n\n"
                f"执行后系统将继续监控止盈止损。"
            ),
        }
    else:
        return {
            "action": "error",
            "message": "没有待确认的决策。",
        }


if __name__ == "__main__":
    """命令行模式：直接运行一次分析"""
    result = run_analysis()
    action = result.get("action", "")
    message = result.get("message", "")
    decision = result.get("decision", {})

    if action == "decision":
        print("股票T+0决策报告")
        print()
        print(message)
    elif action == "confirmation":
        trade_type = decision.get("trade_type", "")
        type_label = "正T" if trade_type == "positive" else "反T"
        print("股票T+0决策报告")
        print()
        print(f"**等待确认 - {type_label}决策**")
        print()
        print(message)
    elif action == "exit_signal":
        print("股票T+0决策报告")
        print()
        print("**止盈止损/出场信号触发**")
        print()
        print(message)
    elif action == "monitor":
        if decision:
            trade_type = decision.get("trade_type", "")
            type_label = "正T" if trade_type == "positive" else "反T"
            pnl = decision.get("pnl", 0)
            pnl_pct = decision.get("pnl_pct", 0)
            print("股票T+0决策报告")
            print()
            print(f"**持仓监控 - {type_label}**")
            print()
            print(f"- 股票: {STOCK_NAME} ({STOCK_CODE}.{EXCHANGE})")
            print(f"- 当前价: {decision.get('current_price', 0):.2f}")
            print(f"- 入场价: {decision.get('entry_price', 0):.2f}")
            print(f"- 盈亏: {pnl:+.2f} ({pnl_pct:+.2f}%)")
            print(f"- 目标价: {decision.get('target_price', 'N/A')}")
            print(f"- 止损价: {decision.get('stop_loss_price', 'N/A')}")
            print(f"- 预测价: {decision.get('predicted_price', 'N/A')}")
        else:
            print("股票T+0决策报告")
            print()
            print("**监控中 - 等待交易信号**")
            print()
            print(message)
    elif action == "done":
        """print("**今日T+0交易已完成**")"""
        """print()"""
        """print(message)"""
    elif action == "error":
        print("股票T+0决策报告")
        print()
        print("**错误**")
        print()
        print(message)
    else:
        print(message)

    """print()"""
    """print("**状态摘要**")"""
    """print(get_status_summary())"""
