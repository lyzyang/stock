"""
股票T+0决策工具 - 主入口
职责边界（严格）：
- 本脚本只采集并整理数据，输出统一 JSON：持仓状态、实时行情、技术指标数值、客观风控事实
- 不做任何买卖判断、信号推理、预测价计算和文案生成——全部由 LLM 完成

命令：
    python src/main.py                      # 采集数据，输出 stock-t0-data/v1 JSON
    python src/main.py confirm <price> <positive|negative>
                                           # 用户确认执行，输出 stock-t0-action/v1 JSON
    python src/main.py status              # 打印状态摘要（调试）
"""

import sys
import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    STOCK_CODE, STOCK_NAME, EXCHANGE,
    HOLDING_SHARES, MAX_POSITION_PCT,
    KLINE_PERIOD, KLINE_COUNT,
    LONG_KLINE_PERIOD,
)
from data_fetcher import (
    get_realtime_quote, get_kline_data, get_daily_kline, get_long_kline_data,
)
from analyzer import (
    calculate_bollinger,
    indicator_snapshot, trend_facts, daily_facts, risk_status,
)
from state_manager import (
    get_state, confirm_decision, is_trade_done, get_status_summary,
)

DATA_SCHEMA = "stock-t0-data/v1"
ACTION_SCHEMA = "stock-t0-action/v1"

PRICE_MIN = 0.01
PRICE_MAX = 10000


def t0_shares() -> int:
    """单次T+0股数（底仓 × 比例，按100股取整，至少100股）"""
    shares = int(HOLDING_SHARES * MAX_POSITION_PCT)
    shares = (shares // 100) * 100
    return max(shares, 100)


def _bars_to_list(df, n: int) -> List[Dict[str, Any]]:
    """DataFrame 最近 n 根K线转原生 JSON 类型列表"""
    bars = []
    for row in df.tail(n).to_dict("records"):
        bars.append({
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2),
            "volume": round(float(row["volume"]), 0),
        })
    return bars


def collect_data() -> Dict[str, Any]:
    """
    采集并整理一次决策所需的全部事实数据。
    无论成功/部分失败，都返回同一套结构，错误写入 errors。
    """
    state = get_state()

    data: Dict[str, Any] = {
        "schema": DATA_SCHEMA,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stage": state["trade_phase"],        # entry / exit / done
        "stock": {
            "code": STOCK_CODE,
            "name": STOCK_NAME,
            "exchange": EXCHANGE,
            "symbol": f"{STOCK_CODE}.{EXCHANGE}",
        },
        "account": {
            "holding_shares": HOLDING_SHARES,
            "t0_shares": t0_shares(),
            "max_position_pct": MAX_POSITION_PCT,
        },
        "position": {
            "traded_today": state["traded_today"],
            "trade_type": state["trade_type"],
            "position_status": state["position_status"],
            "entry_price": state["entry_price"],
            "entry_time": state["entry_time"],
        },
        "quote": None,
        "market": {},
        "risk": None,
        "errors": [],
    }

    # 今日交易已全部完成：只需回传状态事实
    if is_trade_done():
        return data

    # 实时行情（后续一切数据的基础）
    quote = get_realtime_quote()
    if not quote:
        data["errors"].append("获取实时行情失败，请检查网络或数据源配置。")
        return data
    data["quote"] = quote

    current_price = quote["price"]

    # 主周期K线 + 指标事实
    kline = get_kline_data(realtime_price=current_price)
    bollinger = None
    if kline is not None and not kline.empty:
        bollinger = calculate_bollinger(kline["close"])
        data["market"]["main"] = {
            "period": KLINE_PERIOD,
            "bar_count": int(len(kline)),
            "indicators": indicator_snapshot(kline, current_price),
            "recent_bars": _bars_to_list(kline, 10),
        }
    else:
        data["errors"].append(f"获取{KLINE_PERIOD}K线失败。")

    # 辅助周期趋势原始数据（定性由 LLM 完成）
    long_kline = get_long_kline_data(realtime_price=current_price)
    trend = trend_facts(long_kline)
    if trend:
        data["market"]["trend"] = {"period": LONG_KLINE_PERIOD, **trend}

    # 日K线事实
    data["market"]["daily"] = daily_facts(get_daily_kline())

    # 持仓阶段：客观风控事实（盈亏 + 止盈止损/保护触发标志）
    if state["trade_phase"] == "exit" and state["entry_price"]:
        data["risk"] = risk_status(
            current_price,
            state["entry_price"],
            state["trade_type"],
            bollinger=bollinger,
        )

    return data


def confirm_execution(price: float, trade_type: Optional[str] = None) -> Dict[str, Any]:
    """
    用户「执行 price」确认：校验价格并驱动确定性状态流转。
    只回传事实（方向、价格、新阶段），确认文案由 LLM 按统一格式渲染。
    """
    result: Dict[str, Any] = {
        "schema": ACTION_SCHEMA,
        "status": "error",
        "trade_type": trade_type,
        "price": price,
        "time": datetime.now().strftime("%H:%M:%S"),
        "stage": None,
        "error": None,
    }

    if not (PRICE_MIN <= price <= PRICE_MAX):
        result["error"] = f"价格超出合理范围（{PRICE_MIN}-{PRICE_MAX}），请重新输入。"
        return result

    state = confirm_decision(price, trade_type)
    if not state:
        result["error"] = "没有待确认的决策，或交易方向无效。"
        return result

    result["stage"] = state["trade_phase"]
    result["trade_type"] = state["trade_type"]
    result["status"] = (
        "entry_confirmed" if state["trade_phase"] == "exit" else "exit_confirmed"
    )
    if state["trade_phase"] == "done":
        result["exit_price"] = price
    return result


def _print_json(payload: Dict[str, Any]):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        _print_json(collect_data())
    elif args[0] == "confirm":
        if len(args) < 2:
            _print_json({
                "schema": ACTION_SCHEMA,
                "status": "error",
                "error": "缺少价格参数，用法: python main.py confirm <price> [positive|negative]",
            })
        else:
            try:
                exec_price = float(args[1])
            except ValueError:
                _print_json({
                    "schema": ACTION_SCHEMA,
                    "status": "error",
                    "error": f"无效的价格格式: {args[1]}",
                })
            else:
                exec_type = args[2] if len(args) > 2 else None
                _print_json(confirm_execution(exec_price, exec_type))
    elif args[0] == "status":
        print(get_status_summary())
    else:
        _print_json({
            "schema": ACTION_SCHEMA,
            "status": "error",
            "error": f"未知命令: {args[0]}，可用命令: <无参数采集> | confirm <price> [type] | status",
        })
