#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""技术指标计算：只输出数值型整理数据，不含任何语义结论。

金叉/死叉、超买/超卖、趋势强弱等判断由 LLM 结合
analysis_methodology.md 自行推理，本模块只提供原始数值与近期序列。
"""

import sys
import json
import argparse
import numpy as np
from datetime import datetime

from market_data import get_kline_data

RECENT_SERIES_LEN = 5


def calculate_ma(data, periods=[5, 10, 20, 60]):
    closes = np.array([d['close'] for d in data])
    result = {}
    for period in periods:
        result[f'MA{period}'] = round(np.mean(closes[-period:]), 2) if len(closes) >= period else None
    return result


def calculate_macd(data):
    closes = np.array([d['close'] for d in data])
    if len(closes) < 26:
        return None

    ema12 = np.zeros(len(closes))
    ema26 = np.zeros(len(closes))
    ema12[11] = np.mean(closes[:12])
    ema26[25] = np.mean(closes[:26])

    for i in range(12, len(closes)):
        ema12[i] = (closes[i] * 2 / 13) + (ema12[i-1] * 11 / 13)
    for i in range(26, len(closes)):
        ema26[i] = (closes[i] * 2 / 27) + (ema26[i-1] * 25 / 27)

    dif = ema12 - ema26
    dea = np.zeros(len(dif))
    for i in range(9, len(dif)):
        dea[i] = (dif[i] * 2 / 10) + (dea[i-1] * 8 / 10)

    macd = 2 * (dif - dea)

    return {
        'DIF': round(dif[-1], 4),
        'DEA': round(dea[-1], 4),
        'HIST': round(macd[-1], 4),
        # 近期序列，供 LLM 观察交叉与柱状图变化
        'dif_series': [round(v, 4) for v in dif[-RECENT_SERIES_LEN:]],
        'dea_series': [round(v, 4) for v in dea[-RECENT_SERIES_LEN:]],
        'hist_series': [round(v, 4) for v in macd[-RECENT_SERIES_LEN:]]
    }


def calculate_rsi(data, period=14):
    closes = np.array([d['close'] for d in data])
    if len(closes) < period + 1:
        return None

    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    rsi_values = []
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
        rsi_values.append(round(100 - (100 / (1 + rs)), 2))

    return {
        'RSI': rsi_values[-1],
        'rsi_series': rsi_values[-RECENT_SERIES_LEN:]
    }


def calculate_kdj(data, period=9):
    closes = np.array([d['close'] for d in data])
    highs = np.array([d['high'] for d in data])
    lows = np.array([d['low'] for d in data])

    if len(closes) < period:
        return None

    k_values = []
    d_values = []

    for i in range(period - 1, len(closes)):
        high_range = np.max(highs[i-period+1:i+1])
        low_range = np.min(lows[i-period+1:i+1])
        rsv = (closes[i] - low_range) / (high_range - low_range) * 100 if high_range != low_range else 50

        k = (2/3 * k_values[-1] + 1/3 * rsv) if k_values else rsv
        d = (2/3 * d_values[-1] + 1/3 * k) if d_values else k

        k_values.append(k)
        d_values.append(d)

    j_values = 3 * np.array(k_values) - 2 * np.array(d_values)

    return {
        'K': round(k_values[-1], 2),
        'D': round(d_values[-1], 2),
        'J': round(j_values[-1], 2),
        'k_series': [round(v, 2) for v in k_values[-RECENT_SERIES_LEN:]],
        'd_series': [round(v, 2) for v in d_values[-RECENT_SERIES_LEN:]],
        'j_series': [round(v, 2) for v in j_values[-RECENT_SERIES_LEN:]]
    }


def calculate_bollinger(data, period=20):
    closes = np.array([d['close'] for d in data])
    if len(closes) < period:
        return None

    middle = np.zeros(len(closes))
    std_dev = np.zeros(len(closes))
    for i in range(period - 1, len(closes)):
        middle[i] = np.mean(closes[i-period+1:i+1])
        std_dev[i] = np.std(closes[i-period+1:i+1])

    upper = middle + 2 * std_dev
    lower = middle - 2 * std_dev

    price_position = (closes[-1] - lower[-1]) / (upper[-1] - lower[-1]) if upper[-1] != lower[-1] else 0.5

    return {
        'upper': round(upper[-1], 2),
        'middle': round(middle[-1], 2),
        'lower': round(lower[-1], 2),
        'price_position': round(price_position, 4)
    }


def calculate_trend_structure(data):
    """派生整理数据：价格与均线位置关系、MA20斜率、量能比值。数值本身不含结论。"""
    closes = np.array([d['close'] for d in data])
    volume = np.array([d['volume'] for d in data])

    ma = calculate_ma(data)
    ma20 = ma.get('MA20')
    ma60 = ma.get('MA60')
    if ma20 is None or ma60 is None:
        return None

    # MA20 近20日线性回归斜率（每日点位变化）
    ma20_series = np.array([np.mean(closes[max(0, i-19):i+1]) for i in range(len(closes))])
    ma20_slope = float(np.polyfit(range(20), ma20_series[-20:], 1)[0]) if len(closes) >= 20 else None

    avg_volume_20 = np.mean(volume[-20:])
    avg_volume_5 = np.mean(volume[-5:])

    return {
        'current_price': round(float(closes[-1]), 2),
        'price_vs_ma20': round(float(closes[-1]) - ma20, 2),
        'price_vs_ma60': round(float(closes[-1]) - ma60, 2),
        'ma20_minus_ma60': round(ma20 - ma60, 2),
        'ma20_slope_20d': round(ma20_slope, 4) if ma20_slope is not None else None,
        'volume_ratio_5_20': round(float(avg_volume_5 / avg_volume_20), 4) if avg_volume_20 != 0 else None
    }


def calculate_all_indicators(data):
    return {
        'MA': calculate_ma(data),
        'MACD': calculate_macd(data),
        'RSI': calculate_rsi(data),
        'KDJ': calculate_kdj(data),
        'Bollinger': calculate_bollinger(data),
        'trend_structure': calculate_trend_structure(data)
    }


def main():
    parser = argparse.ArgumentParser(description='技术指标计算工具（仅数值，不含结论）')
    parser.add_argument('--symbol', type=str, required=True, help='股票/指数代码')
    parser.add_argument('--indicators', type=str, default='all', help='技术指标列表，逗号分隔: ma,macd,rsi,kdj,boll,structure,all')

    args = parser.parse_args()

    kline_data = get_kline_data(args.symbol, 120)

    if not kline_data:
        print(json.dumps({
            'status': 'error',
            'message': f'无法获取 {args.symbol} 的K线数据',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, ensure_ascii=False, indent=2))
        return

    indicators = args.indicators.split(',')
    selected = {}

    if 'ma' in indicators or 'all' in indicators:
        selected['MA'] = calculate_ma(kline_data)
    if 'macd' in indicators or 'all' in indicators:
        selected['MACD'] = calculate_macd(kline_data)
    if 'rsi' in indicators or 'all' in indicators:
        selected['RSI'] = calculate_rsi(kline_data)
    if 'kdj' in indicators or 'all' in indicators:
        selected['KDJ'] = calculate_kdj(kline_data)
    if 'boll' in indicators or 'all' in indicators:
        selected['Bollinger'] = calculate_bollinger(kline_data)
    if 'structure' in indicators or 'all' in indicators:
        selected['trend_structure'] = calculate_trend_structure(kline_data)

    result = {
        'status': 'success',
        'data': {
            'symbol': args.symbol,
            'indicators': selected
        },
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
