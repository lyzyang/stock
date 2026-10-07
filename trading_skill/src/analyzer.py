"""
股票T+0决策工具 - 指标计算与数据整理
本模块只做确定性的数学计算，输出结构化"事实数据"：
- 技术指标数值（MA / RSI / MACD / 布林带 / 近期高低点 / 偏离度）
- 客观风控状态（止盈、止损、反T上涨保护是否触发的布尔标志）
不包含任何买卖判断、信号规则、预测价和文案——这些一律由 LLM 推理完成。
"""

import pandas as pd
from typing import Dict, Any, Optional

from config import (
    MA_SHORT, MA_LONG, RSI_PERIOD,
    RECENT_LOOKBACK,
    TAKE_PROFIT_PCT, STOP_LOSS_PCT,
    NEGATIVE_T_BOLLINGER_STOP_PCT,
)


def calculate_ma(data: pd.Series, period: int) -> float:
    """计算移动平均线"""
    if len(data) < period:
        return float(data.mean())
    return float(data.tail(period).mean())


def calculate_rsi(data: pd.Series, period: int = 14) -> float:
    """计算 RSI 指标"""
    if len(data) < period + 1:
        return 50.0

    delta = data.diff()
    gain = delta.where(delta > 0, 0).tail(period)
    loss = (-delta.where(delta < 0, 0)).tail(period)

    avg_gain = gain.mean()
    avg_loss = loss.mean()

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return float(round(100 - (100 / (1 + rs)), 2))


def calculate_macd(data: pd.Series) -> Dict[str, float]:
    """计算 MACD 指标"""
    ema12 = data.ewm(span=12, adjust=False).mean()
    ema26 = data.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    hist = 2 * (dif - dea)

    return {
        "dif": float(dif.iloc[-1]),
        "dea": float(dea.iloc[-1]),
        "hist": float(hist.iloc[-1]),
    }


def calculate_bollinger(data: pd.Series, period: int = 20) -> Dict[str, float]:
    """计算布林带"""
    ma = data.tail(period).mean()
    std = data.tail(period).std()
    return {
        "middle": float(ma),
        "upper": float(ma + 2 * std),
        "lower": float(ma - 2 * std),
    }


def indicator_snapshot(kline_df: pd.DataFrame, current_price: float) -> Dict[str, Any]:
    """
    汇总主周期全部技术指标"事实数值"，供 LLM 推理。
    仅返回数值，不做任何超买超卖/支撑压力定性判断。
    """
    close_prices = kline_df["close"]

    ma_short_val = calculate_ma(close_prices, MA_SHORT)
    ma_long_val = calculate_ma(close_prices, MA_LONG)
    rsi_val = calculate_rsi(close_prices, RSI_PERIOD)
    macd = calculate_macd(close_prices)
    bollinger = calculate_bollinger(close_prices)

    lookback = min(RECENT_LOOKBACK, len(close_prices))
    recent_high = float(close_prices.tail(lookback).max())
    recent_low = float(close_prices.tail(lookback).min())

    band_width = bollinger["upper"] - bollinger["lower"]
    bollinger_position = (
        (current_price - bollinger["middle"]) / band_width if band_width > 0 else None
    )

    return {
        f"ma{MA_SHORT}": round(ma_short_val, 3),
        f"ma{MA_LONG}": round(ma_long_val, 3),
        f"deviation_ma{MA_SHORT}_pct": round(
            (current_price - ma_short_val) / ma_short_val * 100, 3
        ),
        f"deviation_ma{MA_LONG}_pct": round(
            (current_price - ma_long_val) / ma_long_val * 100, 3
        ),
        f"rsi{RSI_PERIOD}": rsi_val,
        "macd": {k: round(v, 4) for k, v in macd.items()},
        "bollinger": {k: round(v, 3) for k, v in bollinger.items()},
        "bollinger_position": (
            round(bollinger_position, 3) if bollinger_position is not None else None
        ),
        "recent_high": round(recent_high, 3),
        "recent_low": round(recent_low, 3),
    }


def trend_facts(long_kline_df: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
    """
    辅助周期趋势原始数据：短/长周期均线数值与偏离百分比。
    趋势定性（上升/下降/震荡）由 LLM 依据这些数值完成。
    """
    if long_kline_df is None or long_kline_df.empty:
        return None

    close_prices = long_kline_df["close"]
    if len(close_prices) < 10:
        return None

    ma_short = calculate_ma(close_prices, 5)
    ma_long = calculate_ma(close_prices, 15)

    return {
        "ma5": round(ma_short, 3),
        "ma15": round(ma_long, 3),
        "deviation_pct": round((ma_short - ma_long) / ma_long * 100, 3),
    }


def daily_facts(daily_df: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
    """日K线事实摘要：近30日高低点与最新收盘"""
    if daily_df is None or daily_df.empty:
        return None

    close_prices = daily_df["close"]
    return {
        "bar_count": int(len(close_prices)),
        "last_close": round(float(close_prices.iloc[-1]), 3),
        "high_30": round(float(close_prices.max()), 3),
        "low_30": round(float(close_prices.min()), 3),
    }


def risk_status(
    current_price: float,
    entry_price: float,
    trade_type: str,
    bollinger: Optional[Dict[str, float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    客观风控状态（确定性计算，不含建议）：
    - 浮动盈亏金额与百分比
    - 按配置阈值计算的止盈/止损参考价
    - 止盈、止损、反T布林上轨保护是否已触发（布尔事实）
    LLM 必须优先尊重 flags 中为 true 的硬性风控事实。
    """
    if not entry_price:
        return None

    if trade_type == "positive":
        pnl = current_price - entry_price
        take_profit_price = entry_price * (1 + TAKE_PROFIT_PCT)
        stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
    elif trade_type == "negative":
        pnl = entry_price - current_price
        take_profit_price = entry_price * (1 - TAKE_PROFIT_PCT)
        stop_loss_price = entry_price * (1 + STOP_LOSS_PCT)
    else:
        return None

    pnl_pct = pnl / entry_price

    bollinger_stop_hit = False
    if trade_type == "negative" and bollinger:
        bollinger_stop_hit = (
            current_price >= bollinger["upper"] * (1 + NEGATIVE_T_BOLLINGER_STOP_PCT)
        )

    return {
        "take_profit_pct": TAKE_PROFIT_PCT,
        "stop_loss_pct": STOP_LOSS_PCT,
        "take_profit_price": round(take_profit_price, 2),
        "stop_loss_price": round(stop_loss_price, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct * 100, 3),
        "flags": {
            "take_profit_hit": pnl_pct >= TAKE_PROFIT_PCT,
            "stop_loss_hit": pnl_pct <= -STOP_LOSS_PCT,
            "bollinger_stop_hit": bollinger_stop_hit,
        },
    }
