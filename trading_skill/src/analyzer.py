"""
股票T+0决策工具 - T+0 分析逻辑
基于技术指标判断正T/反T信号
"""

import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime

from config import (
    STOCK_CODE, STOCK_NAME, EXCHANGE, HOLDING_SHARES,
    BUY_TRIGGER_MA_DEVIATION, SELL_TRIGGER_MA_DEVIATION,
    MA_SHORT, MA_LONG, RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
    MAX_POSITION_PCT, STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    EXIT_TRIGGER_RSI, EXIT_TRIGGER_BOLLINGER_PCT,
    NEGATIVE_T_BOLLINGER_STOP_PCT,
    RECENT_LOOKBACK, PREDICTED_PRICE_MIN_PCT,
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
    macd = 2 * (dif - dea)

    return {
        "dif": float(dif.iloc[-1]),
        "dea": float(dea.iloc[-1]),
        "macd": float(macd.iloc[-1]),
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


def calculate_predicted_price(
    price: float,
    bollinger: Dict[str, float],
    close_prices: pd.Series,
    trade_type: str,
) -> float:
    """
    计算预测价
    正T（先买后卖）：预测卖出价 = 综合布林上轨和近期高点（取较低值作为保守预测）
    反T（先卖后买）：预测买入价 = 综合布林下轨和近期低点（取较高值作为保守预测）
    """
    lookback = min(RECENT_LOOKBACK, len(close_prices))
    if lookback == 0:
        if trade_type == "positive":
            return round(bollinger["upper"] * (1 + PREDICTED_PRICE_MIN_PCT), 2)
        else:
            return round(bollinger["lower"] * (1 - PREDICTED_PRICE_MIN_PCT), 2)

    recent_high = float(close_prices.tail(lookback).max())
    recent_low = float(close_prices.tail(lookback).min())

    if trade_type == "positive":
        predicted = min(bollinger["upper"], recent_high)
        min_expected_price = price * (1 + PREDICTED_PRICE_MIN_PCT)
        if predicted <= min_expected_price:
            predicted = bollinger["upper"] * (1 + PREDICTED_PRICE_MIN_PCT)
    else:
        predicted = max(bollinger["lower"], recent_low)
        max_expected_price = price * (1 - PREDICTED_PRICE_MIN_PCT)
        if predicted >= max_expected_price:
            predicted = bollinger["lower"] * (1 - PREDICTED_PRICE_MIN_PCT)

    return round(predicted, 2)


def analyze_t0_signal(
    kline_df: pd.DataFrame,
    current_price: float,
    daily_kline: Optional[pd.DataFrame] = None,
    long_kline_df: Optional[pd.DataFrame] = None,
) -> Optional[Dict[str, Any]]:
    """
    T+0 信号分析主函数
    返回决策信号字典，无信号返回 None
    参数:
        kline_df: 主周期K线数据
        current_price: 当前价格
        daily_kline: 日K线数据（可选）
        long_kline_df: 辅助周期K线数据（可选，用于趋势判断）
    """
    if kline_df is None or kline_df.empty:
        return None

    close_prices = kline_df["close"]

    ma_short_val = calculate_ma(close_prices, MA_SHORT)
    ma_long_val = calculate_ma(close_prices, MA_LONG)
    rsi_val = calculate_rsi(close_prices, RSI_PERIOD)
    macd = calculate_macd(close_prices)
    bollinger = calculate_bollinger(close_prices)

    deviation_from_ma_short = (current_price - ma_short_val) / ma_short_val

    trend_bias = _analyze_long_period_trend(long_kline_df, current_price)

    signal = _check_positive_t_signal(
        current_price, deviation_from_ma_short, rsi_val, macd, bollinger, close_prices, trend_bias
    )

    if not signal:
        signal = _check_negative_t_signal(
            current_price, deviation_from_ma_short, rsi_val, macd, bollinger, close_prices, trend_bias
        )

    if not signal:
        signal = _generate_market_view_signal(
            current_price, ma_short_val, ma_long_val, rsi_val, macd, bollinger, close_prices, trend_bias
        )

    if signal:
        trade_shares = int(HOLDING_SHARES * MAX_POSITION_PCT)
        trade_shares = (trade_shares // 100) * 100
        if trade_shares < 100:
            trade_shares = 100

        signal["stock_code"] = f"{STOCK_CODE}.{EXCHANGE}"
        signal["stock_name"] = STOCK_NAME
        signal["current_price"] = current_price
        signal["trade_shares"] = trade_shares

        trend_info = f" / 趋势: {trend_bias}" if trend_bias else ""
        signal["indicators"] = (
            f"MA{MA_SHORT}: {ma_short_val:.2f} / MA{MA_LONG}: {ma_long_val:.2f} / "
            f"RSI: {rsi_val:.1f} / MACD: {macd['macd']:.3f}{trend_info}"
        )
        signal["entry_price"] = current_price

    return signal


def _analyze_long_period_trend(long_kline_df: Optional[pd.DataFrame], current_price: float) -> str:
    """
    分析辅助周期趋势
    返回: "上升" / "下降" / "震荡" / ""（无数据）
    """
    if long_kline_df is None or long_kline_df.empty:
        return ""

    close_prices = long_kline_df["close"]
    if len(close_prices) < 10:
        return ""

    ma_short = calculate_ma(close_prices, 5)
    ma_long = calculate_ma(close_prices, 15)

    deviation = (ma_short - ma_long) / ma_long

    if deviation > 0.005:
        return "上升"
    elif deviation < -0.005:
        return "下降"
    else:
        return "震荡"


def _generate_market_view_signal(
    price: float, ma_short: float, ma_long: float, rsi: float,
    macd: Dict[str, float], bollinger: Dict[str, float],
    close_prices: pd.Series,
    trend_bias: str = "",
) -> Optional[Dict[str, Any]]:
    """
    当没有强烈信号时，生成市场观点建议
    基于当前趋势给出倾向性建议（偏正T/偏反T/观望）
    参数:
        trend_bias: 辅助周期趋势判断（上升/下降/震荡）
    """
    deviation_short = (price - ma_short) / ma_short
    deviation_long = (price - ma_long) / ma_long
    bollinger_pct = (price - bollinger["middle"]) / (bollinger["upper"] - bollinger["lower"])

    reasons = []
    trade_type = "positive"
    suggested_action = "观望"
    decision_type = "市场观点"

    if deviation_long > 0.005:
        reasons.append("短期趋势偏强")
    elif deviation_long < -0.005:
        reasons.append("短期趋势偏弱")
    else:
        reasons.append("趋势不明朗")

    if rsi > 60:
        reasons.append("RSI偏强")
    elif rsi < 40:
        reasons.append("RSI偏弱")
    else:
        reasons.append("RSI中性")

    if macd["macd"] > 0:
        reasons.append("MACD红柱")
    else:
        reasons.append("MACD绿柱")

    if bollinger_pct > 0.6:
        reasons.append("价格偏布林上轨")
    elif bollinger_pct < 0.4:
        reasons.append("价格偏布林下轨")
    else:
        reasons.append("价格在布林带中间")

    if trend_bias:
        reasons.append(f"辅助周期趋势: {trend_bias}")

    score = 0
    if rsi > 55:
        score += 1
    if rsi < 45:
        score -= 1
    if deviation_short > 0.003:
        score += 1
    if deviation_short < -0.003:
        score -= 1
    if bollinger_pct > 0.6:
        score += 1
    if bollinger_pct < 0.4:
        score -= 1
    if macd["macd"] > 0:
        score += 1
    if macd["macd"] < 0:
        score -= 1

    if trend_bias == "上升":
        score += 1
    elif trend_bias == "下降":
        score -= 1

    if score >= 2:
        trade_type = "negative"
        suggested_action = (
            f"建议反T：卖出 {int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100} 股 "
            f"(价格 {price:.2f})，等待回落后买入接回"
        )
        decision_type = "反T建议（偏强）"
    elif score <= -2:
        trade_type = "positive"
        suggested_action = (
            f"建议正T：买入 {int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100} 股 "
            f"(价格 {price:.2f})，等待反弹后卖出等量底仓"
        )
        decision_type = "正T建议（偏弱）"
    elif score >= 1:
        trade_type = "negative"
        suggested_action = (
            f"倾向反T：卖出 {int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100} 股 "
            f"(价格 {price:.2f})，等待回落后买入接回"
        )
        decision_type = "反T建议（中性偏强）"
    else:
        trade_type = "positive"
        suggested_action = (
            f"倾向正T：买入 {int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100} 股 "
            f"(价格 {price:.2f})，等待反弹后卖出等量底仓"
        )
        decision_type = "正T建议（中性偏弱）"

    predicted_price = calculate_predicted_price(price, bollinger, close_prices, trade_type)
    return {
        "trade_type": trade_type,
        "decision_type": decision_type,
        "suggested_action": suggested_action,
        "next_status": "bought_more" if trade_type == "positive" else "sold_part",
        "target_price": round(price * (1 + TAKE_PROFIT_PCT), 2) if trade_type == "positive" else round(price * (1 - TAKE_PROFIT_PCT), 2),
        "stop_loss_price": round(price * (1 - STOP_LOSS_PCT), 2) if trade_type == "positive" else round(price * (1 + STOP_LOSS_PCT), 2),
        "predicted_price": predicted_price,
        "reason": "; ".join(reasons),
    }


def _check_positive_t_signal(
    price: float, deviation: float, rsi: float,
    macd: Dict[str, float], bollinger: Dict[str, float],
    close_prices: pd.Series,
    trend_bias: str = "",
) -> Optional[Dict[str, Any]]:
    """
    检测正T信号（先买后卖）
    条件：价格跌到支撑位，预期反弹
    参数:
        trend_bias: 辅助周期趋势判断（上升/下降/震荡）
    """
    reasons = []

    if deviation < BUY_TRIGGER_MA_DEVIATION:
        reasons.append(f"价格低于MA{MA_SHORT} {abs(deviation)*100:.1f}%")

    if rsi < RSI_OVERSOLD:
        reasons.append(f"RSI={rsi:.1f} 处于超卖区")

    if price <= bollinger["lower"] * 1.005:
        reasons.append("价格接近布林下轨")

    if macd["macd"] < 0 and macd["dif"] > macd["dea"]:
        reasons.append("MACD绿柱缩短")

    recent_low = close_prices.tail(10).min()
    if price <= recent_low * 1.003:
        reasons.append("价格接近近期低点")

    if trend_bias:
        reasons.append(f"辅助周期趋势: {trend_bias}")

    min_reasons = 2
    if trend_bias == "上升":
        min_reasons = 2
    elif trend_bias == "下降":
        min_reasons = 3

    if len(reasons) >= min_reasons:
        predicted_price = calculate_predicted_price(price, bollinger, close_prices, "positive")
        return {
            "trade_type": "positive",
            "decision_type": "正T决策",
            "suggested_action": (
                f"买入 {int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100} 股 "
                f"(价格 {price:.2f})，等待反弹后卖出等量底仓"
            ),
            "next_status": "bought_more",
            "target_price": round(price * (1 + TAKE_PROFIT_PCT), 2),
            "stop_loss_price": round(price * (1 - STOP_LOSS_PCT), 2),
            "predicted_price": predicted_price,
            "reason": "; ".join(reasons),
        }

    return None


def _check_negative_t_signal(
    price: float, deviation: float, rsi: float,
    macd: Dict[str, float], bollinger: Dict[str, float],
    close_prices: pd.Series,
    trend_bias: str = "",
) -> Optional[Dict[str, Any]]:
    """
    检测反T信号（先卖后买）
    条件：价格涨到压力位，预期回落
    参数:
        trend_bias: 辅助周期趋势判断（上升/下降/震荡）
    """
    reasons = []

    if deviation > SELL_TRIGGER_MA_DEVIATION:
        reasons.append(f"价格高于MA{MA_SHORT} {deviation*100:.1f}%")

    if rsi > RSI_OVERBOUGHT:
        reasons.append(f"RSI={rsi:.1f} 处于超买区")

    if price >= bollinger["upper"] * 0.995:
        reasons.append("价格接近布林上轨")

    if macd["macd"] > 0 and macd["dif"] < macd["dea"]:
        reasons.append("MACD红柱缩短")

    recent_high = close_prices.tail(10).max()
    if price >= recent_high * 0.997:
        reasons.append("价格接近近期高点")

    if trend_bias:
        reasons.append(f"辅助周期趋势: {trend_bias}")

    min_reasons = 2
    if trend_bias == "下降":
        min_reasons = 2
    elif trend_bias == "上升":
        min_reasons = 3

    if len(reasons) >= min_reasons:
        predicted_price = calculate_predicted_price(price, bollinger, close_prices, "negative")
        return {
            "trade_type": "negative",
            "decision_type": "反T决策",
            "suggested_action": (
                f"卖出 {int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100} 股 "
                f"(价格 {price:.2f})，等待回落后买入接回"
            ),
            "next_status": "sold_part",
            "target_price": round(price * (1 - TAKE_PROFIT_PCT), 2),
            "stop_loss_price": round(price * (1 + STOP_LOSS_PCT), 2),
            "predicted_price": predicted_price,
            "reason": "; ".join(reasons),
        }

    return None


def check_exit_signal(
    current_price: float,
    entry_price: float,
    trade_type: str,
    bollinger: Optional[Dict[str, float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    检查是否达到止盈/止损条件（入场后监控）
    反T场景下，若股价突破布林上轨一定比例，也触发止损保护接回
    """
    if entry_price is None or entry_price == 0:
        return None

    if trade_type == "positive":
        profit_pct = (current_price - entry_price) / entry_price
        if profit_pct >= TAKE_PROFIT_PCT:
            return {
                "signal": "take_profit",
                "message": f"达到止盈目标！当前 {current_price:.2f}，成本 {entry_price:.2f}，盈利 {profit_pct*100:.1f}%",
            }
        elif profit_pct <= -STOP_LOSS_PCT:
            return {
                "signal": "stop_loss",
                "message": f"触发止损！当前 {current_price:.2f}，成本 {entry_price:.2f}，亏损 {abs(profit_pct)*100:.1f}%",
            }
    elif trade_type == "negative":
        profit_pct = (entry_price - current_price) / entry_price
        if profit_pct >= TAKE_PROFIT_PCT:
            return {
                "signal": "take_profit",
                "message": f"达到止盈目标！当前 {current_price:.2f}，卖出价 {entry_price:.2f}，差价收益 {profit_pct*100:.1f}%",
            }
        elif profit_pct <= -STOP_LOSS_PCT:
            return {
                "signal": "stop_loss",
                "message": f"触发止损！当前 {current_price:.2f}，卖出价 {entry_price:.2f}，差价亏损 {abs(profit_pct)*100:.1f}%",
            }

        if bollinger and current_price >= bollinger["upper"] * (1 + NEGATIVE_T_BOLLINGER_STOP_PCT):
            loss_pct = (current_price - entry_price) / entry_price
            return {
                "signal": "bollinger_stop",
                "message": (
                    f"反T上涨保护触发！当前 {current_price:.2f} 突破布林上轨 "
                    f"({bollinger['upper']:.2f})，卖出价 {entry_price:.2f}，"
                    f"当前浮亏 {loss_pct*100:.1f}%，建议立即买入接回止损。"
                ),
            }

    return None


def analyze_exit_decision(
    kline_df: pd.DataFrame,
    current_price: float,
    entry_price: float,
    trade_type: str,
) -> Optional[Dict[str, Any]]:
    """
    出场阶段动态分析：未触发止盈止损时，根据技术指标给出买卖建议
    正T已买入 -> 分析卖出信号
    反T已卖出 -> 分析买入接回信号
    """
    if kline_df is None or kline_df.empty:
        return None

    close_prices = kline_df["close"]

    ma_short_val = calculate_ma(close_prices, MA_SHORT)
    rsi_val = calculate_rsi(close_prices, RSI_PERIOD)
    bollinger = calculate_bollinger(close_prices)
    macd = calculate_macd(close_prices)

    deviation_from_ma_short = (current_price - ma_short_val) / ma_short_val

    if trade_type == "positive":
        reasons = []
        if deviation_from_ma_short > SELL_TRIGGER_MA_DEVIATION:
            reasons.append(f"价格高于MA{MA_SHORT} {deviation_from_ma_short*100:.1f}%")
        if rsi_val > EXIT_TRIGGER_RSI:
            reasons.append(f"RSI={rsi_val:.1f} 出现反弹迹象")
        if current_price >= bollinger["upper"] * (1 - EXIT_TRIGGER_BOLLINGER_PCT):
            reasons.append("价格接近布林上轨")
        if macd["macd"] > 0 and macd["dif"] < macd["dea"]:
            reasons.append("MACD红柱缩短")

        if len(reasons) >= 2:
            predicted_price = calculate_predicted_price(current_price, bollinger, close_prices, "positive")
            return {
                "trade_type": "positive",
                "decision_type": "正T出场建议",
                "suggested_action": (
                    f"卖出 {int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100} 股 "
                    f"(价格 {current_price:.2f})，完成正T"
                ),
                "reason": "; ".join(reasons),
                "target_price": round(entry_price * (1 + TAKE_PROFIT_PCT), 2),
                "stop_loss_price": round(entry_price * (1 - STOP_LOSS_PCT), 2),
                "current_price": current_price,
                "entry_price": entry_price,
                "stock_code": f"{STOCK_CODE}.{EXCHANGE}",
                "stock_name": STOCK_NAME,
                "predicted_price": predicted_price,
                "indicators": (
                    f"MA{MA_SHORT}: {ma_short_val:.2f} / RSI: {rsi_val:.1f} / MACD: {macd['macd']:.3f}"
                ),
            }

    elif trade_type == "negative":
        reasons = []
        if deviation_from_ma_short < BUY_TRIGGER_MA_DEVIATION:
            reasons.append(f"价格低于MA{MA_SHORT} {abs(deviation_from_ma_short)*100:.1f}%")
        if rsi_val < EXIT_TRIGGER_RSI:
            reasons.append(f"RSI={rsi_val:.1f} 出现回落迹象")
        if current_price <= bollinger["lower"] * (1 + EXIT_TRIGGER_BOLLINGER_PCT):
            reasons.append("价格接近布林下轨")
        if macd["macd"] < 0 and macd["dif"] > macd["dea"]:
            reasons.append("MACD绿柱缩短")

        if len(reasons) >= 2:
            predicted_price = calculate_predicted_price(current_price, bollinger, close_prices, "negative")
            return {
                "trade_type": "negative",
                "decision_type": "反T出场建议",
                "suggested_action": (
                    f"买入接回 {int(HOLDING_SHARES * MAX_POSITION_PCT / 100) * 100} 股 "
                    f"(价格 {current_price:.2f})，完成反T"
                ),
                "reason": "; ".join(reasons),
                "target_price": round(entry_price * (1 - TAKE_PROFIT_PCT), 2),
                "stop_loss_price": round(entry_price * (1 + STOP_LOSS_PCT), 2),
                "current_price": current_price,
                "entry_price": entry_price,
                "stock_code": f"{STOCK_CODE}.{EXCHANGE}",
                "stock_name": STOCK_NAME,
                "predicted_price": predicted_price,
                "indicators": (
                    f"MA{MA_SHORT}: {ma_short_val:.2f} / RSI: {rsi_val:.1f} / MACD: {macd['macd']:.3f}"
                ),
            }

    return None
